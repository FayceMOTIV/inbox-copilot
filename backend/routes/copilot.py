"""
Copilot routes: smart search and resolve using memory (vendors, contacts, aliases).
No hardcoded vendor lists - everything from MongoDB.
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.database import get_db
from backend.email_service import EmailService
from backend.fuzzy import normalize, fuzzy_match, extract_potential_names, best_match

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/copilot", tags=["copilot"])
email_service = EmailService()


class SearchRequest(BaseModel):
    account_id: Optional[str] = None
    query_text: str
    user_id: str = "default_user"


class ResolveRequest(BaseModel):
    text: str
    user_id: str = "default_user"


# ============================================================
# MEMORY LOADING
# ============================================================

async def load_vendors(user_id: str) -> List[Dict[str, Any]]:
    """Load all vendors for user from MongoDB."""
    db = await get_db()
    return await db.vendors.find(
        {"user_id": user_id},
        {"_id": 0, "name": 1, "domains": 1, "last_invoice_email": 1, "keywords": 1}
    ).to_list(100)


async def load_contacts(user_id: str) -> List[Dict[str, Any]]:
    """Load all contacts for user from MongoDB."""
    db = await get_db()
    return await db.contacts.find(
        {"user_id": user_id},
        {"_id": 0, "email": 1, "name": 1, "first_name": 1, "last_name": 1, "role": 1, "companies": 1}
    ).to_list(100)


async def load_aliases(user_id: str) -> List[Dict[str, Any]]:
    """Load all aliases for user from MongoDB."""
    db = await get_db()
    return await db.aliases.find(
        {"user_id": user_id},
        {"_id": 0, "key": 1, "value": 1, "confidence": 1}
    ).to_list(100)


# ============================================================
# SMART QUERY BUILDER (uses memory, no hardcode)
# ============================================================

def _detect_time_range(query_text: str) -> str:
    """Detect time range from query."""
    ql = normalize(query_text)
    if "mois dernier" in ql or "mois passe" in ql or "last month" in ql:
        return "newer_than:60d"
    if "semaine" in ql or "week" in ql:
        return "newer_than:14d"
    if "annee" in ql or "year" in ql or "ancien" in ql:
        return "newer_than:365d"
    if "hier" in ql or "yesterday" in ql:
        return "newer_than:2d"
    return "newer_than:30d"


def _detect_doc_type(query_text: str) -> Optional[str]:
    """Detect document type keywords."""
    ql = normalize(query_text)
    if any(k in ql for k in ["facture", "invoice", "billing"]):
        return "(facture OR invoice) filename:pdf"
    if any(k in ql for k in ["devis", "quote", "estimation"]):
        return "(devis OR quote) filename:pdf"
    if any(k in ql for k in ["contrat", "contract"]):
        return "(contrat OR contract) filename:pdf"
    if any(k in ql for k in ["rib", "bank"]):
        return "(RIB OR IBAN) filename:pdf"
    if any(k in ql for k in ["kbis"]):
        return "kbis filename:pdf"
    return None


async def _find_matching_entities(
    query_text: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Find vendors, contacts, aliases matching terms in query.
    Returns enrichment data for Gmail query.
    """
    vendors = await load_vendors(user_id)
    contacts = await load_contacts(user_id)
    aliases = await load_aliases(user_id)

    # Extract potential names from query
    potential_names = extract_potential_names(query_text)
    ql = normalize(query_text)

    matched_vendors = []
    matched_contacts = []
    matched_aliases = []
    unknown_terms = []

    # Check aliases first (exact match on key)
    for alias in aliases:
        if normalize(alias["key"]) in ql:
            matched_aliases.append(alias)

    # Check vendors (fuzzy match on name/domains/keywords)
    vendor_names = [v["name"] for v in vendors]
    for name in potential_names:
        match = best_match(name, vendor_names, cutoff=0.5)
        if match:
            vendor = next((v for v in vendors if v["name"] == match), None)
            if vendor and vendor not in matched_vendors:
                matched_vendors.append(vendor)
        else:
            # Could be unknown vendor - track it
            if len(name) > 2 and name.lower() not in {"mail", "email", "dernier", "facture", "invoice"}:
                unknown_terms.append(name)

    # Check contacts (fuzzy match on name/email)
    contact_names = []
    for c in contacts:
        if c.get("name"):
            contact_names.append(c["name"])
        if c.get("first_name"):
            contact_names.append(c["first_name"])
        if c.get("last_name"):
            contact_names.append(c["last_name"])

    for name in potential_names:
        match = best_match(name, contact_names, cutoff=0.5)
        if match:
            contact = next(
                (c for c in contacts if match in [c.get("name"), c.get("first_name"), c.get("last_name")]),
                None
            )
            if contact and contact not in matched_contacts:
                matched_contacts.append(contact)

    return {
        "vendors": matched_vendors,
        "contacts": matched_contacts,
        "aliases": matched_aliases,
        "unknown_terms": unknown_terms,
    }


