"""
Copilot Engine: unified logic for intent detection, email search, and response.
This is the brain that powers both /api/chat and /api/copilot/* endpoints.
"""
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from backend.database import get_db
from backend.email_service import EmailService
from backend.fuzzy import normalize, extract_potential_names
from backend.routes.copilot import _find_matching_entities, _build_queries, load_aliases
from backend.learning import get_sender_emails, learn_from_search, learn_sender

logger = logging.getLogger(__name__)
email_service = EmailService()


# ============================================================
# INTENT DETECTION - SMART & COMPREHENSIVE
# ============================================================

class Intent:
    SEARCH_EMAIL = "search_email"
    SEND_EMAIL = "send_email"
    DOWNLOAD_ATTACHMENT = "download_attachment"
    REPLY_EMAIL = "reply_email"
    EXTRACT_INFO = "extract_info"
    CREATE_REMINDER = "create_reminder"
    OPEN_EMAIL = "open_email"
    COUNT_ANALYZE = "count_analyze"  # for counting/analyzing
    CREATE_AUTOMATION = "create_automation"  # for creating scheduled automations
    GENERAL_QUESTION = "general_question"


def detect_intent(message: str) -> Tuple[str, Dict[str, Any]]:
    """
    Detect user intent from message using smart pattern matching.
    Returns (intent_type, extracted_data).

    PRIORITY ORDER:
    1. COUNT/ANALYZE - "combien", "nombre de" (even if "télécharger" mentioned)
    2. DOWNLOAD - explicit download commands
    3. SEARCH - find emails
    4. REPLY/SEND - email composition
    5. GENERAL - default
    """
    msg = normalize(message)
    original = message
    msg_lower = message.lower()

    # Extract entities upfront
    names = extract_potential_names(original)

    # ============================================================
    # 0. CREATE AUTOMATION (HIGHEST PRIORITY)
    # "crée une automatisation", "chaque semaine", etc.
    # ============================================================
    automation_patterns = [
        r"(crée|créer|créez|fais|faire|met|mets|mettre)\s*(en place)?\s*(une?|l[ea])?\s*automatisation",
        r"automatise",
        r"chaque\s+(semaine|jour|mois|lundi|mardi|mercredi|jeudi|vendredi).*(récupère|cherche|télécharge|facture)",
        r"(récupère|cherche|télécharge).*chaque\s+(semaine|jour|mois)",
        r"tous\s+les\s+(jours|semaines|mois|lundis?|mardis?).*facture",
        r"surveille.*et.*(alerte|notifie|préviens)",
        r"met.*dans.*tableau.*chaque",
        r"(envoie|envoi).*rapport.*chaque",
    ]

    for pattern in automation_patterns:
        if re.search(pattern, msg_lower, re.I):
            return Intent.CREATE_AUTOMATION, {
                "query_text": original,
                "entities": names
            }

    # ============================================================
    # 1. EXTRACT INFO - "dis moi le montant", "quel est le total"
    # User wants to extract specific data from an attachment
    # ============================================================
    extract_patterns = [
        r"(dis|donne|montre).*?(montant|total|prix|somme)",
        r"(quel|quelle).*?(montant|total|prix|somme)",
        r"(montant|total|prix)\s+(de|du|des|la|le)",
        r"c.?est\s+combien",
        r"combien.*?(coute|coûte|fait|€|euro)",
    ]

    for pattern in extract_patterns:
        if re.search(pattern, msg, re.I):
            return Intent.EXTRACT_INFO, {
                "query_text": original,
                "entities": names,
                "extract_type": "amount"
            }

    count_patterns = [
        r"combien",
        r"nombre\s+de",
        r"compte.*?(facture|mail|email|devis)",
        r"total\s+de",
        r"liste.*?(facture|mail|email|devis)",
        r"recapitulatif",
        r"résumé",
        r"resume",
        r"y.a.t.il",
        r"est.ce.qu.*?(il\s+y\s+a|j.ai)",
        r"j.ai\s+(combien|quoi)",
        r"qu.?est.?ce\s+que\s+j.?ai",
    ]

    for pattern in count_patterns:
        if re.search(pattern, msg, re.I):
            return Intent.COUNT_ANALYZE, {
                "query_text": original,
                "entities": names
            }

    # ============================================================
    # 2. DOWNLOAD / TÉLÉCHARGEMENT
    # Explicit download commands: "télécharge les", "récupère les factures"
    # ============================================================
    download_keywords = [
        "telecharge", "télécharge", "telechargement", "téléchargement",
        "download", "recupere", "récupère", "recup", "récup",
        "prends", "attrape", "choppe", "dl"
    ]

    # Check for download intent
    has_download_word = any(kw in msg for kw in download_keywords)
    has_file_context = any(kw in msg for kw in [
        "facture", "devis", "pj", "piece", "pièce", "fichier",
        "document", "pdf", "excel", "attachment", "joint"
    ])

    if has_download_word or (has_file_context and "telecharge" in msg_lower):
        return Intent.DOWNLOAD_ATTACHMENT, {
            "query_text": original,
            "entities": names,
            "wants_all": any(kw in msg for kw in ["toutes", "tous", "tout", "all", "chaque", "ensemble"])
        }

    # ============================================================
    # 3. SEARCH / FIND (trouve, cherche, montre, affiche)
    # ============================================================
    search_triggers = [
        # Direct search commands
        r"(trouve|cherche|montre|affiche|donne|vois|regarde)",
        # Questions about emails
        r"(ou\s+est|c.est\s+quoi|quel|quelle)",
        # Document types (implies search)
        r"(facture|devis|contrat|rib|kbis|attestation|releve|relevé)",
        # Temporal searches
        r"(dernier|dernière|avant.dernier|recent|récent)",
        # From someone
        r"(mail|email|message|courrier)\s+(de|du|d')",
        # Check if received
        r"(recu|reçu|eu|arrivé)\s+(un\s+)?(mail|email|facture)",
    ]

    for pattern in search_triggers:
        if re.search(pattern, msg, re.I):
            return Intent.SEARCH_EMAIL, {
                "query_text": original,
                "entities": names
            }

    # ============================================================
    # 4. REPLY (réponds, dis-lui, écris-lui)
    # ============================================================
    reply_patterns = [
        r"(repond|répond|repondre|répondre|reply)",
        r"dis[\s-]lui",
        r"ecris[\s-]lui",
        r"écris[\s-]lui",
        r"envoie[\s-]lui",
    ]

    for pattern in reply_patterns:
        if re.search(pattern, msg, re.I):
            return Intent.REPLY_EMAIL, {
                "query_text": original,
                "entities": names
            }

    # ============================================================
    # 5. SEND EMAIL (envoie, écris, rédige un mail)
    # ============================================================
    send_patterns = [
        r"(envoie|envoi|ecris|écris|redige|rédige)\s+(un\s+)?(mail|email|message)",
        r"(relance|rappel)\s+(pour|concernant|sur|à)",
        r"fais\s+un\s+(mail|email)",
    ]

    for pattern in send_patterns:
        if re.search(pattern, msg, re.I):
            return Intent.SEND_EMAIL, {"query_text": original, "entities": names}

    # ============================================================
    # 6. OPEN EMAIL (ouvre, lis, affiche ce mail)
    # ============================================================
    if re.search(r"(ouvre|ouvrir|lis|lire|affiche)\s+(le|ce|cet)?\s*(mail|email|message)", msg, re.I):
        return Intent.OPEN_EMAIL, {"query_text": original, "entities": names}

    # ============================================================
    # 7. FALLBACK - Check for any document/email mention = SEARCH
    # ============================================================
    if any(kw in msg for kw in ["facture", "devis", "mail", "email", "message", "courrier"]):
        return Intent.SEARCH_EMAIL, {"query_text": original, "entities": names}

    # ============================================================
    # 8. DEFAULT
    # ============================================================
    return Intent.GENERAL_QUESTION, {"query_text": original}


