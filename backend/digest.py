"""
Recap System (Digest)
=====================
Generate morning/evening recaps with smart classification.
Influence by user memory (VIPs, preferences, learned patterns).
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from bson import ObjectId

from backend.database import get_db
from backend.email_service import EmailService
from backend.threads import (
    get_or_create_thread,
    get_waiting_threads,
    ThreadStatus
)

logger = logging.getLogger(__name__)
email_service = EmailService()


class EmailPriority:
    URGENT = "urgent"       # Action immédiate requise
    TODO = "todo"           # À traiter aujourd'hui
    WAITING = "waiting"     # En attente de réponse
    INFO = "info"           # Pour info
    IGNORE = "ignore"       # Ignorable


class RecapType:
    MORNING = "morning"
    EVENING = "evening"
    MANUAL = "manual"


# Keywords for classification
URGENT_KEYWORDS = [
    "urgent", "urgente", "asap", "immédiat", "immediately",
    "deadline", "échéance", "aujourd'hui", "today",
    "retard", "late", "overdue", "impayé", "unpaid",
    "huissier", "mise en demeure", "relance finale",
    "dernier délai", "final notice", "action requise",
    "expiration", "expire"
]

TODO_KEYWORDS = [
    "facture", "invoice", "paiement", "payment",
    "contrat", "contract", "devis", "quote",
    "signature", "à signer", "validation", "confirmer",
    "rendez-vous", "meeting", "réunion", "rappel"
]

VIP_DOMAINS = [
    "banque", "bank", "impot", "tax", "urssaf", "dgfip",
    "tresor", "tribunal", "avocat", "notaire", "assurance"
]

IGNORE_PATTERNS = [
    "newsletter", "unsubscribe", "se désabonner",
    "notification automatique", "no-reply", "noreply",
    "promo", "soldes", "offre spéciale", "marketing"
]


async def get_user_memory(user_id: str) -> Dict[str, Any]:
    """Load user memory to influence classification."""
    db = await get_db()

    # VIP senders from important_patterns
    vip_patterns = await db.important_patterns.find({
        "user_id": user_id,
        "importance": "high"
    }).to_list(100)

    # Direct VIP list
    vips = await db.vips.find({"user_id": user_id}).to_list(100)
    vip_emails = [v.get("email", "").lower() for v in vips]

    # Known vendors
    vendors = await db.vendors.find({"user_id": user_id}).to_list(100)

    # Aliases
    aliases = await db.aliases.find({"user_id": user_id}).to_list(100)

    # Preferences
    prefs = await db.user_preferences.find_one({"user_id": user_id}) or {}

    return {
        "vip_patterns": vip_patterns,
        "vip_emails": vip_emails,
        "vendors": [v.get("name", "").lower() for v in vendors],
        "aliases": {a.get("key", "").lower(): a.get("email", "") for a in aliases},
        "preferences": prefs
    }


def classify_email(
    email: Dict[str, Any],
    memory: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Classify email with reason.
    Returns: {"priority": str, "reason": str, "confidence": float, "is_vip": bool}
    """
    subject = (email.get("subject") or "").lower()
    snippet = (email.get("snippet") or "").lower()
    from_email = (email.get("from_email") or "").lower()
    from_name = (email.get("from") or "").lower()
    text = f"{subject} {snippet}"

    memory = memory or {}
    vip_patterns = memory.get("vip_patterns", [])
    vip_emails = memory.get("vip_emails", [])
    vendors = memory.get("vendors", [])

    # Check if sender is in VIP list
    is_vip = from_email in vip_emails

    # Check ignorable first (but not for VIPs)
    if not is_vip:
        for pattern in IGNORE_PATTERNS:
            if pattern in text or pattern in from_email:
                return {
                    "priority": EmailPriority.IGNORE,
                    "reason": "Email promotionnel",
                    "confidence": 0.8,
                    "is_vip": False
                }

    # Check if in VIP list - priority boost
    if is_vip:
        # Check for urgent keywords even for VIPs
        for kw in URGENT_KEYWORDS:
            if kw in text:
                return {
                    "priority": EmailPriority.URGENT,
                    "reason": f"VIP + {kw}",
                    "confidence": 0.98,
                    "is_vip": True
                }
        # Default: VIP = at least TODO
        return {
            "priority": EmailPriority.TODO,
            "reason": "Contact VIP",
            "confidence": 0.9,
            "is_vip": True
        }

    # Check VIP patterns from memory
    for pattern in vip_patterns:
        ptype = pattern.get("pattern_type", "")
        pval = pattern.get("pattern_value", "").lower()
        if ptype == "sender" and pval in from_email:
            return {
                "priority": EmailPriority.URGENT,
                "reason": f"VIP: {pattern.get('label', pval)}",
                "confidence": 0.95,
                "is_vip": True
            }
        if ptype == "keyword" and pval in text:
            return {
                "priority": EmailPriority.URGENT,
                "reason": f"Mot-clé prioritaire: {pval}",
                "confidence": 0.9,
                "is_vip": False
            }

    # Check VIP domains
    for vip in VIP_DOMAINS:
        if vip in from_email:
            return {
                "priority": EmailPriority.URGENT,
                "reason": f"Organisme officiel",
                "confidence": 0.9,
                "is_vip": False
            }

    # Check urgent keywords
    for kw in URGENT_KEYWORDS:
        if kw in text:
            return {
                "priority": EmailPriority.URGENT,
                "reason": f"Urgence: {kw}",
                "confidence": 0.85,
                "is_vip": False
            }

    # Check if from known vendor (usually invoice/business)
    for vendor in vendors:
        if vendor in from_email or vendor in from_name:
            return {
                "priority": EmailPriority.TODO,
                "reason": f"Fournisseur: {vendor}",
                "confidence": 0.8,
                "is_vip": False
            }

    # Check TODO keywords
    for kw in TODO_KEYWORDS:
        if kw in text:
            return {
                "priority": EmailPriority.TODO,
                "reason": f"À traiter: {kw}",
                "confidence": 0.75,
                "is_vip": False
            }

    # Check if has attachments
    if email.get("has_attachments"):
        return {
            "priority": EmailPriority.TODO,
            "reason": "Pièce jointe",
            "confidence": 0.6,
            "is_vip": False
        }

    return {
        "priority": EmailPriority.INFO,
        "reason": "Informatif",
        "confidence": 0.5,
        "is_vip": False
    }


