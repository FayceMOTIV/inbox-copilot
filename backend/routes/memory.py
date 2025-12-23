"""
Memory API routes: manage contacts, aliases, vendors, VIPs.
Allows users to view and correct their memory.
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.database import get_db
from backend.memory import upsert_alias, upsert_vendor, get_memory_stats

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/memory", tags=["memory"])


# ============================================================
# VIP ENDPOINTS
# ============================================================

class VIPCreate(BaseModel):
    label: str
    email: str


@router.get("/vips")
async def list_vips(user_id: str = Query("default_user")) -> Dict[str, Any]:
    """List all VIP contacts."""
    db = await get_db()

    cursor = db.vips.find({"user_id": user_id}).sort("created_at", -1)
    vips = []
    async for vip in cursor:
        vips.append({
            "id": str(vip["_id"]),
            "label": vip.get("label", ""),
            "email": vip.get("email", ""),
            "created_at": vip.get("created_at")
        })

    return {"vips": vips, "count": len(vips)}


@router.post("/vips")
async def create_vip(body: VIPCreate, user_id: str = Query("default_user")) -> Dict[str, Any]:
    """Add a VIP contact."""
    db = await get_db()

    # Check if already exists
    existing = await db.vips.find_one({
        "user_id": user_id,
        "email": body.email.lower()
    })
    if existing:
        return {"id": str(existing["_id"]), "message": "VIP already exists", "success": True}

    doc = {
        "user_id": user_id,
        "label": body.label,
        "email": body.email.lower(),
        "created_at": datetime.utcnow()
    }
    result = await db.vips.insert_one(doc)

    # Also add to important_patterns for classification impact
    await db.important_patterns.update_one(
        {"user_id": user_id, "pattern_type": "sender", "pattern_value": body.email.lower()},
        {"$set": {
            "user_id": user_id,
            "pattern_type": "sender",
            "pattern_value": body.email.lower(),
            "importance": "high",
            "label": body.label,
            "is_vip": True,
            "notify": True,
            "updated_at": datetime.utcnow()
        }},
        upsert=True
    )

    logger.info(f"VIP created: {body.label} <{body.email}>")
    return {"id": str(result.inserted_id), "success": True}


@router.delete("/vips/{vip_id}")
async def delete_vip(vip_id: str, user_id: str = Query("default_user")) -> Dict[str, str]:
    """Delete a VIP contact."""
    db = await get_db()

    try:
        oid = ObjectId(vip_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid VIP ID")

    # Get VIP email first
    vip = await db.vips.find_one({"_id": oid, "user_id": user_id})
    if not vip:
        raise HTTPException(status_code=404, detail="VIP not found")

    # Delete VIP
    await db.vips.delete_one({"_id": oid})

    # Also remove from important_patterns
    await db.important_patterns.delete_one({
        "user_id": user_id,
        "pattern_type": "sender",
        "pattern_value": vip["email"],
        "is_vip": True
    })

    return {"status": "deleted"}


# ============================================================
# MODELS
# ============================================================

class AliasCreate(BaseModel):
    key: str
    value: str
    confidence: float = 1.0


class VendorCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    last_invoice_email: Optional[str] = None
    keywords: Optional[List[str]] = None


# ============================================================
# CONTACTS
# ============================================================

@router.get("/contacts")
async def list_contacts(
    user_id: str = Query("default_user"),
    limit: int = Query(50, le=200),
    offset: int = Query(0)
) -> Dict[str, Any]:
    """List all contacts for a user."""
    db = await get_db()

    cursor = db.contacts.find(
        {"user_id": user_id},
        {"_id": 1, "email": 1, "name": 1, "first_name": 1, "last_name": 1,
         "role": 1, "companies": 1, "phones": 1, "seen_count": 1, "last_seen_at": 1}
    ).sort("last_seen_at", -1).skip(offset).limit(limit)

    contacts = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        contacts.append(doc)

    total = await db.contacts.count_documents({"user_id": user_id})

    return {
        "contacts": contacts,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: str, user_id: str = Query("default_user")) -> Dict[str, Any]:
    """Get a single contact by ID."""
    db = await get_db()

    try:
        oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact ID")

    contact = await db.contacts.find_one({"_id": oid, "user_id": user_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact["id"] = str(contact.pop("_id"))
    return contact


@router.delete("/contacts/{contact_id}")
async def delete_contact(contact_id: str, user_id: str = Query("default_user")) -> Dict[str, str]:
    """Delete a contact."""
    db = await get_db()

    try:
        oid = ObjectId(contact_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid contact ID")

    result = await db.contacts.delete_one({"_id": oid, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Contact not found")

    return {"status": "deleted"}


# ============================================================
# ALIASES
# ============================================================

@router.get("/aliases")
async def list_aliases(
    user_id: str = Query("default_user"),
    limit: int = Query(50, le=200),
    offset: int = Query(0)
) -> Dict[str, Any]:
    """List all aliases for a user."""
    db = await get_db()

    cursor = db.aliases.find(
        {"user_id": user_id},
        {"_id": 1, "key": 1, "value": 1, "confidence": 1, "auto_created": 1, "created_at": 1, "updated_at": 1}
    ).sort("key", 1).skip(offset).limit(limit)

    aliases = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        aliases.append(doc)

    total = await db.aliases.count_documents({"user_id": user_id})

    return {
        "aliases": aliases,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/aliases")
async def create_alias(body: AliasCreate, user_id: str = Query("default_user")) -> Dict[str, Any]:
    """Create or update an alias (manual = high priority)."""
    if not body.key or not body.value:
        raise HTTPException(status_code=400, detail="key and value required")

    await upsert_alias(
        user_id=user_id,
        key=body.key,
        value=body.value,
        confidence=body.confidence,
        auto_created=False  # Manual creation = not auto
    )

    db = await get_db()
    alias = await db.aliases.find_one({"user_id": user_id, "key": body.key.lower().strip()})
    if alias:
        alias["id"] = str(alias.pop("_id"))
        return alias

    return {"status": "created", "key": body.key, "value": body.value}


@router.delete("/aliases/{alias_id}")
async def delete_alias(alias_id: str, user_id: str = Query("default_user")) -> Dict[str, str]:
    """Delete an alias."""
    db = await get_db()

    try:
        oid = ObjectId(alias_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid alias ID")

    result = await db.aliases.delete_one({"_id": oid, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alias not found")

    return {"status": "deleted"}


@router.delete("/aliases/by-key/{key}")
async def delete_alias_by_key(key: str, user_id: str = Query("default_user")) -> Dict[str, str]:
    """Delete an alias by its key."""
    db = await get_db()

    result = await db.aliases.delete_one({"user_id": user_id, "key": key.lower().strip()})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alias not found")

    return {"status": "deleted"}


# ============================================================
# VENDORS
# ============================================================

@router.get("/vendors")
async def list_vendors(
    user_id: str = Query("default_user"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    include_candidates: bool = Query(False)
) -> Dict[str, Any]:
    """List all vendors for a user."""
    db = await get_db()

    query = {"user_id": user_id}
    if not include_candidates:
        query["$or"] = [{"candidate": False}, {"candidate": {"$exists": False}}]

    cursor = db.vendors.find(
        query,
        {"_id": 1, "name": 1, "domains": 1, "last_invoice_email": 1, "keywords": 1,
         "candidate": 1, "created_at": 1, "updated_at": 1}
    ).sort("name", 1).skip(offset).limit(limit)

    vendors = []
    async for doc in cursor:
        doc["id"] = str(doc.pop("_id"))
        vendors.append(doc)

    total = await db.vendors.count_documents(query)

    return {
        "vendors": vendors,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/vendors")
async def create_vendor(body: VendorCreate, user_id: str = Query("default_user")) -> Dict[str, Any]:
    """Create or update a vendor."""
    if not body.name:
        raise HTTPException(status_code=400, detail="name required")

    await upsert_vendor(
        user_id=user_id,
        name=body.name,
        domain=body.domain,
        last_invoice_email=body.last_invoice_email,
        keywords=body.keywords
    )

    db = await get_db()
    vendor = await db.vendors.find_one({"user_id": user_id, "name": body.name.lower().strip()})
    if vendor:
        vendor["id"] = str(vendor.pop("_id"))
        return vendor

    return {"status": "created", "name": body.name}


@router.delete("/vendors/{vendor_id}")
async def delete_vendor(vendor_id: str, user_id: str = Query("default_user")) -> Dict[str, str]:
    """Delete a vendor."""
    db = await get_db()

    try:
        oid = ObjectId(vendor_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid vendor ID")

    result = await db.vendors.delete_one({"_id": oid, "user_id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Vendor not found")

    return {"status": "deleted"}


# ============================================================
# STATS
# ============================================================

@router.get("/stats")
async def memory_stats(user_id: str = Query("default_user")) -> Dict[str, Any]:
    """Get memory statistics for a user."""
    stats = await get_memory_stats(user_id)
    return {
        "user_id": user_id,
        "stats": stats
    }
