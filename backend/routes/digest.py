"""
API Routes pour Recaps et Threads
==================================
Endpoints pour les récaps matin/soir et le suivi des threads.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from backend.digest import (
    generate_recap,
    get_or_generate_recap,
    get_recaps_history,
    get_today_summary,
    get_latest_digest,
    get_digest_by_date,
    RecapType
)
from backend.threads import (
    get_threads_by_status,
    update_thread_status,
    get_thread_stats,
    get_waiting_threads,
    ThreadStatus
)

router = APIRouter(prefix="/api", tags=["Recaps & Threads"])


# ============================================================
# RECAP ENDPOINTS (New System)
# ============================================================

class RecapRequest(BaseModel):
    type: Optional[str] = "auto"  # morning, evening, manual, auto
    accounts: Optional[List[str]] = None
    force: Optional[bool] = False


@router.get("/today")
async def get_today(user_id: str = Query(default="default_user")):
    """
    Récupère le résumé du jour pour l'écran "Aujourd'hui".
    Combine les données des récaps matin + soir.
    """
    summary = await get_today_summary(user_id)
    return summary


@router.get("/recap/{recap_type}")
async def get_recap(
    recap_type: str,
    user_id: str = Query(default="default_user")
):
    """
    Récupère ou génère un récap (lazy scheduler).

    Types:
    - morning: Récap du matin (nouveaux emails de la nuit)
    - evening: Récap du soir (emails de la journée)
    - auto: Détermine automatiquement selon l'heure
    """
    if recap_type not in ["morning", "evening", "auto"]:
        raise HTTPException(
            status_code=400,
            detail="Type invalide. Utilisez: morning, evening, auto"
        )

    recap = await get_or_generate_recap(user_id, recap_type)

    if recap.get("error"):
        raise HTTPException(status_code=404, detail=recap["error"])

    return recap


@router.post("/recap/generate")
async def create_recap(
    request: RecapRequest,
    user_id: str = Query(default="default_user")
):
    """
    Force la génération d'un récap.

    - type: morning, evening, manual (default: manual)
    - accounts[]: filtre sur ces comptes
    - force: true = régénère même s'il existe déjà
    """
    recap_type = request.type or "manual"

    if recap_type not in ["morning", "evening", "manual", "auto"]:
        recap_type = RecapType.MANUAL
    elif recap_type == "morning":
        recap_type = RecapType.MORNING
    elif recap_type == "evening":
        recap_type = RecapType.EVENING
    elif recap_type == "auto":
        # Determine based on time
        hour = datetime.utcnow().hour
        recap_type = RecapType.MORNING if 6 <= hour < 18 else RecapType.EVENING
    else:
        recap_type = RecapType.MANUAL

    recap = await generate_recap(
        user_id=user_id,
        recap_type=recap_type,
        account_ids=request.accounts,
        force=request.force or False
    )

    if recap.get("error"):
        raise HTTPException(status_code=404, detail=recap["error"])

    return recap


@router.get("/recaps/history")
async def recap_history(
    user_id: str = Query(default="default_user"),
    limit: int = Query(default=14, le=30)
):
    """
    Historique des récaps (14 derniers jours par défaut).
    """
    recaps = await get_recaps_history(user_id, limit)

    return {
        "recaps": recaps,
        "count": len(recaps)
    }


# ============================================================
# LEGACY DIGEST ENDPOINTS (Backwards Compatibility)
# ============================================================

class DigestRequest(BaseModel):
    accounts: Optional[List[str]] = None
    date: Optional[str] = None
    days_back: Optional[int] = 1


@router.post("/digest/generate")
async def create_digest(
    request: DigestRequest,
    user_id: str = Query(default="default_user")
):
    """
    [Legacy] Génère un digest des emails.
    Redirige vers generate_recap.
    """
    recap = await generate_recap(
        user_id=user_id,
        recap_type=RecapType.MANUAL,
        account_ids=request.accounts,
        force=True
    )

    if recap.get("error"):
        raise HTTPException(status_code=404, detail=recap["error"])

    return recap


@router.get("/digest/latest")
async def get_latest(user_id: str = Query(default="default_user")):
    """[Legacy] Récupère le dernier digest généré."""
    digest = await get_latest_digest(user_id)

    if not digest:
        raise HTTPException(status_code=404, detail="No digest found. Generate one first.")

    return digest


@router.get("/digest/{date}")
async def get_by_date(
    date: str,
    user_id: str = Query(default="default_user")
):
    """[Legacy] Récupère le digest d'une date spécifique."""
    digest = await get_digest_by_date(user_id, date)

    if not digest:
        raise HTTPException(status_code=404, detail=f"No digest found for {date}")

    return digest


