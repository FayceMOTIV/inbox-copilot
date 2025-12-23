"""
API Routes pour les Notifications et l'Apprentissage
=====================================================
Endpoints pour l'app mobile et la gestion de l'IA.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.email_monitor import (
    get_pending_notifications,
    mark_notification_read,
    mark_all_notifications_read,
    scan_new_emails,
    get_daily_summary,
    email_monitor
)
from backend.learning import (
    learn_sender,
    get_sender_emails,
    get_all_known_senders,
    learn_faq,
    find_similar_question,
    set_preference,
    get_preference,
    get_all_preferences,
    learn_important_pattern,
    get_important_patterns,
    get_learning_stats
)
from backend.database import get_db

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])
learning_router = APIRouter(prefix="/api/learning", tags=["Learning"])


# ============================================================
# NOTIFICATIONS ENDPOINTS
# ============================================================

@router.get("")
async def list_notifications(
    user_id: str = Query(default="default_user"),
    limit: int = Query(default=50, le=100),
    unread_only: bool = Query(default=False)
):
    """
    Récupère les notifications.
    unread_only=true pour seulement les non lues.
    """
    db = await get_db()
    query = {"user_id": user_id}
    if unread_only:
        query["read"] = False

    cursor = db.notifications.find(query).sort("created_at", -1).limit(limit)
    notifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        doc["id"] = doc["_id"]
        notifications.append(doc)

    # Count unread
    unread_count = await db.notifications.count_documents({"user_id": user_id, "read": False})

    return {
        "notifications": notifications,
        "count": len(notifications),
        "unread_count": unread_count
    }


@router.post("/{notification_id}/read")
async def read_notification(notification_id: str):
    """Marque une notification comme lue."""
    await mark_notification_read(notification_id)
    return {"success": True}


class MarkReadRequest(BaseModel):
    ids: List[str]


@router.post("/mark_read")
async def batch_mark_read(body: MarkReadRequest):
    """Marque plusieurs notifications comme lues."""
    from bson import ObjectId
    db = await get_db()
    object_ids = [ObjectId(id) for id in body.ids]
    await db.notifications.update_many(
        {"_id": {"$in": object_ids}},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )
    return {"success": True, "marked": len(body.ids)}


@router.post("/mark_all_read")
async def mark_all_read_endpoint(user_id: str = Query(default="default_user")):
    """Marque toutes les notifications comme lues."""
    await mark_all_notifications_read(user_id)
    return {"success": True}


@router.post("/read-all")
async def read_all_notifications(user_id: str = Query(default="default_user")):
    """Marque toutes les notifications comme lues."""
    await mark_all_notifications_read(user_id)
    return {"success": True}


@router.post("/scan")
async def trigger_scan(
    user_id: str = Query(default="default_user"),
    account_id: str = Query(...)
):
    """
    Déclenche un scan manuel des emails.
    Utile pour rafraîchir les notifications.
    """
    important = await scan_new_emails(user_id, account_id)
    return {
        "success": True,
        "important_count": len(important),
        "important_emails": important[:10]  # Limiter pour la réponse
    }


@router.get("/summary")
async def daily_summary(
    user_id: str = Query(default="default_user"),
    account_id: str = Query(...)
):
    """Résumé quotidien des emails."""
    summary = await get_daily_summary(user_id, account_id)
    return summary


# ============================================================
# DEVICE REGISTRATION (pour push notifications futures)
# ============================================================

class DeviceRegistration(BaseModel):
    device_token: str
    platform: str  # "ios" ou "android"
    app_version: Optional[str] = None


@router.post("/register-device")
async def register_device(
    registration: DeviceRegistration,
    user_id: str = Query(default="default_user")
):
    """
    Enregistre un device pour les push notifications.
    Pour une future intégration avec APNs (iOS) ou FCM.
    """
    db = await get_db()

    await db.devices.update_one(
        {"user_id": user_id, "device_token": registration.device_token},
        {
            "$set": {
                "platform": registration.platform,
                "app_version": registration.app_version,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )

    return {"success": True, "message": "Device registered"}


# ============================================================
# LEARNING ENDPOINTS
# ============================================================

class SenderMapping(BaseModel):
    name: str
    email: str
    context: Optional[str] = None


@learning_router.post("/sender")
async def add_sender_mapping(
    mapping: SenderMapping,
    user_id: str = Query(default="default_user")
):
    """
    Apprend une correspondance nom -> email.
    Ex: "Promocash" -> "noreply@promocash.fr"
    """
    await learn_sender(user_id, mapping.name, mapping.email, mapping.context)
    return {"success": True, "message": f"Learned: {mapping.name} -> {mapping.email}"}


@learning_router.get("/sender/{name}")
async def get_sender_mapping(
    name: str,
    user_id: str = Query(default="default_user")
):
    """Récupère les emails connus pour un expéditeur."""
    emails = await get_sender_emails(user_id, name)
    return {"name": name, "emails": emails}


@learning_router.get("/senders")
async def list_all_senders(user_id: str = Query(default="default_user")):
    """Liste tous les expéditeurs connus."""
    senders = await get_all_known_senders(user_id)
    # Convert ObjectId to string
    for s in senders:
        s["_id"] = str(s["_id"])
    return {"senders": senders, "count": len(senders)}


class FAQEntry(BaseModel):
    question: str
    answer: str
    category: Optional[str] = "general"


@learning_router.post("/faq")
async def add_faq(
    entry: FAQEntry,
    user_id: str = Query(default="default_user")
):
    """Ajoute une entrée FAQ."""
    await learn_faq(user_id, entry.question, entry.answer, entry.category)
    return {"success": True}


@learning_router.get("/faq/search")
async def search_faq(
    q: str = Query(...),
    user_id: str = Query(default="default_user")
):
    """Cherche une question similaire dans la FAQ."""
    result = await find_similar_question(user_id, q)
    if result:
        result["_id"] = str(result["_id"])
    return {"found": result is not None, "result": result}


class Preference(BaseModel):
    key: str
    value: Any


@learning_router.post("/preference")
async def set_user_preference(
    pref: Preference,
    user_id: str = Query(default="default_user")
):
    """Définit une préférence utilisateur."""
    await set_preference(user_id, pref.key, pref.value)
    return {"success": True}


@learning_router.get("/preferences")
async def list_preferences(user_id: str = Query(default="default_user")):
    """Liste toutes les préférences."""
    prefs = await get_all_preferences(user_id)
    return {"preferences": prefs}


class ImportantPattern(BaseModel):
    pattern_type: str  # "sender", "subject", "keyword"
    pattern_value: str
    importance: Optional[str] = "high"
    notify: Optional[bool] = True


@learning_router.post("/important-pattern")
async def add_important_pattern(
    pattern: ImportantPattern,
    user_id: str = Query(default="default_user")
):
    """
    Ajoute un pattern pour identifier les emails importants.
    Ex: pattern_type="sender", pattern_value="banque" -> tous les emails de banque = important
    """
    await learn_important_pattern(
        user_id,
        pattern.pattern_type,
        pattern.pattern_value,
        pattern.importance,
        pattern.notify
    )
    return {"success": True}


@learning_router.get("/important-patterns")
async def list_important_patterns(user_id: str = Query(default="default_user")):
    """Liste les patterns importants."""
    patterns = await get_important_patterns(user_id)
    for p in patterns:
        p["_id"] = str(p["_id"])
    return {"patterns": patterns}


@learning_router.get("/stats")
async def learning_stats(user_id: str = Query(default="default_user")):
    """Statistiques d'apprentissage."""
    stats = await get_learning_stats(user_id)
    return stats


# ============================================================
# WORKER CONTROL
# ============================================================

@router.post("/worker/start")
async def start_worker():
    """Démarre le worker de surveillance."""
    await email_monitor.start()
    return {"success": True, "message": "Worker started"}


@router.post("/worker/stop")
async def stop_worker():
    """Arrête le worker de surveillance."""
    await email_monitor.stop()
    return {"success": True, "message": "Worker stopped"}


@router.get("/worker/status")
async def worker_status():
    """Status du worker."""
    return {
        "running": email_monitor.running,
        "interval_seconds": email_monitor.interval
    }