# ============================================================
# TEMPORAL PARSING - COMPREHENSIVE FRENCH SUPPORT
# ============================================================

def parse_temporal_reference(text: str) -> Optional[str]:
    """
    Parse French temporal references into Gmail date filters.
    Returns Gmail query fragment like 'after:2025/01/01 before:2025/12/31'
    """
    text_lower = text.lower()
    now = datetime.now()

    # Mois en français
    months_fr = {
        "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
        "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
        "septembre": 9, "octobre": 10, "novembre": 11,
        "decembre": 12, "décembre": 12, "dec": 12, "déc": 12
    }

    # Specific year mentioned (2024, 2025, etc.)
    year_match = re.search(r'\b(20[0-9]{2})\b', text)
    if year_match:
        year = year_match.group(1)
        # Check if also has month
        for month_name, month_num in months_fr.items():
            if month_name in text_lower:
                if month_num == 12:
                    return f"after:{year}/12/01 before:{int(year)+1}/01/01"
                else:
                    return f"after:{year}/{month_num:02d}/01 before:{year}/{month_num+1:02d}/01"
        return f"after:{year}/01/01 before:{year}/12/31"

    # "cette année" / "cette annee"
    if "cette ann" in text_lower or "l'année en cours" in text_lower or "cette annee" in text_lower:
        return f"after:{now.year}/01/01"

    # "le mois dernier" / "mois précédent"
    if "mois dernier" in text_lower or "mois prec" in text_lower or "mois passé" in text_lower:
        first_of_month = now.replace(day=1)
        last_month_end = first_of_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return f"after:{last_month_start.strftime('%Y/%m/%d')} before:{first_of_month.strftime('%Y/%m/%d')}"

    # "ce mois" / "ce mois-ci"
    if "ce mois" in text_lower:
        first_of_month = now.replace(day=1)
        return f"after:{first_of_month.strftime('%Y/%m/%d')}"

    # "cette semaine"
    if "cette semaine" in text_lower:
        start_of_week = now - timedelta(days=now.weekday())
        return f"after:{start_of_week.strftime('%Y/%m/%d')}"

    # "semaine dernière"
    if "semaine dern" in text_lower:
        start_of_week = now - timedelta(days=now.weekday())
        prev_week_start = start_of_week - timedelta(days=7)
        return f"after:{prev_week_start.strftime('%Y/%m/%d')} before:{start_of_week.strftime('%Y/%m/%d')}"

    # Month names - "en décembre", "de décembre", just "décembre"
    for month_name, month_num in months_fr.items():
        if month_name in text_lower:
            # Determine year - if month is in future, use last year
            year = now.year if month_num <= now.month else now.year - 1
            # Get next month for end date
            if month_num == 12:
                next_month = 1
                next_year = year + 1
            else:
                next_month = month_num + 1
                next_year = year
            return f"after:{year}/{month_num:02d}/01 before:{next_year}/{next_month:02d}/01"

    # "depuis [mois]"
    for month_name, month_num in months_fr.items():
        if f"depuis {month_name}" in text_lower:
            year = now.year if month_num <= now.month else now.year - 1
            return f"after:{year}/{month_num:02d}/01"

    # "récent" / "récemment"
    if "recent" in text_lower or "récen" in text_lower:
        thirty_days_ago = now - timedelta(days=30)
        return f"after:{thirty_days_ago.strftime('%Y/%m/%d')}"

    # "hier"
    if "hier" in text_lower:
        yesterday = now - timedelta(days=1)
        return f"after:{yesterday.strftime('%Y/%m/%d')} before:{now.strftime('%Y/%m/%d')}"

    # "aujourd'hui"
    if "aujourd" in text_lower:
        return f"after:{now.strftime('%Y/%m/%d')}"

    # Trimestres Q1, Q2, Q3, Q4
    quarter_match = re.search(r'\b[qQt]([1-4])\b', text)
    if quarter_match:
        q = int(quarter_match.group(1))
        start_month = (q - 1) * 3 + 1
        end_month = q * 3
        year = now.year
        return f"after:{year}/{start_month:02d}/01 before:{year}/{end_month:02d}/31"

    return None