async def is_silence_active(db, user_id: str) -> bool:
    """Check if silence mode is currently active."""
    settings = await db.user_settings.find_one({"user_id": user_id})
    if not settings or "silence" not in settings:
        return False

    silence = settings["silence"]
    if not silence.get("enabled"):
        return False

    # Check time ranges
    now = datetime.utcnow()
    current_time = now.strftime("%H:%M")

    for r in silence.get("ranges", []):
        start = r.get("start", "00:00")
        end = r.get("end", "23:59")
        if start <= current_time <= end:
            return True

    return False


async def generate_recap_notifications(db, user_id: str, recap: Dict[str, Any]):
    """Generate notifications for important recap items."""
    now = datetime.utcnow()

    # Check silence mode - still create notifications but mark them
    silence_active = await is_silence_active(db, user_id)

    notifications_to_create = []

    # URGENT items (confidence >= 0.85)
    for item in recap.get("urgent", []):
        if item.get("confidence", 0) >= 0.85:
            notifications_to_create.append({
                "user_id": user_id,
                "type": "urgent",
                "title": f"🔴 Urgent: {item.get('from', '').split('<')[0].strip()[:30]}",
                "body": item.get("subject", "")[:100],
                "message": item.get("subject", "")[:100],
                "priority": "urgent",
                "data": {
                    "email_id": item.get("email_id"),
                    "account_id": item.get("account_id"),
                    "reason": item.get("reason")
                },
                "email_id": item.get("email_id"),
                "created_at": now,
                "read": False,
                "silenced": silence_active
            })

    # VIP items
    for item in recap.get("urgent", []) + recap.get("todo", []):
        if item.get("is_vip"):
            # Avoid duplicates
            if not any(n.get("email_id") == item.get("email_id") for n in notifications_to_create):
                notifications_to_create.append({
                    "user_id": user_id,
                    "type": "vip",
                    "title": f"⭐ VIP: {item.get('from', '').split('<')[0].strip()[:30]}",
                    "body": item.get("subject", "")[:100],
                    "message": item.get("subject", "")[:100],
                    "priority": "high",
                    "data": {
                        "email_id": item.get("email_id"),
                        "account_id": item.get("account_id"),
                        "is_vip": True
                    },
                    "email_id": item.get("email_id"),
                    "created_at": now,
                    "read": False,
                    "silenced": silence_active
                })

    # Document critiques (facture, devis)
    for doc in recap.get("documents", []):
        doc_type = doc.get("doc_type", doc.get("type", "document"))
        if doc_type in ["facture", "devis", "invoice"]:
            notifications_to_create.append({
                "user_id": user_id,
                "type": "document",
                "title": f"📄 {doc_type.capitalize()}: {doc.get('from', '').split('<')[0].strip()[:25]}",
                "body": doc.get("subject", "")[:100],
                "message": doc.get("subject", "")[:100],
                "priority": "medium",
                "data": {
                    "email_id": doc.get("email_id"),
                    "doc_type": doc_type
                },
                "email_id": doc.get("email_id"),
                "created_at": now,
                "read": False,
                "silenced": silence_active
            })

    # Waiting overdue
    for w in recap.get("waiting", []):
        if w.get("is_overdue"):
            notifications_to_create.append({
                "user_id": user_id,
                "type": "waiting_overdue",
                "title": f"⏰ Relance: {w.get('subject', 'conversation')[:40]}",
                "body": f"Sans réponse depuis {w.get('days_waiting', 0)} jours",
                "message": f"Sans réponse depuis {w.get('days_waiting', 0)} jours",
                "priority": "medium",
                "data": {
                    "thread_id": w.get("thread_id"),
                    "days_waiting": w.get("days_waiting")
                },
                "thread_id": w.get("thread_id"),
                "created_at": now,
                "read": False,
                "silenced": silence_active
            })

    # Insert notifications (avoid duplicates by email_id/thread_id for today)
    for notif in notifications_to_create[:10]:  # Limit to 10 per recap
        existing = await db.notifications.find_one({
            "user_id": user_id,
            "email_id": notif.get("email_id"),
            "created_at": {"$gte": datetime.utcnow().replace(hour=0, minute=0, second=0)}
        }) if notif.get("email_id") else None

        if not existing:
            await db.notifications.insert_one(notif)

    logger.info(f"🔔 Created {len(notifications_to_create)} notifications for {user_id} (silence={silence_active})")