async def _build_queries(query_text: str, user_id: str) -> List[Dict[str, Any]]:
    """
    Build Gmail queries using memory lookups.
    Returns list of {query, description} ordered by specificity.
    """
    time_range = _detect_time_range(query_text)
    doc_type = _detect_doc_type(query_text)

    entities = await _find_matching_entities(query_text, user_id)
    queries = []

    # Build from/subject filters from entities
    from_filters = []
    subject_filters = []

    # Aliases → email
    for alias in entities["aliases"]:
        email = alias.get("value")
        if email:
            from_filters.append(f'from:{email}')

    # Vendors → domain or email
    for vendor in entities["vendors"]:
        name = vendor.get("name", "")
        domains = vendor.get("domains", [])
        email = vendor.get("last_invoice_email")
        if email:
            from_filters.append(f'from:{email}')
        elif domains:
            from_filters.append(f'from:@{domains[0]}')
        else:
            subject_filters.append(f'"{name}"')

    # Contacts → email
    for contact in entities["contacts"]:
        email = contact.get("email")
        if email:
            from_filters.append(f'from:{email}')

    # Unknown terms → try as subject search
    for term in entities["unknown_terms"]:
        subject_filters.append(f'"{term}"')

    # Query 1: Most specific (time + doc_type + from/subject)
    parts = [time_range]
    if doc_type:
        parts.append(doc_type)
    if from_filters:
        parts.append(f'({" OR ".join(from_filters)})')
    elif subject_filters:
        parts.append(f'({" OR ".join(subject_filters)})')

    queries.append({
        "query": " ".join(parts),
        "description": "Recherche précise avec mémoire",
        "entities": entities
    })

    # Query 2: Fallback without doc type
    if doc_type:
        parts2 = [time_range]
        if from_filters:
            parts2.append(f'({" OR ".join(from_filters)})')
        elif subject_filters:
            parts2.append(f'({" OR ".join(subject_filters)})')
        if len(parts2) > 1:
            queries.append({
                "query": " ".join(parts2),
                "description": "Recherche élargie sans type doc"
            })

    # Query 3: Broader time range
    queries.append({
        "query": f"newer_than:365d {' OR '.join(subject_filters)}" if subject_filters else "newer_than:365d",
        "description": "Recherche large sur 1 an"
    })

    return queries[:3]


