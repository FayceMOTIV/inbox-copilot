"""
Memory system: contacts, aliases, vendors.
Auto-learns from email interactions.
"""
import logging
import re
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.database import get_db

logger = logging.getLogger(__name__)

# Email user parts that indicate invoice/billing portals
PORTAL_USERS = {"facturation", "billing", "noreply", "no-reply", "invoices", "factures", "comptabilite"}

# Keywords that suggest a comptable/accountant role
COMPTABLE_KEYWORDS = {"comptable", "comptabilité", "cerfrance", "expert-comptable", "cabinet comptable"}

# Invoice-related subject keywords
INVOICE_KEYWORDS = {"facture", "invoice", "billing", "payment", "paiement", "devis", "quote"}


def _domain(email: Optional[str]) -> Optional[str]:
    """Extract domain from email."""
    if not email or "@" not in email:
        return None
    return email.split("@", 1)[1].lower()


def _user_part(email: Optional[str]) -> Optional[str]:
    """Extract user part from email."""
    if not email or "@" not in email:
        return None
    return email.split("@")[0].lower()


def _calculate_alias_confidence(
    role: Optional[str],
    domain: Optional[str],
    name: Optional[str],
    subject: Optional[str],
    companies: Optional[List[str]]
) -> Dict[str, float]:
    """
    Calculate confidence scores for potential aliases.
    Returns dict of {alias_key: confidence_score}.
    """
    scores = {}

    # Comptable detection
    comptable_score = 0.0
    reasons = []

    if role:
        role_lower = role.lower()
        if any(k in role_lower for k in ["comptable", "accountant", "cfo", "expert-comptable"]):
            comptable_score += 0.5
            reasons.append("role_match")

    if domain:
        if domain.endswith("cerfrance.fr"):
            comptable_score += 0.4
            reasons.append("cerfrance_domain")
        elif any(k in domain for k in ["compta", "expert", "cabinet"]):
            comptable_score += 0.3
            reasons.append("compta_domain")

    if name:
        name_lower = name.lower()
        if any(k in name_lower for k in COMPTABLE_KEYWORDS):
            comptable_score += 0.2
            reasons.append("name_match")

    if companies:
        for c in companies:
            c_lower = c.lower() if c else ""
            if any(k in c_lower for k in ["cerfrance", "fiducial", "kpmg", "pwc", "deloitte", "ey", "mazars"]):
                comptable_score += 0.3
                reasons.append("company_match")
                break

    if comptable_score >= 0.85:
        scores["comptable"] = min(comptable_score, 1.0)
        logger.info(f"Comptable alias detected with confidence {comptable_score}: {reasons}")

    return scores


async def upsert_contact(
    user_id: str,
    email: Optional[str],
    name: Optional[str],
    phones: Optional[List[str]] = None,
    companies: Optional[List[str]] = None,
    role: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
):
    """Upsert a contact in the database."""
    if not email:
        return

    db = await get_db()
    now = datetime.utcnow()

    update = {
        "last_seen_at": now,
    }

    # Only set non-null values
    if name:
        update["name"] = name
    if first_name:
        update["first_name"] = first_name
    if last_name:
        update["last_name"] = last_name
    if role:
        update["role"] = role

    set_on_insert = {
        "user_id": user_id,
        "email": email,
        "created_at": now,
        "seen_count": 0,
    }

    operations = {
        "$set": update,
        "$setOnInsert": set_on_insert,
        "$inc": {"seen_count": 1}
    }

    if phones:
        operations["$addToSet"] = {"phones": {"$each": list(set(p for p in phones if p))}}
    if companies:
        if "$addToSet" not in operations:
            operations["$addToSet"] = {}
        operations["$addToSet"]["companies"] = {"$each": list(set(c for c in companies if c))}

    await db.contacts.update_one(
        {"user_id": user_id, "email": email},
        operations,
        upsert=True
    )


async def upsert_alias(
    user_id: str,
    key: str,
    value: str,
    confidence: float = 1.0,
    auto_created: bool = False
):
    """
    Upsert an alias. Only updates if new confidence is higher or if manual.
    """
    if not key or not value:
        return

    db = await get_db()
    key_normalized = key.lower().strip()
    now = datetime.utcnow()

    # Check existing alias
    existing = await db.aliases.find_one({"user_id": user_id, "key": key_normalized})

    if existing:
        # Only update if:
        # 1. New is manual (not auto_created)
        # 2. Or new confidence is higher than existing
        existing_confidence = existing.get("confidence", 1.0)
        existing_auto = existing.get("auto_created", False)

        if auto_created and existing_confidence >= confidence:
            # Don't override with lower confidence auto-alias
            return
        if not auto_created or confidence > existing_confidence:
            await db.aliases.update_one(
                {"user_id": user_id, "key": key_normalized},
                {"$set": {
                    "value": value,
                    "confidence": confidence,
                    "auto_created": auto_created,
                    "updated_at": now
                }}
            )
    else:
        # Create new alias
        await db.aliases.insert_one({
            "user_id": user_id,
            "key": key_normalized,
            "value": value,
            "confidence": confidence,
            "auto_created": auto_created,
            "created_at": now,
            "updated_at": now
        })
        logger.info(f"Created alias '{key_normalized}' -> '{value}' (confidence: {confidence}, auto: {auto_created})")