# ============================================================
# SMART EMAIL SEARCH (unified)
# ============================================================

async def smart_search(
    user_id: str,
    query_text: str,
    account_id: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Unified smart email search.
    Uses memory (aliases, contacts, vendors) to build optimal queries.
    ALWAYS tries multiple fallbacks until finding results.
    """
    db = await get_db()
    query_lower = normalize(query_text)

    # Find account
    account = None
    if account_id:
        account = await db.accounts.find_one({"account_id": account_id})
    if not account:
        account = await db.accounts.find_one(
            {"user_id": user_id, "$or": [{"provider": "gmail"}, {"type": "gmail"}]}
        )

    if not account:
        return {
            "success": False,
            "error": "no_account",
            "message": "Aucun compte Gmail connecté."
        }

    # STEP 1: Resolve aliases and contacts
    names = extract_potential_names(query_text)
    resolved_emails = []
    resolved_names = []

    for name in names:
        ref = await resolve_reference(user_id, name)
        if ref.get("resolved") and ref.get("email"):
            resolved_emails.append(ref["email"])
            resolved_names.append(ref.get("name", name))

    # Scan for ALL known aliases in the query text
    all_aliases = await db.aliases.find({"user_id": user_id}).to_list(100)
    for alias in all_aliases:
        alias_key = normalize(alias.get("key", ""))
        if alias_key and alias_key in query_lower:
            if alias.get("value") and alias["value"] not in resolved_emails:
                resolved_emails.append(alias["value"])
                resolved_names.append(alias.get("key", ""))
                logger.info(f"Found alias '{alias['key']}' -> {alias['value']}")

    # Check common keywords
    alias_keywords = ["comptable", "avocat", "banque", "assurance", "fournisseur"]
    for keyword in alias_keywords:
        if keyword in query_lower:
            alias = await db.aliases.find_one({"user_id": user_id, "key": keyword})
            if alias and alias.get("value"):
                if alias["value"] not in resolved_emails:
                    resolved_emails.append(alias["value"])
                    resolved_names.append(keyword)

    # STEP 1.5: Check LEARNED sender mappings
    # This uses the learning system to find known senders
    words_to_check = [w for w in query_text.lower().split() if len(w) > 3]
    for word in words_to_check:
        # Skip common words
        if word in ["facture", "factures", "devis", "mail", "email", "dernier", "derniere",
                    "toutes", "tous", "tout", "telecharge", "trouve", "cherche", "semaine"]:
            continue
        learned_emails = await get_sender_emails(user_id, word)
        for email in learned_emails:
            if email not in resolved_emails:
                resolved_emails.append(email)
                resolved_names.append(word)
                logger.info(f"📚 Found learned sender '{word}' -> {email}")

    # STEP 2: Parse temporal and build queries
    temporal_filter = parse_temporal_reference(query_text)

    # Detect document type
    doc_subject = ""
    if any(kw in query_lower for kw in ["facture", "factures"]):
        doc_subject = "subject:facture"
    elif any(kw in query_lower for kw in ["devis"]):
        doc_subject = "subject:devis"
    elif any(kw in query_lower for kw in ["releve", "relevé"]):
        doc_subject = "subject:relevé OR subject:releve"

    # Default to current year for accounting queries if no temporal specified
    if not temporal_filter:
        is_accounting = any(kw in query_lower for kw in [
            "facture", "devis", "paiement", "reglement", "comptab"
        ])
        if is_accounting:
            temporal_filter = f"after:{datetime.now().year}/01/01"

    logger.info(f"Smart search: temporal={temporal_filter}, subject={doc_subject}, names={names}, resolved={resolved_emails}")

    # STEP 3: Build query list - CORRECT PRIORITY ORDER
    queries_to_try = []

    # ==== PRIORITY 1: Resolved emails FIRST (known contacts/vendors) ====
    # If we know who the user is looking for, search them first!
    if resolved_emails:
        for email in resolved_emails[:3]:
            base = f"from:{email}"
            if temporal_filter and doc_subject:
                queries_to_try.append(f"{temporal_filter} {doc_subject} {base}")
            if temporal_filter:
                queries_to_try.append(f"{temporal_filter} {base}")
            if doc_subject:
                queries_to_try.append(f"{doc_subject} {base}")
            queries_to_try.append(base)

    # ==== PRIORITY 2: Document type + temporal (if no specific sender) ====
    if doc_subject and temporal_filter:
        queries_to_try.append(f"{temporal_filter} {doc_subject}")

    # ==== PRIORITY 3: Just document type or just temporal ====
    if doc_subject:
        queries_to_try.append(doc_subject)
    if temporal_filter:
        queries_to_try.append(temporal_filter)

    # ==== PRIORITY 4: Name-based queries (proper names only) ====
    # Filter out garbage extractions
    skip_words = [
        "facture", "factures", "devis", "mail", "email", "message",
        "combien", "telecharger", "télécharger", "download", "récupère",
        "trouve", "cherche", "montre", "affiche", "donne",
        "décembre", "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre",
        "toutes", "tous", "tout", "les", "des", "une", "mon", "ma",
        "j'ai", "ai", "de", "à", "en", "du", "la", "le"
    ]

    for name in names[:3]:
        name_lower = name.lower().strip()
        # Skip if it's a common word or too short
        if name_lower in skip_words or len(name_lower) < 3:
            continue
        # Skip if it contains common query words
        if any(sw in name_lower for sw in ["facture", "combien", "telecharge", "décembre"]):
            continue

        # Try both from: AND subject: for vendor names
        from_base = f'from:"{name}"'
        subject_base = f'subject:"{name}"'

        # Priority: from + temporal + doc
        if temporal_filter and doc_subject:
            queries_to_try.append(f"{temporal_filter} {doc_subject} {from_base}")
            queries_to_try.append(f"{temporal_filter} {doc_subject} {subject_base}")
        if temporal_filter:
            queries_to_try.append(f"{temporal_filter} {from_base}")
            queries_to_try.append(f"{temporal_filter} {subject_base}")
        if doc_subject:
            queries_to_try.append(f"{doc_subject} {from_base}")
            queries_to_try.append(f"{doc_subject} {subject_base}")
        queries_to_try.append(from_base)
        queries_to_try.append(subject_base)
        # Also search anywhere
        queries_to_try.append(f'"{name}"')

    # Fallback: use _build_queries
    query_defs = await _build_queries(query_text, user_id)
    for qdef in query_defs:
        if qdef["query"] not in queries_to_try:
            queries_to_try.append(qdef["query"])

    # STEP 4: Execute queries until we find results
    results = []
    queries_tried = []

    for q in queries_to_try[:20]:  # Try up to 20 queries
        queries_tried.append(q)
        try:
            emails = await email_service.search_emails(account["account_id"], q)
            if emails:
                results = emails[:limit]
                logger.info(f"Found {len(results)} results with query: {q}")
                break
        except Exception as e:
            logger.warning(f"Search query failed: {q} - {e}")
            continue

    # Get entity info
    entities = await _find_matching_entities(query_text, user_id)

    # LEARN from successful search results
    if results:
        try:
            await learn_from_search(user_id, query_text, results)
        except Exception as e:
            logger.warning(f"Learning from search failed: {e}")

    return {
        "success": bool(results),
        "results": results,
        "count": len(results),
        "queries_tried": queries_tried,
        "query_used": queries_tried[-1] if queries_tried and results else None,
        "resolved_emails": resolved_emails,
        "resolved_names": resolved_names,
        "temporal_filter": temporal_filter,
        "entities": {
            "vendors_matched": [v["name"] for v in entities.get("vendors", [])],
            "contacts_matched": [c.get("name") or c.get("email") for c in entities.get("contacts", [])],
            "aliases_used": [a["key"] for a in entities.get("aliases", [])],
        },
        "account": {
            "account_id": account["account_id"],
            "email": account.get("email")
        }
    }


async def resolve_reference(user_id: str, text: str) -> Dict[str, Any]:
    """
    Resolve a text reference (alias, contact name, vendor) to email.
    """
    db = await get_db()
    key = normalize(text)

    # Check alias first
    alias = await db.aliases.find_one({"user_id": user_id, "key": key})
    if alias:
        return {
            "resolved": True,
            "email": alias["value"],
            "source": "alias",
            "name": key
        }

    # Check contacts
    regex = {"$regex": re.escape(key), "$options": "i"}
    contact = await db.contacts.find_one(
        {"user_id": user_id, "$or": [{"name": regex}, {"email": regex}, {"first_name": regex}, {"last_name": regex}]}
    )
    if contact and contact.get("email"):
        return {
            "resolved": True,
            "email": contact["email"],
            "source": "contact",
            "name": contact.get("name") or f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
        }

    # Check vendors
    vendor = await db.vendors.find_one(
        {"user_id": user_id, "$or": [{"name": regex}, {"keywords": regex}]}
    )
    if vendor and vendor.get("last_invoice_email"):
        return {
            "resolved": True,
            "email": vendor["last_invoice_email"],
            "source": "vendor",
            "name": vendor.get("name")
        }

    return {"resolved": False}


# ============================================================
# BUILD CONTEXT FOR LLM
# ============================================================

async def build_action_context(
    user_id: str,
    message: str,
    accounts: List[Dict[str, Any]],
    active_email: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build complete context for LLM including search results, resolved refs, etc.
    This is called before invoking the LLM.
    """
    intent, intent_data = detect_intent(message)
    msg_lower = message.lower()

    context = {
        "intent": intent,
        "intent_data": intent_data,
        "tool_results": "",
        "resolved_refs": [],
        "search_results": [],
        "active_email": active_email,
        "email_details": None,
        "attachments": [],
        "suggested_actions": [],
        "count": 0,
    }

    # Get default account
    account = next((a for a in accounts if a.get("type") == "gmail"), accounts[0] if accounts else None)
    account_id = account.get("account_id") if account else None

    # Handle all search-related intents
    if intent in [Intent.SEARCH_EMAIL, Intent.OPEN_EMAIL, Intent.DOWNLOAD_ATTACHMENT, Intent.COUNT_ANALYZE, Intent.EXTRACT_INFO]:

        # For EXTRACT_INFO - extract data from PDF attachments
        if intent == Intent.EXTRACT_INFO and active_email and active_email.get("attachments"):
            # Try to extract data from PDF attachments
            for att in active_email.get("attachments", []):
                if att.get("mimeType") == "application/pdf" or att.get("filename", "").lower().endswith('.pdf'):
                    try:
                        invoice_data = await email_service.extract_invoice_data(
                            account_id,
                            active_email["id"],
                            att.get("attachmentId")
                        )
                        if invoice_data.get("total"):
                            total = invoice_data["total"]
                            context["tool_results"] = (
                                f"**Facture analysée:** {att.get('filename')}\n\n"
                                f"**Montant total: {total['formatted']}**\n\n"
                            )
                            if invoice_data.get("invoice_number"):
                                context["tool_results"] += f"N° Facture: {invoice_data['invoice_number']}\n"
                            if invoice_data.get("amounts") and len(invoice_data["amounts"]) > 1:
                                context["tool_results"] += "\nAutres montants trouvés:\n"
                                for amt in invoice_data["amounts"][1:4]:
                                    context["tool_results"] += f"- {amt['formatted']}\n"
                            context["extracted_data"] = invoice_data
                            context["email_details"] = active_email
                            return context
                        else:
                            context["tool_results"] = f"PDF analysé ({att.get('filename')}) mais aucun montant trouvé."
                    except Exception as e:
                        logger.warning(f"Could not extract invoice data: {e}")
                        context["tool_results"] = f"Erreur lors de l'analyse du PDF: {e}"
            # If no PDF found or extraction failed, continue with search
            if not context.get("tool_results"):
                context["tool_results"] = "Aucun PDF trouvé dans l'email actif."

        # For DOWNLOAD with active email context only (no search terms)
        if intent == Intent.DOWNLOAD_ATTACHMENT and active_email and active_email.get("id"):
            short_msg = len(message.split()) <= 4  # "telecharge les" is short
            if short_msg:
                context["target_email"] = active_email
                context["email_details"] = active_email
                if not active_email.get("attachments") and account_id:
                    try:
                        full_email = await get_email_with_attachments(account_id, active_email["id"])
                        context["email_details"] = full_email
                        context["attachments"] = full_email.get("attachments", [])
                    except Exception as e:
                        logger.warning(f"Could not fetch attachments: {e}")
                else:
                    context["attachments"] = active_email.get("attachments", [])

                att_count = len(context["attachments"])
                context["tool_results"] = f"{att_count} pièce(s) jointe(s) disponible(s)"
                context["suggested_actions"] = ["download_attachments"]
                return context

        # Search for emails
        search_result = await smart_search(user_id, message, account_id, limit=500)

        if search_result["success"] and search_result["results"]:
            emails = search_result["results"]
            context["search_results"] = emails
            context["count"] = len(emails)

            # Check if user wants ALL emails
            wants_all = intent_data.get("wants_all") or any(kw in msg_lower for kw in ["toutes", "tous", "tout", "all", "chaque"])

            # Handle "avant-dernier"
            target_index = 0
            if "avant-dernier" in msg_lower or "avant dernier" in msg_lower:
                target_index = 1 if len(emails) > 1 else 0
            elif "dernier" in msg_lower and not wants_all:
                target_index = 0

            # COUNT/ANALYZE intent - count, summarize, AND prepare for download
            if intent == Intent.COUNT_ANALYZE:
                context["tool_results"] = f"{len(emails)} email(s) trouvé(s)"

                # Collect emails with attachments for potential download
                all_attachments = []
                emails_with_attachments_list = []

                for email in emails:  # Check ALL emails
                    if account_id and email.get("id"):
                        try:
                            full = await get_email_with_attachments(account_id, email["id"])
                            atts = full.get("attachments", [])
                            if atts:
                                for att in atts:
                                    att["email_subject"] = email.get("subject", "")
                                    att["email_id"] = email.get("id")
                                all_attachments.extend(atts)
                                emails_with_attachments_list.append({**email, "attachments": atts})
                        except:
                            pass

                if emails_with_attachments_list:
                    context["tool_results"] += f"\n{len(emails_with_attachments_list)} email(s) avec pièces jointes ({len(all_attachments)} fichiers au total)"

                    # Prepare for multi-email download
                    context["attachments"] = all_attachments
                    context["emails_with_attachments"] = emails_with_attachments_list
                    context["multi_email"] = True
                    context["email_details"] = emails_with_attachments_list[0]  # First email for panel
                    context["target_email"] = emails_with_attachments_list[0]

                # Add list to tool_results
                context["tool_results"] += "\n\nEmails:\n"
                for i, e in enumerate(emails, 1):
                    # Mark which ones have attachments
                    has_att = any(ea.get("id") == e.get("id") for ea in emails_with_attachments_list)
                    att_marker = " (PJ)" if has_att else ""
                    context["tool_results"] += f"{i}. {e.get('subject', 'Sans objet')} - {e.get('date', '')}{att_marker}\n"

                context["suggested_actions"] = ["download_attachments"] if all_attachments else []

            # EXTRACT_INFO intent - search, get PDF, extract data from ALL matching emails
            elif intent == Intent.EXTRACT_INFO:
                extracted_invoices = []
                all_attachments = []
                total_sum = 0.0

                # Process ALL emails, not just the first one
                for target_email in emails:
                    logger.info(f"📄 EXTRACT_INFO: Processing email {target_email.get('subject')}")

                    if account_id and target_email.get("id"):
                        try:
                            full_email = await get_email_with_attachments(account_id, target_email["id"])
                            logger.info(f"📄 Email has {len(full_email.get('attachments', []))} attachments")

                            # Try to extract data from PDF attachments
                            for att in full_email.get("attachments", []):
                                # Skip CGV and non-invoice PDFs
                                filename = att.get("filename", "").lower()
                                if "cgv" in filename or "condition" in filename:
                                    continue

                                logger.info(f"📄 Checking attachment: {att.get('filename')} ({att.get('mimeType')})")
                                if att.get("mimeType") == "application/pdf" or filename.endswith('.pdf'):
                                    try:
                                        invoice_data = await email_service.extract_invoice_data(
                                            account_id,
                                            target_email["id"],
                                            att.get("attachmentId")
                                        )
                                        if invoice_data.get("total"):
                                            total = invoice_data["total"]
                                            extracted_invoices.append({
                                                "subject": target_email.get("subject", "N/A"),
                                                "from": target_email.get("from", "N/A"),
                                                "date": target_email.get("date", "N/A"),
                                                "total": total,
                                                "invoice_number": invoice_data.get("invoice_number")
                                            })
                                            total_sum += total.get("value", 0)
                                            # Add attachment for download
                                            att["email_subject"] = target_email.get("subject", "")
                                            att["email_id"] = target_email.get("id")
                                            all_attachments.append(att)
                                            break  # Only need first valid invoice per email
                                    except Exception as e:
                                        logger.warning(f"Could not extract invoice data: {e}")
                        except Exception as e:
                            logger.warning(f"Could not fetch email {target_email.get('id')}: {e}")

                context["attachments"] = all_attachments
                context["multi_email"] = len(extracted_invoices) > 1

                if extracted_invoices:
                    # Format results for multiple invoices
                    if len(extracted_invoices) == 1:
                        inv = extracted_invoices[0]
                        context["tool_results"] = (
                            f"**Facture:** {inv['subject']}\n"
                            f"**De:** {inv['from']}\n"
                            f"**Date:** {inv['date']}\n\n"
                            f"**Montant total: {inv['total']['formatted']}**\n\n"
                        )
                    else:
                        # Multiple invoices - list all with amounts
                        context["tool_results"] = f"**{len(extracted_invoices)} factures trouvées**\n\n"
                        for i, inv in enumerate(extracted_invoices, 1):
                            context["tool_results"] += (
                                f"{i}. {inv['subject']} - {inv['date']}\n"
                                f"   **Montant: {inv['total']['formatted']}**\n\n"
                            )
                        # Add total sum
                        formatted_sum = f"{total_sum:,.2f} €".replace(",", " ").replace(".", ",")
                        context["tool_results"] += f"**TOTAL: {formatted_sum}**\n"

                    context["extracted_data"] = extracted_invoices
                else:
                    context["tool_results"] = (
                        f"{len(emails)} email(s) trouvé(s) mais pas de montant détecté dans les PDF."
                    )

            # DOWNLOAD intent with "wants_all"
            elif wants_all and intent == Intent.DOWNLOAD_ATTACHMENT and len(emails) > 1:
                all_attachments = []
                emails_with_attachments = []

                for email in emails:  # ALL emails
                    if account_id and email.get("id"):
                        try:
                            full_email = await get_email_with_attachments(account_id, email["id"])
                            email_atts = full_email.get("attachments", [])
                            if email_atts:
                                for att in email_atts:
                                    att["email_subject"] = email.get("subject", "")
                                    att["email_id"] = email.get("id")
                                all_attachments.extend(email_atts)
                                emails_with_attachments.append({**email, "attachments": email_atts})
                        except Exception as e:
                            logger.warning(f"Could not fetch email {email.get('id')}: {e}")

                context["attachments"] = all_attachments
                context["emails_with_attachments"] = emails_with_attachments
                context["multi_email"] = True

                context["tool_results"] = (
                    f"{len(emails_with_attachments)} email(s) avec pièces jointes\n"
                    f"{len(all_attachments)} fichier(s) à télécharger\n\n"
                )
                for i, e in enumerate(emails_with_attachments, 1):
                    att_count = len(e.get("attachments", []))
                    context["tool_results"] += f"{i}. {e.get('subject', 'N/A')} ({att_count} PJ)\n"

            # Single email mode
            else:
                target_email = emails[target_index] if len(emails) > target_index else emails[0]
                context["target_email"] = target_email

                if account_id and target_email.get("id"):
                    try:
                        full_email = await get_email_with_attachments(account_id, target_email["id"])
                        context["email_details"] = full_email
                        context["attachments"] = full_email.get("attachments", [])
                    except Exception as e:
                        logger.warning(f"Could not fetch full email: {e}")

                context["tool_results"] = (
                    f"De: {target_email.get('from', 'N/A')}\n"
                    f"Sujet: {target_email.get('subject', 'N/A')}\n"
                    f"Date: {target_email.get('date', 'N/A')}\n"
                    f"Aperçu: {target_email.get('snippet', 'N/A')}"
                )

                if context["attachments"]:
                    context["tool_results"] += f"\n\n{len(context['attachments'])} pièce(s) jointe(s)"

                if len(emails) > 1:
                    context["tool_results"] += f"\n\n({len(emails)} résultats au total)"

                context["suggested_actions"] = ["open", "reply"]
                if context["attachments"]:
                    context["suggested_actions"].insert(0, "download_attachments")

        else:
            context["tool_results"] = (
                f"Aucun email trouvé.\n"
                f"Recherches effectuées: {', '.join(search_result.get('queries_tried', [])[:3])}"
            )

    elif intent == Intent.CREATE_AUTOMATION:
        # Handle automation creation
        from backend.automations.parser import parse_automation_request, format_automation_summary
        from backend.automations.engine import automation_engine

        config = parse_automation_request(message)

        if config:
            # Get account ID
            account = next((a for a in accounts if a.get("type") == "gmail" or a.get("provider") == "gmail"), accounts[0] if accounts else None)
            account_id = account.get("account_id") if account else None

            if account_id:
                try:
                    result = await automation_engine.create_automation(
                        user_id=user_id,
                        account_id=account_id,
                        config=config
                    )
                    context["automation_created"] = result
                    context["tool_results"] = (
                        f"**Automatisation créée** ✓\n\n"
                        f"{result['summary']}\n\n"
                        f"📊 Tableau **{result['table_name']}** initialisé\n\n"
                        f"[Voir les automatisations →]"
                    )
                    context["suggested_actions"] = ["view_automations", "run_now"]
                except Exception as e:
                    logger.error(f"Failed to create automation: {e}")
                    context["tool_results"] = f"Erreur lors de la création de l'automatisation: {str(e)}"
            else:
                context["tool_results"] = "Connecte d'abord un compte email pour créer des automatisations."
        else:
            context["tool_results"] = (
                "Je n'ai pas compris la demande d'automatisation.\n"
                "Exemple: \"Crée une automatisation qui récupère chaque semaine les factures de Distram et Promocash\""
            )

    elif intent == Intent.REPLY_EMAIL:
        if active_email:
            context["active_email"] = active_email
            context["tool_results"] = (
                f"Réponse à: {active_email.get('from', 'N/A')}\n"
                f"Sujet: {active_email.get('subject', 'N/A')}"
            )
            context["suggested_actions"] = ["compose_reply"]
        else:
            names = extract_potential_names(message)
            for name in names:
                ref = await resolve_reference(user_id, name)
                if ref["resolved"]:
                    context["resolved_refs"].append(ref)

    elif intent == Intent.SEND_EMAIL:
        names = extract_potential_names(message)
        for name in names:
            ref = await resolve_reference(user_id, name)
            if ref["resolved"]:
                context["resolved_refs"].append(ref)
        context["suggested_actions"] = ["compose_email"]

    return context


async def get_email_with_attachments(account_id: str, message_id: str) -> Dict[str, Any]:
    """Fetch full email details including attachments info."""
    try:
        full_email = await email_service.get_email_by_id(account_id, message_id)
        return full_email
    except Exception as e:
        logger.error(f"Error fetching email: {e}")
        return {}


def format_results_for_llm(context: Dict[str, Any]) -> str:
    """Format context as text for LLM prompt."""
    parts = []

    if context.get("tool_results"):
        parts.append(context["tool_results"])

    if context.get("resolved_refs"):
        refs = context["resolved_refs"]
        parts.append("\nContacts résolus:")
        for ref in refs:
            parts.append(f"- {ref.get('name', 'N/A')}: {ref.get('email', 'N/A')} ({ref.get('source', 'N/A')})")

    return "\n".join(parts) if parts else ""