async def generate_recap(
    user_id: str,
    recap_type: str = RecapType.MANUAL,
    account_ids: Optional[List[str]] = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Generate a recap (morning or evening).
    Implements lazy generation - won't regenerate if already exists today.
    """
    db = await get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")

    # Check if already generated today (unless forced)
    if not force:
        existing = await db.recaps.find_one({
            "user_id": user_id,
            "date": today,
            "type": recap_type
        })
        if existing:
            existing["id"] = str(existing.pop("_id"))
            return existing

    # Load user memory for classification
    memory = await get_user_memory(user_id)

    # Get accounts
    if account_ids:
        accounts = await db.accounts.find({
            "user_id": user_id,
            "account_id": {"$in": account_ids}
        }).to_list(100)
    else:
        accounts = await db.accounts.find({"user_id": user_id}).to_list(100)

    if not accounts:
        return {"error": "Aucun compte connecté", "accounts": []}

    # Determine time range based on recap type
    if recap_type == RecapType.MORNING:
        # Morning: last 12 hours (evening to morning)
        start_date = now - timedelta(hours=12)
    elif recap_type == RecapType.EVENING:
        # Evening: today's emails
        start_date = now.replace(hour=0, minute=0, second=0)
    else:
        # Manual: last 24 hours
        start_date = now - timedelta(hours=24)

    urgent_items = []
    todo_items = []
    info_count = 0
    ignore_count = 0
    total_scanned = 0
    documents_detected = []

    # Search each account
    for account in accounts:
        account_id = account.get("account_id")
        account_email = account.get("email")

        try:
            query = f"is:unread after:{start_date.strftime('%Y/%m/%d')}"
            emails = await email_service.search_emails(account_id, query)

            for email in emails:
                total_scanned += 1
                classification = classify_email(email, memory)
                priority = classification["priority"]

                # Check for documents (attachments with specific names)
                has_doc = False
                if email.get("has_attachments") or "📎" in email.get("snippet", ""):
                    subject_lower = (email.get("subject") or "").lower()
                    for doc_type in ["facture", "devis", "contrat", "bon de commande"]:
                        if doc_type in subject_lower:
                            has_doc = True
                            documents_detected.append({
                                "email_id": email.get("id"),
                                "subject": email.get("subject"),
                                "from": email.get("from"),
                                "type": doc_type,
                                "date": email.get("date")
                            })
                            break

                item = {
                    "email_id": email.get("id"),
                    "thread_id": email.get("thread_id", email.get("id")),
                    "account_id": account_id,
                    "account_email": account_email,
                    "subject": email.get("subject"),
                    "from": email.get("from"),
                    "from_email": email.get("from_email"),
                    "date": email.get("date"),
                    "snippet": email.get("snippet", "")[:120],
                    "priority": priority,
                    "reason": classification["reason"],
                    "confidence": classification["confidence"],
                    "is_vip": classification.get("is_vip", False),
                    "has_attachments": email.get("has_attachments") or has_doc,
                    "link": email.get("link")
                }

                if priority == EmailPriority.URGENT:
                    urgent_items.append(item)
                elif priority == EmailPriority.TODO:
                    todo_items.append(item)
                elif priority == EmailPriority.IGNORE:
                    ignore_count += 1
                else:
                    info_count += 1

                # Create/update thread
                await get_or_create_thread(
                    user_id=user_id,
                    account_id=account_id,
                    thread_id=email.get("thread_id", email.get("id")),
                    subject=email.get("subject"),
                    participants=[email.get("from_email")]
                )

        except Exception as e:
            logger.warning(f"Error scanning account {account_email}: {e}")

    # Get waiting threads
    waiting_threads = await get_waiting_threads(user_id, overdue_only=False)
    waiting_items = []
    for thread in waiting_threads[:5]:
        waiting_items.append({
            "thread_id": thread.get("thread_id"),
            "account_id": thread.get("account_id"),
            "subject": thread.get("subject"),
            "days_waiting": thread.get("days_waiting", 0),
            "is_overdue": thread.get("next_followup_at") and
                         thread["next_followup_at"] < datetime.utcnow()
        })

    # Generate AI suggestions (top 3 actions)
    suggestions = []
    if urgent_items:
        suggestions.append({
            "action": f"Traiter l'email urgent de {urgent_items[0].get('from', 'inconnu').split('<')[0].strip()}",
            "reason": urgent_items[0].get("reason"),
            "email_id": urgent_items[0].get("email_id"),
            "type": "urgent"
        })
    if waiting_items and waiting_items[0].get("is_overdue"):
        suggestions.append({
            "action": f"Relancer: {waiting_items[0].get('subject', 'conversation')[:40]}",
            "reason": f"Sans réponse depuis {waiting_items[0].get('days_waiting', 0)}j",
            "thread_id": waiting_items[0].get("thread_id"),
            "type": "waiting"
        })
    if documents_detected:
        suggestions.append({
            "action": f"Traiter {documents_detected[0].get('type')}",
            "reason": f"De {documents_detected[0].get('from', 'inconnu').split('<')[0].strip()[:20]}",
            "email_id": documents_detected[0].get("email_id"),
            "type": "document"
        })

    # Generate Rappels IA for evening recap
    rappels_ia = []
    if recap_type == RecapType.EVENING:
        # Check for untreated TODO items
        for item in todo_items[:3]:
            rappels_ia.append({
                "message": f"N'oublie pas: {item.get('subject', 'email')[:50]}",
                "from": item.get("from", "").split("<")[0].strip()[:25],
                "email_id": item.get("email_id"),
                "priority": "todo"
            })
        # Check for overdue waiting threads
        for w in waiting_items:
            if w.get("is_overdue") and len(rappels_ia) < 3:
                rappels_ia.append({
                    "message": f"Relance en retard: {w.get('subject', 'conversation')[:40]}",
                    "from": "",
                    "thread_id": w.get("thread_id"),
                    "priority": "overdue"
                })

    # Build recap
    recap = {
        "user_id": user_id,
        "date": today,
        "type": recap_type,
        "generated_at": now,
        "accounts": [a.get("email") for a in accounts],
        "urgent": urgent_items[:5],
        "todo": todo_items[:10],
        "waiting": waiting_items,
        "documents": documents_detected[:5],
        "suggestions": suggestions[:3],
        "rappels_ia": rappels_ia[:3],
        "stats": {
            "urgent_count": len(urgent_items),
            "todo_count": len(todo_items),
            "waiting_count": len(waiting_threads),
            "documents_count": len(documents_detected)
        }
    }

    # Store recap (upsert)
    await db.recaps.update_one(
        {"user_id": user_id, "date": today, "type": recap_type},
        {"$set": recap},
        upsert=True
    )

    # Generate notifications for important items (respecting Mode Silence)
    await generate_recap_notifications(db, user_id, recap)

    logger.info(f"📊 Generated {recap_type} recap for {user_id}: {recap['stats']}")

    return recap


async def get_or_generate_recap(
    user_id: str,
    recap_type: str
) -> Dict[str, Any]:
    """
    Lazy scheduler: get existing recap or generate if needed.
    Called on frontend load.
    """
    db = await get_db()
    now = datetime.utcnow()
    today = now.strftime("%Y-%m-%d")
    hour = now.hour

    # Determine which recap to check
    if recap_type == "auto":
        if 6 <= hour < 18:
            recap_type = RecapType.MORNING
        else:
            recap_type = RecapType.EVENING

    # Check if exists
    existing = await db.recaps.find_one({
        "user_id": user_id,
        "date": today,
        "type": recap_type
    })

    if existing:
        existing["id"] = str(existing.pop("_id"))
        return existing

    # Generate new
    return await generate_recap(user_id, recap_type)


async def get_recaps_history(
    user_id: str,
    limit: int = 14
) -> List[Dict[str, Any]]:
    """Get recap history (last X days)."""
    db = await get_db()

    cursor = db.recaps.find(
        {"user_id": user_id}
    ).sort("generated_at", -1).limit(limit)

    recaps = []
    async for recap in cursor:
        recap["id"] = str(recap.pop("_id"))
        recaps.append(recap)

    return recaps


async def get_today_summary(user_id: str) -> Dict[str, Any]:
    """
    Quick summary for 'Aujourd'hui' screen.
    Combines morning + evening data.
    """
    db = await get_db()
    today = datetime.utcnow().strftime("%Y-%m-%d")

    # Get today's recaps
    recaps = await db.recaps.find({
        "user_id": user_id,
        "date": today
    }).to_list(10)

    # Merge data
    urgent = []
    todo = []
    waiting = []
    documents = []

    seen_emails = set()

    for recap in recaps:
        for item in recap.get("urgent", []):
            if item.get("email_id") not in seen_emails:
                urgent.append(item)
                seen_emails.add(item.get("email_id"))
        for item in recap.get("todo", []):
            if item.get("email_id") not in seen_emails:
                todo.append(item)
                seen_emails.add(item.get("email_id"))
        for item in recap.get("waiting", []):
            waiting.append(item)
        for item in recap.get("documents", []):
            documents.append(item)

    # Get thread stats
    from backend.threads import get_thread_stats
    thread_stats = await get_thread_stats(user_id)

    return {
        "date": today,
        "urgent": urgent[:5],
        "todo": todo[:10],
        "waiting": waiting[:5],
        "documents": documents[:5],
        "stats": {
            "urgent_count": len(urgent),
            "todo_count": len(todo),
            "waiting_count": thread_stats.get("WAITING", 0),
            "overdue_count": thread_stats.get("overdue", 0)
        }
    }


# Legacy compatibility
async def generate_digest(user_id: str, account_ids=None, date=None, days_back=1):
    """Legacy function - redirects to generate_recap."""
    return await generate_recap(user_id, RecapType.MANUAL, account_ids)


async def get_latest_digest(user_id: str):
    """Legacy function."""
    db = await get_db()
    recap = await db.recaps.find_one(
        {"user_id": user_id},
        sort=[("generated_at", -1)]
    )
    if recap:
        recap["id"] = str(recap.pop("_id"))
    return recap


async def get_digest_by_date(user_id: str, date: str):
    """Legacy function."""
    db = await get_db()
    recap = await db.recaps.find_one({
        "user_id": user_id,
        "date": date
    })
    if recap:
        recap["id"] = str(recap.pop("_id"))
    return recap
