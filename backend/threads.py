"""
Thread Tracking System
======================
Track email thread status: OPEN, WAITING, DONE
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Literal
from bson import ObjectId
from enum import Enum

from backend.database import get_db

logger = logging.getLogger(__name__)


class ThreadStatus(str, Enum):
    OPEN = "OPEN"           # New or needs attention
    WAITING = "WAITING"     # User replied, waiting for response
    DONE = "DONE"           # Resolved/closed


async def get_or_create_thread(
    user_id: str,
    account_id: str,
    thread_id: str,
    subject: Optional[str] = None,
    participants: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Get existing thread or create new one."""
    db = await get_db()

    thread = await db.threads.find_one({
        "user_id": user_id,
        "account_id": account_id,
        "thread_id": thread_id
    })

    if thread:
        thread["id"] = str(thread.pop("_id"))
        return thread

    # Create new thread
    now = datetime.utcnow()
    thread_doc = {
        "user_id": user_id,
        "account_id": account_id,
        "thread_id": thread_id,
        "subject": subject,
        "participants": participants or [],
        "status": ThreadStatus.OPEN,
        "last_activity_at": now,
        "last_user_reply_at": None,
        "next_followup_at": None,
        "tags": [],
        "created_at": now,
        "updated_at": now,
        "email_count": 1,
        "unread_count": 1
    }

    result = await db.threads.insert_one(thread_doc)
    thread_doc["id"] = str(result.inserted_id)
    thread_doc.pop("_id", None)

    logger.info(f"📧 Created thread {thread_id} for user {user_id}")
    return thread_doc


async def update_thread_status(
    user_id: str,
    thread_id: str,
    status: ThreadStatus,
    next_followup_at: Optional[datetime] = None
) -> bool:
    """Update thread status. Creates thread if it doesn't exist (upsert)."""
    db = await get_db()
    now = datetime.utcnow()

    update = {
        "$set": {
            "status": status,
            "updated_at": now
        },
        "$setOnInsert": {
            "user_id": user_id,
            "thread_id": thread_id,
            "created_at": now,
            "last_activity_at": now,
            "participants": [],
            "tags": [],
            "email_count": 0,
            "unread_count": 0
        }
    }

    if status == ThreadStatus.WAITING:
        update["$set"]["last_user_reply_at"] = now
        # Default followup in 3 days if not specified
        if next_followup_at:
            update["$set"]["next_followup_at"] = next_followup_at
        else:
            update["$set"]["next_followup_at"] = now + timedelta(days=3)
    elif status == ThreadStatus.DONE:
        update["$set"]["next_followup_at"] = None

    result = await db.threads.update_one(
        {"user_id": user_id, "thread_id": thread_id},
        update,
        upsert=True
    )

    return result.modified_count > 0 or result.upserted_id is not None


async def mark_thread_activity(
    user_id: str,
    thread_id: str,
    is_user_reply: bool = False
) -> bool:
    """Mark activity on a thread."""
    db = await get_db()

    update = {
        "$set": {
            "last_activity_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        "$inc": {"email_count": 1}
    }

    if is_user_reply:
        update["$set"]["last_user_reply_at"] = datetime.utcnow()
        update["$set"]["status"] = ThreadStatus.WAITING
        update["$set"]["next_followup_at"] = datetime.utcnow() + timedelta(days=3)
    else:
        # Incoming email - mark as needs attention if we were waiting
        update["$set"]["status"] = ThreadStatus.OPEN
        update["$inc"]["unread_count"] = 1

    result = await db.threads.update_one(
        {"user_id": user_id, "thread_id": thread_id},
        update
    )

    return result.modified_count > 0


async def get_threads_by_status(
    user_id: str,
    status: Optional[ThreadStatus] = None,
    account_id: Optional[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Get threads filtered by status."""
    db = await get_db()

    query = {"user_id": user_id}
    if status:
        query["status"] = status
    if account_id:
        query["account_id"] = account_id

    cursor = db.threads.find(query).sort("last_activity_at", -1).limit(limit)

    threads = []
    async for thread in cursor:
        thread["id"] = str(thread.pop("_id"))
        threads.append(thread)

    return threads


async def get_waiting_threads(
    user_id: str,
    overdue_only: bool = False
) -> List[Dict[str, Any]]:
    """Get threads waiting for response, optionally only overdue ones."""
    db = await get_db()

    query = {
        "user_id": user_id,
        "status": ThreadStatus.WAITING
    }

    if overdue_only:
        query["next_followup_at"] = {"$lt": datetime.utcnow()}

    cursor = db.threads.find(query).sort("next_followup_at", 1)

    threads = []
    async for thread in cursor:
        thread["id"] = str(thread.pop("_id"))
        # Calculate days waiting
        if thread.get("last_user_reply_at"):
            delta = datetime.utcnow() - thread["last_user_reply_at"]
            thread["days_waiting"] = delta.days
        threads.append(thread)

    return threads


async def get_thread_stats(user_id: str, account_id: Optional[str] = None) -> Dict[str, Any]:
    """Get thread statistics."""
    db = await get_db()

    query = {"user_id": user_id}
    if account_id:
        query["account_id"] = account_id

    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]

    stats = {"OPEN": 0, "WAITING": 0, "DONE": 0, "total": 0}

    async for doc in db.threads.aggregate(pipeline):
        stats[doc["_id"]] = doc["count"]
        stats["total"] += doc["count"]

    # Count overdue
    overdue = await db.threads.count_documents({
        **query,
        "status": ThreadStatus.WAITING,
        "next_followup_at": {"$lt": datetime.utcnow()}
    })
    stats["overdue"] = overdue

    return stats


async def auto_classify_thread(
    user_id: str,
    thread_id: str,
    email_data: Dict[str, Any]
) -> ThreadStatus:
    """
    Auto-classify thread status based on email content.
    Returns the determined status.
    """
    # Check if user is the sender (outgoing email)
    db = await get_db()
    account = await db.accounts.find_one({"user_id": user_id})

    if account:
        user_email = account.get("email", "").lower()
        from_email = email_data.get("from_email", "").lower()

        if user_email and from_email == user_email:
            # User sent this email - mark as WAITING
            return ThreadStatus.WAITING

    # Incoming email - mark as OPEN (needs attention)
    return ThreadStatus.OPEN