async def _maybe_create_vendor_candidate(user_id: str, term: str):
    """
    If term looks like a vendor name (capitalized, not common word),
    create a candidate vendor entry for future learning.
    """
    if not term or len(term) < 3:
        return

    # Skip common words
    skip_words = {
        "mail", "email", "message", "dernier", "facture", "invoice",
        "devis", "contrat", "document", "fichier", "piece", "jointe"
    }
    if term.lower() in skip_words:
        return

    db = await get_db()
    existing = await db.vendors.find_one({"user_id": user_id, "name": {"$regex": f"^{re.escape(term)}$", "$options": "i"}})
    if not existing:
        # Create candidate vendor (will be enriched when we see an email from them)
        await db.vendors.update_one(
            {"user_id": user_id, "name": term.lower()},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "name": term.lower(),
                    "domains": [],
                    "keywords": [term.lower()],
                    "last_invoice_email": None,
                    "candidate": True,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        logger.info(f"Created vendor candidate: {term}")


# ============================================================
# ROUTES
# ============================================================

@router.post("/search")
async def copilot_search(body: SearchRequest) -> Dict[str, Any]:
    """
    Smart email search using memory (vendors, contacts, aliases).
    Builds multiple queries with fallbacks.
    """
    db = await get_db()

    # Find account
    account = None
    if body.account_id:
        account = await db.accounts.find_one({"account_id": body.account_id})
    if not account:
        account = await db.accounts.find_one(
            {"user_id": body.user_id, "$or": [{"provider": "gmail"}, {"type": "gmail"}]}
        )
    if not account:
        raise HTTPException(status_code=404, detail="No Gmail account connected")

    # Build queries using memory
    query_defs = await _build_queries(body.query_text, body.user_id)

    attempts = []
    fallbacks_used = []
    final_results = []

    for idx, qdef in enumerate(query_defs):
        q = qdef["query"]
        try:
            emails = await email_service.search_emails(account["account_id"], q)
            attempt = {
                "query": q,
                "description": qdef.get("description", ""),
                "count": len(emails),
                "results": emails[:5]
            }
            if "entities" in qdef:
                attempt["entities_found"] = {
                    "vendors": [v["name"] for v in qdef["entities"].get("vendors", [])],
                    "contacts": [c.get("name") or c.get("email") for c in qdef["entities"].get("contacts", [])],
                    "aliases": [a["key"] for a in qdef["entities"].get("aliases", [])],
                    "unknown": qdef["entities"].get("unknown_terms", [])
                }
            attempts.append(attempt)

            if idx > 0:
                fallbacks_used.append(q)

            if emails:
                final_results = emails[:5]
                # Create vendor candidates for unknown terms that yielded results
                if "entities" in qdef:
                    for term in qdef["entities"].get("unknown_terms", []):
                        await _maybe_create_vendor_candidate(body.user_id, term)
                break

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("copilot_search failed")
            attempts.append({"query": q, "error": str(e)})
            if idx > 0:
                fallbacks_used.append(q)

    return {
        "account": {"account_id": account["account_id"], "email": account.get("email")},
        "query_text": body.query_text,
        "attempts": attempts,
        "fallbacks_used": fallbacks_used,
        "results": final_results,
        "action_hint": "open_email" if final_results else "refine_search"
    }


@router.post("/resolve")
async def copilot_resolve(body: ResolveRequest) -> Dict[str, Any]:
    """
    Resolve a text reference to an email address.
    Lookup chain: aliases → contacts → vendors (with fuzzy matching).
    """
    db = await get_db()
    key = normalize(body.text)
    if not key:
        raise HTTPException(status_code=400, detail="text required")

    # 1. Exact alias match
    alias = await db.aliases.find_one({"user_id": body.user_id, "key": key})
    if alias:
        return {
            "resolved": True,
            "email": alias["value"],
            "source": "alias",
            "confidence": alias.get("confidence", 1.0),
            "choices": []
        }

    # 2. Fuzzy search in contacts
    contacts = await load_contacts(body.user_id)
    contact_candidates = []
    for c in contacts:
        names = [c.get("name"), c.get("first_name"), c.get("last_name"), c.get("email")]
        names = [n for n in names if n]
        matches = fuzzy_match(body.text, names, cutoff=0.5)
        if matches:
            score = matches[0][1]
            contact_candidates.append((c, score))

    # 3. Fuzzy search in vendors
    vendors = await load_vendors(body.user_id)
    vendor_candidates = []
    for v in vendors:
        names = [v.get("name")] + (v.get("keywords") or [])
        names = [n for n in names if n]
        matches = fuzzy_match(body.text, names, cutoff=0.5)
        if matches:
            score = matches[0][1]
            vendor_candidates.append((v, score))

    # Combine and sort by score
    choices = []
    for c, score in sorted(contact_candidates, key=lambda x: x[1], reverse=True)[:3]:
        choices.append({
            "email": c.get("email"),
            "name": c.get("name") or f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
            "role": c.get("role"),
            "source": "contact",
            "score": round(score, 2)
        })

    for v, score in sorted(vendor_candidates, key=lambda x: x[1], reverse=True)[:3]:
        if v.get("last_invoice_email"):
            choices.append({
                "email": v["last_invoice_email"],
                "name": v.get("name"),
                "source": "vendor",
                "score": round(score, 2)
            })

    # Sort all choices by score
    choices = sorted(choices, key=lambda x: x.get("score", 0), reverse=True)[:5]

    # If single high-confidence match, resolve immediately
    if len(choices) == 1 and choices[0].get("email") and choices[0].get("score", 0) >= 0.8:
        return {
            "resolved": True,
            "email": choices[0]["email"],
            "source": choices[0].get("source"),
            "confidence": choices[0].get("score"),
            "choices": choices
        }

    if choices:
        return {
            "resolved": False,
            "choices": choices,
            "message": "Plusieurs correspondances trouvées."
        }

    raise HTTPException(
        status_code=404,
        detail="Aucun contact ou fournisseur trouvé. Précise le nom ou l'adresse email."
    )
