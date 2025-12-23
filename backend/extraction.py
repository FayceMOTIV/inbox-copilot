import re
from typing import Any, Dict, List, Optional

PHONE_RE = re.compile(r"(\+33\s?[1-9](?:[\s\.-]?\d{2}){4}|0[1-9](?:[\s\.-]?\d{2}){4})")
SIRET_RE = re.compile(r"\b\d{14}\b")
SIREN_RE = re.compile(r"\b\d{9}\b")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL_RE = re.compile(r"https?://\S+")


def extract_signature(body: str) -> str:
    lines = body.splitlines()
    tail = lines[-25:] if len(lines) > 25 else lines
    cleaned = []
    for ln in tail:
        if ln.strip().startswith(">"):
            continue
        if re.search(r"^On .*wrote:$", ln.strip()):
            break
        cleaned.append(ln)
    return "\n".join(cleaned).strip()


def regex_hits(text: str) -> Dict[str, List[str]]:
    return {
        "phones": list(dict.fromkeys(m.group(0) for m in PHONE_RE.finditer(text))),
        "siret": list(dict.fromkeys(m.group(0) for m in SIRET_RE.finditer(text))),
        "siren": list(dict.fromkeys(m.group(0) for m in SIREN_RE.finditer(text))),
        "emails": list(dict.fromkeys(m.group(0) for m in EMAIL_RE.finditer(text))),
        "urls": list(dict.fromkeys(m.group(0) for m in URL_RE.finditer(text))),
    }


def classify_attachment(filename: str, mime_type: Optional[str]) -> str:
    fn = (filename or "").lower()
    if "kbis" in fn:
        return "kbis"
    if "rib" in fn:
        return "rib"
    if "devis" in fn or "quote" in fn:
        return "devis"
    if "facture" in fn or "invoice" in fn:
        return "facture"
    if "cni" in fn or "identit" in fn or "passport" in fn:
        return "id"
    if (mime_type or "").lower().endswith("pdf"):
        return "pdf"
    return "other"


def build_extraction_input(email_obj: Dict[str, Any]) -> Dict[str, Any]:
    subject = email_obj.get("subject") or ""
    body = email_obj.get("body") or email_obj.get("snippet") or ""
    from_email = email_obj.get("from_email") or email_obj.get("from")
    from_name = email_obj.get("from_name") or from_email
    attachments = email_obj.get("attachments") or []
    signature = extract_signature(body)
    hits = regex_hits(body + "\n" + signature)
    return {
        "from_email": from_email,
        "from_name": from_name,
        "subject": subject,
        "body_text": body,
        "signature_block": signature,
        "attachments": [
            {
                "filename": a.get("filename"),
                "mime_type": a.get("mime_type"),
                "size_bytes": a.get("size_bytes"),
                "category": classify_attachment(a.get("filename", ""), a.get("mime_type")),
            }
            for a in attachments
        ],
        "regex_hits": hits,
    }
