"""
Conversations API routes: persist chat history.
"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/conversations", tags=["conversations"])


# ============================================================
# MODELS
# ============================================================

class MessageModel(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ConversationCreate(BaseModel):
    title: Optional[str] = None
    messages: List[MessageModel] = []


class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    messages: Optional[List[MessageModel]] = None


# ============================================================
# ROUTES
# ============================================================

@router.get("")
async def list_conversations(
    user_id: str = Query("default_user"),
    limit: int = Query(20, le=50),
    offset: int = Query(0)
) -> Dict[str, Any]:
    """List all conversations for a user, sorted by most recent."""
    db = await get_db()

    cursor = db.conversations.find(
        {"user_id": user_id},
        {"_id": 0, "conversation_id": 1, "title": 1, "preview": 1, "message_count": 1, "created_at": 1, "updated_at": 1}
    ).sort("updated_at", -1).skip(offset).limit(limit)

    conversations = await cursor.to_list(limit)
    total = await db.conversations.count_documents({"user_id": user_id})

    return {
        "conversations": conversations,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    user_id: str = Query("default_user")
) -> Dict[str, Any]:
    """Get a single conversation with all messages."""
    db = await get_db()

    conv = await db.conversations.find_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"_id": 0}
    )

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return conv


@router.post("")
async def create_conversation(
    body: ConversationCreate,
    user_id: str = Query("default_user")
) -> Dict[str, Any]:
    """Create a new conversation."""
    db = await get_db()

    now = datetime.utcnow()
    conversation_id = str(uuid.uuid4())

    # Generate title from first message if not provided
    title = body.title
    if not title and body.messages:
        first_user_msg = next((m.content for m in body.messages if m.role == "user"), None)
        if first_user_msg:
            title = first_user_msg[:50] + ("..." if len(first_user_msg) > 50 else "")

    # Generate preview from last message
    preview = ""
    if body.messages:
        last_msg = body.messages[-1]
        preview = last_msg.content[:100] + ("..." if len(last_msg.content) > 100 else "")

    conv = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": title or "Nouvelle conversation",
        "preview": preview,
        "messages": [{"role": m.role, "content": m.content} for m in body.messages],
        "message_count": len(body.messages),
        "created_at": now,
        "updated_at": now
    }

    await db.conversations.insert_one(conv)

    return {
        "conversation_id": conversation_id,
        "title": conv["title"],
        "created_at": now.isoformat()
    }


@router.put("/{conversation_id}")
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    user_id: str = Query("default_user")
) -> Dict[str, Any]:
    """Update a conversation (add messages, change title)."""
    db = await get_db()

    # Check exists
    existing = await db.conversations.find_one(
        {"conversation_id": conversation_id, "user_id": user_id}
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Conversation not found")

    now = datetime.utcnow()
    update = {"updated_at": now}

    if body.title is not None:
        update["title"] = body.title

    if body.messages is not None:
        messages = [{"role": m.role, "content": m.content} for m in body.messages]
        update["messages"] = messages
        update["message_count"] = len(messages)

        # Update preview
        if messages:
            last_msg = messages[-1]
            update["preview"] = last_msg["content"][:100] + ("..." if len(last_msg["content"]) > 100 else "")

    await db.conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {"$set": update}
    )

    return {"status": "updated", "conversation_id": conversation_id}


@router.post("/{conversation_id}/messages")
async def add_message(
    conversation_id: str,
    message: MessageModel,
    user_id: str = Query("default_user")
) -> Dict[str, Any]:
    """Add a single message to a conversation."""
    db = await get_db()

    now = datetime.utcnow()

    result = await db.conversations.update_one(
        {"conversation_id": conversation_id, "user_id": user_id},
        {
            "$push": {"messages": {"role": message.role, "content": message.content}},
            "$inc": {"message_count": 1},
            "$set": {
                "updated_at": now,
                "preview": message.content[:100] + ("..." if len(message.content) > 100 else "")
            }
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "added"}


@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user_id: str = Query("default_user")
) -> Dict[str, str]:
    """Delete a conversation."""
    db = await get_db()

    result = await db.conversations.delete_one(
        {"conversation_id": conversation_id, "user_id": user_id}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return {"status": "deleted"}


@router.get("/current/active")
async def get_or_create_active(
    user_id: str = Query("default_user")
) -> Dict[str, Any]:
    """Get the most recent conversation or create a new one."""
    db = await get_db()

    # Get most recent
    conv = await db.conversations.find_one(
        {"user_id": user_id},
        {"_id": 0},
        sort=[("updated_at", -1)]
    )

    if conv:
        return conv

    # Create new
    now = datetime.utcnow()
    conversation_id = str(uuid.uuid4())

    new_conv = {
        "conversation_id": conversation_id,
        "user_id": user_id,
        "title": "Nouvelle conversation",
        "preview": "",
        "messages": [],
        "message_count": 0,
        "created_at": now,
        "updated_at": now
    }

    await db.conversations.insert_one(new_conv)
    del new_conv["_id"]

    return new_conv