async def upsert_vendor(
    user_id: str,
    name: str,
    domain: Optional[str] = None,
    last_invoice_email: Optional[str] = None,
    keywords: Optional[List[str]] = None
):
    """Upsert a vendor in the database."""
    if not name:
        return

    db = await get_db()
    name_normalized = name.lower().strip()
    now = datetime.utcnow()

    update = {
        "updated_at": now,
    }
    if last_invoice_email:
        update["last_invoice_email"] = last_invoice_email

    set_on_insert = {
        "user_id": user_id,
        "name": name_normalized,
        "created_at": now,
        "candidate": False,
    }

    operations = {
        "$set": update,
        "$setOnInsert": set_on_insert,
    }

    if domain:
        operations["$addToSet"] = {"domains": domain}
    if keywords:
        if "$addToSet" not in operations:
            operations["$addToSet"] = {}
        operations["$addToSet"]["keywords"] = {"$each": [k.lower() for k in keywords if k]}

    # Also mark as non-candidate since we have real data
    operations["$set"]["candidate"] = False

    await db.vendors.update_one(
        {"user_id": user_id, "name": name_normalized},
        operations,
        upsert=True
    )


async def process_extraction(
    user_id: str,
    email_obj: Dict[str, Any],
    extraction: Dict[str, Any]
):
    """
    Process email extraction results and update memory.
    Auto-creates contacts, vendors, and aliases based on patterns.
    """
    contact = (extraction or {}).get("contact") or {}
    subject = email_obj.get("subject", "").lower()

    # Extract contact info
    email_addr = contact.get("email") or email_obj.get("from_email")
    first_name = contact.get("first_name")
    last_name = contact.get("last_name")
    name = contact.get("name") or email_obj.get("from_name")
    if not name and (first_name or last_name):
        name = f"{first_name or ''} {last_name or ''}".strip()

    phones = []
    companies = []
    role = contact.get("role")

    regex_hits = (extraction or {}).get("regex_hits") or {}
    if regex_hits:
        phones.extend(regex_hits.get("phones") or [])

    if contact.get("company"):
        companies.append(contact["company"])

    # Upsert contact
    await upsert_contact(
        user_id=user_id,
        email=email_addr,
        name=name,
        phones=phones,
        companies=companies,
        role=role,
        first_name=first_name,
        last_name=last_name
    )

    dom = _domain(email_addr)
    user_part = _user_part(email_addr)

    # Auto-detect vendor from invoice emails
    is_invoice_email = (
        user_part in PORTAL_USERS or
        any(kw in subject for kw in INVOICE_KEYWORDS) or
        email_obj.get("has_pdf_attachment", False)
    )

    if dom and is_invoice_email:
        # Extract vendor name from domain
        vendor_name = dom.split(".")[0]
        # Skip generic domains
        if vendor_name not in {"gmail", "outlook", "yahoo", "hotmail", "orange", "free", "sfr"}:
            await upsert_vendor(
                user_id=user_id,
                name=vendor_name,
                domain=dom,
                last_invoice_email=email_addr,
                keywords=[vendor_name]
            )

    # Auto-create aliases with confidence scoring
    alias_scores = _calculate_alias_confidence(
        role=role,
        domain=dom,
        name=name,
        subject=subject,
        companies=companies
    )

    for alias_key, confidence in alias_scores.items():
        if confidence >= 0.85 and email_addr:
            await upsert_alias(
                user_id=user_id,
                key=alias_key,
                value=email_addr,
                confidence=confidence,
                auto_created=True
            )


async def get_memory_stats(user_id: str) -> Dict[str, int]:
    """Get memory stats for a user."""
    db = await get_db()
    return {
        "contacts": await db.contacts.count_documents({"user_id": user_id}),
        "aliases": await db.aliases.count_documents({"user_id": user_id}),
        "vendors": await db.vendors.count_documents({"user_id": user_id}),
    }
