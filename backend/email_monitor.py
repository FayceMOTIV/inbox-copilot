"""
ARIA Email Monitor - Surveillance et Notifications
===================================================
Système qui surveille les emails entrants et génère des notifications
pour les emails importants.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from backend.database import get_db
from backend.email_service import EmailService
from backend.learning import (
    is_email_important,
    mark_email_processed,
    is_email_processed,
    learn_sender,
    learn_from_search
)

logger = logging.getLogger(__name__)
email_service = EmailService()


# ============================================================
# NOTIFICATION QUEUE
# ============================================================

async def create_notification(
    user_id: str,
    title: str,
    body: str,
    data: Dict[str, Any] = None,
    priority: str = "high",
    email_id: str = None
):
    """
    Crée une notification dans la queue.
    Sera récupérée par l'app mobile via l'API.
    """
    db = await get_db()

    notification = {
        "user_id": user_id,
        "title": title,
        "body": body,
        "data": data or {},
        "priority": priority,
        "email_id": email_id,
        "created_at": datetime.utcnow(),
        "read": False,
        "sent_to_device": False
    }

    result = await db.notifications.insert_one(notification)
    logger.info(f"🔔 Notification created: {title}")
    return str(result.inserted_id)


async def get_pending_notifications(user_id: str, limit: int = 50) -> List[Dict]:
    """
    Récupère les notifications non lues pour un utilisateur.
    """
    db = await get_db()
    cursor = db.notifications.find({
        "user_id": user_id,
        "read": False
    }).sort("created_at", -1).limit(limit)

    notifications = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        notifications.append(doc)

    return notifications


async def mark_notification_read(notification_id: str):
    """
    Marque une notification comme lue.
    """
    db = await get_db()
    from bson import ObjectId
    await db.notifications.update_one(
        {"_id": ObjectId(notification_id)},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )


async def mark_all_notifications_read(user_id: str):
    """
    Marque toutes les notifications d'un utilisateur comme lues.
    """
    db = await get_db()
    await db.notifications.update_many(
        {"user_id": user_id, "read": False},
        {"$set": {"read": True, "read_at": datetime.utcnow()}}
    )


# ============================================================
# EMAIL SCANNING
# ============================================================

async def scan_new_emails(user_id: str, account_id: str) -> List[Dict]:
    """
    Scanne les nouveaux emails et identifie ceux qui sont importants.
    Retourne la liste des emails importants détectés.
    """
    db = await get_db()

    try:
        # Récupérer les emails des dernières 24h non lus
        query = "is:unread newer_than:1d"
        emails = await email_service.search_emails(account_id, query)

        important_emails = []

        for email_data in emails:
            email_id = email_data.get("id")
            if not email_id:
                continue

            # Vérifier si déjà traité
            if await is_email_processed(user_id, email_id):
                continue

            # Analyser l'importance
            importance = await is_email_important(user_id, email_data)

            if importance["important"]:
                important_emails.append({
                    **email_data,
                    "importance": importance
                })

                # Créer une notification
                if importance.get("notify", True):
                    sender = email_data.get("from_name") or email_data.get("from", "Inconnu")
                    subject = email_data.get("subject", "Sans objet")

                    await create_notification(
                        user_id=user_id,
                        title=f"📧 {sender}",
                        body=subject[:100],
                        data={
                            "email_id": email_id,
                            "account_id": account_id,
                            "type": "email",
                            "importance": importance["importance"]
                        },
                        priority=importance["importance"],
                        email_id=email_id
                    )

            # Marquer comme traité
            await mark_email_processed(user_id, email_id, "scanned")

            # Apprendre l'expéditeur
            sender_email = email_data.get("from_email")
            sender_name = email_data.get("from_name")
            if sender_email and sender_name:
                await learn_sender(user_id, sender_name, sender_email, "from scan")

        logger.info(f"📬 Scanned {len(emails)} emails, {len(important_emails)} important")
        return important_emails

    except Exception as e:
        logger.error(f"Error scanning emails: {e}")
        return []


async def analyze_email_content(account_id: str, email_id: str) -> Dict[str, Any]:
    """
    Analyse approfondie du contenu d'un email pour extraire des informations.
    """
    try:
        email_data = await email_service.get_email_by_id(account_id, email_id)

        analysis = {
            "has_attachments": bool(email_data.get("attachments")),
            "attachment_count": len(email_data.get("attachments", [])),
            "is_invoice": False,
            "is_quote": False,
            "mentions_amount": False,
            "mentions_deadline": False,
            "extracted_amounts": [],
            "extracted_dates": []
        }

        subject = email_data.get("subject", "").lower()
        body = email_data.get("body", "").lower()
        content = subject + " " + body

        # Détecter le type de document
        if any(kw in content for kw in ["facture", "invoice", "fact."]):
            analysis["is_invoice"] = True
        if any(kw in content for kw in ["devis", "quote", "estimation"]):
            analysis["is_quote"] = True

        # Détecter les montants (pattern: XXX,XX € ou XXX.XX€)
        import re
        amounts = re.findall(r'(\d+[.,]\d{2})\s*[€$]', content)
        analysis["extracted_amounts"] = amounts
        analysis["mentions_amount"] = bool(amounts)

        # Détecter les dates limites
        deadline_keywords = ["avant le", "jusqu'au", "date limite", "échéance", "deadline"]
        analysis["mentions_deadline"] = any(kw in content for kw in deadline_keywords)

        return analysis

    except Exception as e:
        logger.error(f"Error analyzing email: {e}")
        return {}


# ============================================================
# SMART SUMMARIES
# ============================================================

async def get_daily_summary(user_id: str, account_id: str) -> Dict[str, Any]:
    """
    Génère un résumé quotidien des emails importants.
    """
    db = await get_db()

    # Récupérer les stats des dernières 24h
    yesterday = datetime.utcnow() - timedelta(days=1)

    # Notifications créées aujourd'hui
    notifications = await db.notifications.count_documents({
        "user_id": user_id,
        "created_at": {"$gte": yesterday}
    })

    # Emails traités aujourd'hui
    processed = await db.processed_emails.count_documents({
        "user_id": user_id,
        "processed_at": {"$gte": yesterday}
    })

    # Récupérer les emails importants non lus
    important_unread = await db.notifications.find({
        "user_id": user_id,
        "read": False,
        "priority": "high"
    }).to_list(10)

    summary = {
        "date": datetime.utcnow().isoformat(),
        "emails_scanned": processed,
        "important_detected": notifications,
        "unread_important": len(important_unread),
        "top_senders": [],
        "pending_actions": []
    }

    # Top expéditeurs
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$name", "count": {"$sum": "$seen_count"}}},
        {"$sort": {"count": -1}},
        {"$limit": 5}
    ]
    top_senders = await db.sender_mappings.aggregate(pipeline).to_list(5)
    summary["top_senders"] = [{"name": s["_id"], "count": s["count"]} for s in top_senders]

    return summary


# ============================================================
# BACKGROUND WORKER
# ============================================================

class EmailMonitorWorker:
    """
    Worker qui tourne en background pour surveiller les emails.
    """

    def __init__(self, interval_seconds: int = 300):  # 5 minutes par défaut
        self.interval = interval_seconds
        self.running = False
        self.task = None

    async def start(self):
        """Démarre le worker."""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info("📬 Email monitor worker started")

    async def stop(self):
        """Arrête le worker."""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("📬 Email monitor worker stopped")

    async def _run(self):
        """Boucle principale du worker."""
        while self.running:
            try:
                await self._scan_all_accounts()
            except Exception as e:
                logger.error(f"Error in email monitor: {e}")

            await asyncio.sleep(self.interval)

    async def _scan_all_accounts(self):
        """Scanne tous les comptes email actifs."""
        db = await get_db()

        # Récupérer tous les comptes actifs
        accounts = await db.accounts.find({"type": "gmail"}).to_list(100)

        for account in accounts:
            user_id = account.get("user_id", "default_user")
            account_id = account.get("account_id")

            if account_id:
                try:
                    await scan_new_emails(user_id, account_id)
                except Exception as e:
                    logger.error(f"Error scanning account {account_id}: {e}")


# Instance globale du worker
email_monitor = EmailMonitorWorker(interval_seconds=300)