# ============================================================
# THREADS ENDPOINTS
# ============================================================

class ThreadStatusUpdate(BaseModel):
    status: str  # OPEN, WAITING, DONE
    next_followup_at: Optional[str] = None  # ISO datetime


@router.get("/threads")
async def list_threads(
    user_id: str = Query(default="default_user"),
    status: Optional[str] = Query(default=None),
    account_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=100)
):
    """
    Liste les threads email.

    Filtres optionnels:
    - status: OPEN, WAITING, DONE
    - account_id: filtre par compte
    """
    thread_status = None
    if status:
        try:
            thread_status = ThreadStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Use: OPEN, WAITING, DONE"
            )

    threads = await get_threads_by_status(
        user_id=user_id,
        status=thread_status,
        account_id=account_id,
        limit=limit
    )

    return {
        "threads": threads,
        "count": len(threads),
        "filter": {"status": status, "account_id": account_id}
    }


@router.post("/threads/{thread_id}/status")
async def update_status(
    thread_id: str,
    update: ThreadStatusUpdate,
    user_id: str = Query(default="default_user")
):
    """
    Met à jour le statut d'un thread.

    - OPEN: Besoin d'attention
    - WAITING: En attente de réponse (définit un suivi automatique à J+3)
    - DONE: Terminé
    """
    # Validate thread_id is not empty
    if not thread_id or thread_id.strip() == "":
        raise HTTPException(status_code=400, detail="thread_id cannot be empty")

    try:
        status = ThreadStatus(update.status.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Use: OPEN, WAITING, DONE"
        )

    followup = None
    if update.next_followup_at:
        try:
            followup = datetime.fromisoformat(update.next_followup_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid datetime format")

    success = await update_thread_status(
        user_id=user_id,
        thread_id=thread_id,
        status=status,
        next_followup_at=followup
    )

    if not success:
        raise HTTPException(status_code=404, detail="Thread not found")

    return {"success": True, "status": status}


@router.get("/threads/waiting")
async def get_waiting(
    user_id: str = Query(default="default_user"),
    overdue_only: bool = Query(default=False)
):
    """
    Récupère les threads en attente de réponse.

    - overdue_only: true = seulement ceux dépassant la date de relance
    """
    threads = await get_waiting_threads(user_id, overdue_only)

    return {
        "threads": threads,
        "count": len(threads),
        "overdue_count": sum(1 for t in threads if t.get("is_overdue") or
                            (t.get("next_followup_at") and t["next_followup_at"] < datetime.utcnow()))
    }


@router.get("/threads/stats")
async def thread_stats(
    user_id: str = Query(default="default_user"),
    account_id: Optional[str] = Query(default=None)
):
    """Statistiques des threads."""
    stats = await get_thread_stats(user_id, account_id)
    return stats


# ============================================================
# SETTINGS: MODE SILENCE
# ============================================================

class SilenceSettings(BaseModel):
    enabled: bool
    ranges: Optional[List[dict]] = None  # [{start: "11:00", end: "14:00"}, ...]


@router.get("/settings/silence")
async def get_silence_settings(user_id: str = Query(default="default_user")):
    """Get silence mode settings."""
    from backend.database import get_db
    db = await get_db()

    settings = await db.user_settings.find_one({"user_id": user_id})

    if not settings or "silence" not in settings:
        return {
            "enabled": False,
            "ranges": [
                {"start": "11:00", "end": "14:00"},
                {"start": "18:00", "end": "23:59"}
            ]
        }

    return settings["silence"]


@router.post("/settings/silence")
async def update_silence_settings(
    settings: SilenceSettings,
    user_id: str = Query(default="default_user")
):
    """Update silence mode settings."""
    from backend.database import get_db
    db = await get_db()

    silence_data = {
        "enabled": settings.enabled,
        "ranges": settings.ranges or [
            {"start": "11:00", "end": "14:00"},
            {"start": "18:00", "end": "23:59"}
        ],
        "updated_at": datetime.utcnow()
    }

    await db.user_settings.update_one(
        {"user_id": user_id},
        {"$set": {"silence": silence_data, "updated_at": datetime.utcnow()}},
        upsert=True
    )

    return {"success": True, "silence": silence_data}


# ============================================================
# NATURAL SEARCH
# ============================================================

class NaturalSearchQuery(BaseModel):
    query: str
    account_id: Optional[str] = None


@router.post("/search/natural")
async def natural_search(
    search: NaturalSearchQuery,
    user_id: str = Query(default="default_user")
):
    """
    Natural language search for emails.
    Parses queries like:
    - "facture Metro décembre"
    - "emails comptable cette semaine"
    - "devis Distram novembre"
    """
    from backend.email_service import EmailService
    from backend.database import get_db
    import re

    db = await get_db()
    email_service = EmailService()

    query = search.query.lower().strip()

    # Parse time expressions
    time_filter = ""
    if "aujourd'hui" in query or "today" in query:
        time_filter = "newer_than:1d"
    elif "cette semaine" in query or "this week" in query:
        time_filter = "newer_than:7d"
    elif "ce mois" in query or "this month" in query:
        time_filter = "newer_than:30d"
    elif "décembre" in query or "december" in query:
        time_filter = "after:2025/12/01 before:2026/01/01"
    elif "novembre" in query or "november" in query:
        time_filter = "after:2025/11/01 before:2025/12/01"
    elif "octobre" in query or "october" in query:
        time_filter = "after:2025/10/01 before:2025/11/01"

    # Parse document types
    doc_keywords = []
    if "facture" in query or "invoice" in query:
        doc_keywords.append("facture OR invoice")
    if "devis" in query or "quote" in query:
        doc_keywords.append("devis OR quote")
    if "contrat" in query or "contract" in query:
        doc_keywords.append("contrat OR contract")
    if "attestation" in query:
        doc_keywords.append("attestation")

    # Parse sender/company names
    words = query.split()
    sender_keywords = []
    skip_words = {"facture", "devis", "contrat", "email", "emails", "cette",
                  "semaine", "mois", "décembre", "novembre", "octobre",
                  "trouve", "cherche", "montre", "la", "le", "de", "du",
                  "des", "un", "une", "ma", "mon", "mes", "au", "aux"}

    known_patterns = ["metro", "distram", "comptable", "banque", "edf",
                      "orange", "free", "sfr", "uber", "amazon", "google"]

    for word in words:
        clean_word = re.sub(r'[^\w]', '', word).lower()
        if clean_word and clean_word not in skip_words:
            if clean_word in known_patterns or (len(clean_word) > 2 and word[0].isupper()):
                sender_keywords.append(clean_word)

    # Build Gmail query
    gmail_query_parts = []
    if sender_keywords:
        gmail_query_parts.append(" ".join(sender_keywords))
    if doc_keywords:
        gmail_query_parts.append(f"({' OR '.join(doc_keywords)})")
    if time_filter:
        gmail_query_parts.append(time_filter)

    gmail_query = " ".join(gmail_query_parts) if gmail_query_parts else query

    # Get account
    account_id = search.account_id
    if not account_id:
        account = await db.accounts.find_one({"user_id": user_id})
        if account:
            account_id = account.get("account_id")

    if not account_id:
        return {
            "results": [],
            "query_used": gmail_query,
            "message": "Aucun compte email connecté"
        }

    # Execute search
    try:
        results = await email_service.search_emails(account_id, gmail_query, max_results=10)

        # Enrich results with reasons and VIP check
        enriched = []
        for email in results:
            reasons = []
            subject_lower = (email.get("subject") or "").lower()

            if any(kw in subject_lower for kw in ["facture", "invoice"]):
                reasons.append("Facture")
            if any(kw in subject_lower for kw in ["devis", "quote"]):
                reasons.append("Devis")
            if any(kw in subject_lower for kw in ["contrat", "contract"]):
                reasons.append("Contrat")
            if email.get("has_attachments"):
                reasons.append("Pièce jointe")

            # Check if VIP
            from_email = (email.get("from_email") or "").lower()
            vip = await db.vips.find_one({"user_id": user_id, "email": from_email})
            if vip:
                reasons.insert(0, "VIP")

            enriched.append({
                **email,
                "reasons": reasons if reasons else ["Correspondance"],
                "is_vip": vip is not None,
                "account_id": account_id
            })

        return {
            "results": enriched,
            "count": len(enriched),
            "query_used": gmail_query,
            "parsed": {
                "time": time_filter or "all",
                "doc_types": doc_keywords,
                "senders": sender_keywords
            }
        }

    except Exception as e:
        return {
            "results": [],
            "query_used": gmail_query,
            "error": str(e)
        }
