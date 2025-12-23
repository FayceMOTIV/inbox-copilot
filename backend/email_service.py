from typing import List, Dict, Any, Optional, Tuple
import logging
import base64
import re
import io
from email.utils import parseaddr
from fastapi import HTTPException
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import aiohttp

from backend.database import get_db
from backend.oauth_gmail import GmailOAuth
from backend.oauth_microsoft import MicrosoftOAuth

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_data: bytes) -> str:
    """Extract text content from a PDF file."""
    try:
        from PyPDF2 import PdfReader
        pdf_file = io.BytesIO(pdf_data)
        reader = PdfReader(pdf_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        logger.error(f"Error extracting PDF text: {e}")
        return ""


def extract_amounts_from_text(text: str) -> Dict[str, Any]:
    """
    Extract monetary amounts from text, with special attention to payment amounts.
    Returns dict with 'total_to_pay' (the amount to pay) and 'all_amounts' (all found amounts).
    """
    all_amounts = []
    total_to_pay = None

    # PRIORITY 1: Look for explicit "amount to pay" patterns (amount on same line)
    payment_patterns = [
        (r'NET\s*[AÀ]\s*PAYER\s*:?\s*(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})', 'net_a_payer'),
        (r'MONTANT\s*TTC\s*:?\s*(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})', 'montant_ttc'),
        (r'[AÀ]\s*PAYER\s*:?\s*(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})', 'a_payer'),
        (r'SOLDE\s*(?:DU|À|A)?\s*:?\s*(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})', 'solde'),
        (r'RESTE\s*[AÀ]\s*PAYER\s*:?\s*(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})', 'reste_a_payer'),
    ]

    for pattern, label in payment_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            for match in matches:
                clean_amount = match.replace('\u00a0', '').replace(' ', '').replace(',', '.')
                try:
                    value = float(clean_amount)
                    if value > 0:
                        total_to_pay = {
                            'value': value,
                            'formatted': f"{value:,.2f} €".replace(',', ' ').replace('.', ',').replace(' ', ' '),
                            'source': label
                        }
                        logger.info(f"📄 Found payment amount ({label}): {value}")
                        break
                except ValueError:
                    pass
            if total_to_pay:
                break

    # PRIORITY 2: Look for "Total TTC" followed by amount on next lines (Promocash format)
    # Pattern: "Total TTC :" followed later by an amount with €
    if not total_to_pay:
        ttc_match = re.search(r'Total\s*TTC\s*:', text, re.IGNORECASE)
        if ttc_match:
            # Look for the first amount with € after "Total TTC"
            after_ttc = text[ttc_match.end():]
            amount_after = re.search(r'(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})\s+[€]', after_ttc)
            if amount_after:
                clean_amount = amount_after.group(1).replace('\u00a0', '').replace(' ', '').replace(',', '.')
                try:
                    value = float(clean_amount)
                    if value > 0:
                        total_to_pay = {
                            'value': value,
                            'formatted': f"{value:,.2f} €".replace(',', ' ').replace('.', ',').replace(' ', ' '),
                            'source': 'total_ttc_after'
                        }
                        logger.info(f"📄 Found Total TTC (after pattern): {value}")
                except ValueError:
                    pass

    # PRIORITY 3: Extract all amounts for reference
    # Pattern allows 1-2 spaces before €
    amount_pattern = r'(\d{1,3}(?:[\s\u00a0]?\d{3})*[,\.]\d{2})\s{1,2}[€]'
    matches = re.findall(amount_pattern, text)

    for match in matches:
        clean_amount = match.replace('\u00a0', '').replace(' ', '').replace(',', '.')
        try:
            value = float(clean_amount)
            if value > 0 and value not in [a['value'] for a in all_amounts]:
                all_amounts.append({
                    'value': value,
                    'formatted': f"{value:,.2f} €".replace(',', ' ').replace('.', ',').replace(' ', ' ')
                })
        except ValueError:
            pass

    # Sort all amounts by value
    all_amounts.sort(key=lambda x: x['value'], reverse=True)

    # PRIORITY 4: If still no total, look for amount that appears at start of document
    # (often the total is shown prominently at the top)
    if not total_to_pay and all_amounts:
        # Find the first amount that appears in the first 500 chars
        first_500 = text[:500]
        for amt in all_amounts:
            # Try different formats
            amt_formats = [
                f"{amt['value']:.2f}".replace('.', ','),  # 2759,55
                f"{amt['value']:,.2f}".replace(',', ' ').replace('.', ','),  # 2 759,55
            ]
            for fmt in amt_formats:
                if fmt in first_500:
                    total_to_pay = {**amt, 'source': 'first_in_doc'}
                    logger.info(f"📄 Using first amount in document: {amt['value']}")
                    break
            if total_to_pay:
                break

    # PRIORITY 5: If only one reasonable amount found, use it
    if not total_to_pay and all_amounts:
        reasonable = [a for a in all_amounts if 10 <= a['value'] <= 50000]
        if len(reasonable) == 1:
            total_to_pay = {**reasonable[0], 'source': 'only_reasonable'}
            logger.info(f"📄 Only one reasonable amount found: {reasonable[0]['value']}")
        elif reasonable:
            # Take the largest reasonable amount (likely the invoice total)
            total_to_pay = {**reasonable[0], 'source': 'largest_reasonable'}
            logger.info(f"📄 Using largest reasonable amount: {reasonable[0]['value']}")

    return {
        'total_to_pay': total_to_pay,
        'all_amounts': all_amounts
    }


def parse_from_header(value: str) -> Tuple[Optional[str], Optional[str]]:
    if not value:
        return None, None
    name, email = parseaddr(value)
    name = name.strip('"') if name else None
    email = email or None
    return (name or email, email)


class EmailService:
    def __init__(self):
        self.gmail_oauth = GmailOAuth()
        self.microsoft_oauth = MicrosoftOAuth()

    def _handle_gmail_http_error(self, error: HttpError):
        msg = str(error)
        status = getattr(error, "resp", None).status if getattr(error, "resp", None) else None
        if status == 403 and "accessNotConfigured" in msg:
            raise HTTPException(
                status_code=503,
                detail="Gmail API disabled for the Google Cloud project used by OAuth. Enable Gmail API in Google Cloud Console, then retry."
            )
        raise error

    async def send_email(self, account_id: str, to: str, subject: str, body: str, signature_id: Optional[str] = None) -> dict:
        try:
            db = await get_db()
            account = await db.accounts.find_one({"account_id": account_id})
            if not account:
                raise Exception(f"Compte {account_id} non trouvé")

            final_body = body
            if signature_id:
                signature = await db.signatures.find_one({"signature_id": signature_id})
                if signature:
                    final_body = f"{body}\n\n{signature['content']}"
            else:
                default_sig = await db.signatures.find_one({"account_id": account_id, "is_default": True})
                if default_sig:
                    final_body = f"{body}\n\n{default_sig['content']}"

            if account.get("type") == "gmail":
                return await self._send_gmail(account_id, to, subject, final_body)
            if account.get("type") == "microsoft":
                return await self._send_microsoft(account_id, to, subject, final_body)
            raise Exception(f"Type de compte non supporté: {account.get('type')}")
        except Exception as e:
            logger.error(f"Erreur envoi email: {e}")
            raise

    async def _send_gmail(self, account_id: str, to: str, subject: str, body: str) -> dict:
        try:
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            credentials = await self.gmail_oauth.get_credentials(account_id)
            service = build('gmail', 'v1', credentials=credentials)
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            message.attach(MIMEText(body, 'plain'))
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            result = service.users().messages().send(userId='me', body={'raw': raw_message}).execute()
            logger.info(f"✅ Email envoyé via Gmail: {result['id']}")
            return {"success": True, "message_id": result['id']}
        except HttpError as e:
            self._handle_gmail_http_error(e)
        except Exception as e:
            logger.error(f"Erreur envoi Gmail: {e}")
            raise

    async def _send_microsoft(self, account_id: str, to: str, subject: str, body: str) -> dict:
        try:
            access_token = await self.microsoft_oauth.get_access_token(account_id)
            message = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "Text", "content": body},
                    "toRecipients": [{"emailAddress": {"address": to}}],
                }
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://graph.microsoft.com/v1.0/me/sendMail",
                    headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                    json=message,
                ) as response:
                    if response.status != 202:
                        error_text = await response.text()
                        raise Exception(f"Erreur Microsoft Graph: {error_text}")
            logger.info("✅ Email envoyé via Microsoft Graph")
            return {"success": True}
        except Exception as e:
            logger.error(f"Erreur envoi Microsoft: {e}")
            raise

    async def search_emails(self, account_id: str, query_string: str) -> List[Dict[str, Any]]:
        try:
            db = await get_db()
            account = await db.accounts.find_one({"account_id": account_id})
            if not account:
                raise Exception(f"Compte {account_id} non trouvé")
            if account.get("type") == "gmail":
                return await self._search_gmail(account_id, query_string)
            if account.get("type") == "microsoft":
                return await self._search_microsoft(account_id, query_string)
            raise Exception(f"Type de compte non supporté: {account.get('type')}")
        except Exception as e:
            logger.error(f"Erreur recherche email: {e}")
            raise

    async def _search_gmail(self, account_id: str, query: str, max_results: int = 500) -> List[Dict[str, Any]]:
        try:
            credentials = await self.gmail_oauth.get_credentials(account_id)
            service = build('gmail', 'v1', credentials=credentials)
            # Gmail API max is 500 per request
            results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            emails = []
            for msg in messages:
                message = service.users().messages().get(
                    userId='me', id=msg['id'], format='metadata', metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                headers = {h['name']: h['value'] for h in message['payload']['headers']}
                from_name, from_email = parse_from_header(headers.get('From', ''))
                emails.append({
                    "id": msg['id'],
                    "date": headers.get('Date', 'N/A'),
                    "from": headers.get('From', 'N/A'),
                    "from_email": from_email,
                    "from_name": from_name,
                    "subject": headers.get('Subject', 'N/A'),
                    "snippet": message.get('snippet', ''),
                    "link": f"https://mail.google.com/mail/u/0/#inbox/{msg['id']}"
                })
            return emails
        except HttpError as e:
            self._handle_gmail_http_error(e)
        except Exception as e:
            logger.error(f"Erreur recherche Gmail: {e}")
            raise

    async def _fetch_gmail_message_full(self, account_id: str, message_id: str) -> Dict[str, Any]:
        try:
            credentials = await self.gmail_oauth.get_credentials(account_id)
            service = build('gmail', 'v1', credentials=credentials)
            msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = {h.get("name"): h.get("value") for h in msg.get("payload", {}).get("headers", [])}
            body = ""
            parts = msg.get("payload", {}).get("parts", []) or []
            for part in parts:
                if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
                    body += base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="ignore")
            from_name, from_email = parse_from_header(headers.get("From"))
            # Extract attachments info
            attachments = self._extract_attachments_info(msg.get("payload", {}))

            return {
                "id": message_id,
                "date": headers.get("Date"),
                "from": headers.get("From"),
                "from_email": from_email,
                "from_name": from_name,
                "subject": headers.get("Subject"),
                "snippet": msg.get("snippet"),
                "body": body,
                "attachments": attachments,
            }
        except HttpError as e:
            self._handle_gmail_http_error(e)

    def _extract_attachments_info(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract attachment info from message payload recursively."""
        attachments = []

        def process_part(part):
            filename = part.get("filename", "")
            if filename and part.get("body", {}).get("attachmentId"):
                attachments.append({
                    "filename": filename,
                    "mimeType": part.get("mimeType", "application/octet-stream"),
                    "size": part.get("body", {}).get("size", 0),
                    "attachmentId": part.get("body", {}).get("attachmentId")
                })
            # Process nested parts
            for sub_part in part.get("parts", []):
                process_part(sub_part)

        process_part(payload)
        return attachments

    async def download_attachment(self, account_id: str, message_id: str, attachment_id: str) -> Tuple[bytes, str, str]:
        """Download an attachment and return (data, filename, mimeType)."""
        try:
            credentials = await self.gmail_oauth.get_credentials(account_id)
            service = build('gmail', 'v1', credentials=credentials)

            # Get attachment data
            attachment = service.users().messages().attachments().get(
                userId='me', messageId=message_id, id=attachment_id
            ).execute()

            data = base64.urlsafe_b64decode(attachment['data'])

            # Get filename from the message
            msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            filename, mime_type = self._find_attachment_filename(msg.get("payload", {}), attachment_id)

            return data, filename, mime_type
        except HttpError as e:
            self._handle_gmail_http_error(e)
        except Exception as e:
            logger.error(f"Erreur téléchargement pièce jointe: {e}")
            raise

    async def extract_invoice_data(self, account_id: str, message_id: str, attachment_id: str) -> Dict[str, Any]:
        """
        Download a PDF attachment and extract invoice data (amounts, dates, etc.)
        """
        try:
            logger.info(f"📄 Downloading PDF attachment {attachment_id[:20]}...")
            try:
                data, filename, mime_type = await self.download_attachment(account_id, message_id, attachment_id)
                logger.info(f"📄 Downloaded: {filename} ({len(data)} bytes, type: {mime_type})")
            except Exception as e:
                logger.error(f"📄 Download failed: {e}")
                return {"error": f"Download failed: {e}"}

            # Always try to extract from PDF, even if mime_type is wrong
            logger.info(f"📄 Extracting text from PDF...")
            try:
                text = extract_text_from_pdf(data)
                logger.info(f"📄 Extracted {len(text)} characters from PDF")
            except Exception as e:
                logger.error(f"📄 PDF extraction failed: {e}")
                return {"error": f"PDF extraction failed: {e}", "filename": filename}

            if not text:
                logger.warning(f"📄 No text extracted from PDF")
                return {"error": "Could not extract text from PDF", "filename": filename}

            # Extract amounts
            logger.info(f"📄 Searching for amounts in text...")
            logger.info(f"📄 PDF TEXT PREVIEW: {text[:1000]}")  # Debug: show text content
            amount_data = extract_amounts_from_text(text)
            total = amount_data.get('total_to_pay')
            amounts = amount_data.get('all_amounts', [])
            logger.info(f"📄 All amounts found: {amounts}")
            logger.info(f"📄 Total to pay: {total}")

            # Extract invoice number patterns
            invoice_patterns = [
                r'(?:facture|invoice|fact\.?)\s*n[°o]?\s*:?\s*([A-Z0-9\-]+)',
                r'n[°o]\s*(?:facture|invoice)\s*:?\s*([A-Z0-9\-]+)',
                r'(?:référence|ref\.?)\s*:?\s*([A-Z0-9\-]+)',
            ]
            invoice_number = None
            for pattern in invoice_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    invoice_number = match.group(1)
                    break

            # Extract date patterns
            date_patterns = [
                r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})',
                r'(\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4})',
            ]
            dates = []
            for pattern in date_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                dates.extend(matches[:3])

            result = {
                "filename": filename,
                "text_length": len(text),
                "amounts": amounts[:5],  # Top 5 amounts
                "total": total,
                "invoice_number": invoice_number,
                "dates_found": dates[:3],
                "text_preview": text[:500] if text else None
            }

            logger.info(f"📄 Extracted invoice data: {filename} - Total: {total}")
            return result

        except Exception as e:
            logger.error(f"Error extracting invoice data: {e}")
            return {"error": str(e)}

    def _find_attachment_filename(self, payload: Dict[str, Any], attachment_id: str) -> Tuple[str, str]:
        """Find filename and mimeType for an attachment by its ID."""
        def search_part(part):
            if part.get("body", {}).get("attachmentId") == attachment_id:
                return part.get("filename", "attachment"), part.get("mimeType", "application/octet-stream")
            for sub_part in part.get("parts", []):
                result = search_part(sub_part)
                if result:
                    return result
            return None

        result = search_part(payload)
        return result if result else ("attachment", "application/octet-stream")

    async def download_all_attachments(self, account_id: str, message_id: str, save_dir: str = "/tmp") -> List[Dict[str, Any]]:
        """Download all attachments from a message and save to disk."""
        import os

        try:
            credentials = await self.gmail_oauth.get_credentials(account_id)
            service = build('gmail', 'v1', credentials=credentials)

            # Get the full message
            msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            attachments_info = self._extract_attachments_info(msg.get("payload", {}))

            downloaded = []
            for att in attachments_info:
                try:
                    # Download attachment
                    attachment = service.users().messages().attachments().get(
                        userId='me', messageId=message_id, id=att["attachmentId"]
                    ).execute()

                    data = base64.urlsafe_b64decode(attachment['data'])

                    # Save to file
                    filepath = os.path.join(save_dir, att["filename"])
                    with open(filepath, 'wb') as f:
                        f.write(data)

                    downloaded.append({
                        "filename": att["filename"],
                        "size": len(data),
                        "path": filepath
                    })
                    logger.info(f"✅ Pièce jointe téléchargée: {att['filename']}")
                except Exception as e:
                    logger.error(f"Erreur téléchargement {att['filename']}: {e}")

            return downloaded
        except HttpError as e:
            self._handle_gmail_http_error(e)
        except Exception as e:
            logger.error(f"Erreur téléchargement pièces jointes: {e}")
            raise

    async def get_latest_email(self, account_id: str) -> Optional[Dict[str, Any]]:
        try:
            emails = await self._search_gmail(account_id, "newer_than:30d")
            if not emails:
                emails = await self._search_gmail(account_id, "")
            if not emails:
                return None
            return await self._fetch_gmail_message_full(account_id, emails[0]["id"])
        except HttpError as e:
            self._handle_gmail_http_error(e)

    async def get_email_by_id(self, account_id: str, email_id: str) -> Optional[Dict[str, Any]]:
        try:
            return await self._fetch_gmail_message_full(account_id, email_id)
        except HttpError as e:
            self._handle_gmail_http_error(e)

    async def _search_microsoft(self, account_id: str, query: str) -> List[Dict[str, Any]]:
        try:
            access_token = await self.microsoft_oauth.get_access_token(account_id)
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://graph.microsoft.com/v1.0/me/messages?$search=\"{query}\"&$top=10",
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Erreur Microsoft Graph: {error_text}")
                    data = await response.json()
                    messages = data.get('value', [])
            emails = []
            for msg in messages:
                emails.append({
                    "id": msg['id'],
                    "date": msg.get('receivedDateTime', 'N/A'),
                    "from": msg.get('from', {}).get('emailAddress', {}).get('address', 'N/A'),
                    "from_email": msg.get('from', {}).get('emailAddress', {}).get('address', 'N/A'),
                    "from_name": msg.get('from', {}).get('emailAddress', {}).get('name', 'N/A'),
                    "subject": msg.get('subject', 'N/A'),
                    "snippet": msg.get('bodyPreview', ''),
                    "link": msg.get('webLink', '#')
                })
            return emails
        except Exception as e:
            logger.error(f"Erreur recherche Microsoft: {e}")
            raise
