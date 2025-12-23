from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from googleapiclient.errors import HttpError

from backend.extraction import build_extraction_input
from backend.llm_service import llm_chat
from backend.email_service import EmailService
from backend.database import get_db
from backend.memory import process_extraction

router = APIRouter(prefix="/api/email", tags=["email"])


class ExtractRequest(BaseModel):
    account_id: Optional[str] = None
    email_id: Optional[str] = None
    user_id: str = "default_user"


email_service = EmailService()


@router.post("/extract")
async def extract_email(req: ExtractRequest) -> Dict[str, Any]:
    db = await get_db()
    account_id = req.account_id
    user_id = req.user_id
    if not account_id:
        doc = await db.accounts.find_one({"user_id": user_id})
        if doc:
            account_id = doc.get("account_id")
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id required")

    try:
        if req.email_id:
            email_obj = await email_service.get_email_by_id(account_id, req.email_id)
        else:
            email_obj = await email_service.get_latest_email(account_id)
    except HttpError as he:
        msg = str(he)
        status = getattr(he, "resp", None).status if getattr(he, "resp", None) else None
        if status == 403 and "accessNotConfigured" in msg:
            raise HTTPException(
                status_code=503,
                detail="Gmail API disabled for the Google Cloud project used by OAuth. Enable Gmail API in Google Cloud Console, then retry."
            )
        raise HTTPException(status_code=502, detail="Erreur Gmail API")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not email_obj:
        raise HTTPException(status_code=404, detail="email not found")

    payload = build_extraction_input(email_obj)

    messages = [
        {
            "role": "system",
            "content": "Tu es un moteur d'extraction JSON. Réponds STRICTEMENT en JSON selon le schéma fourni. Si inconnu, mets null."
        },
        {
            "role": "user",
            "content": (
                "Schema: {contact:{first_name,last_name,email,phone,company}, documents:{attachments,missing}, intent, summary}. "
                "Input: " + str(payload)
            ),
        },
    ]

    try:
        extraction = await llm_chat(messages, user_id=user_id)
        if not isinstance(extraction, dict):
            raise HTTPException(status_code=502, detail="LLM returned invalid JSON")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM returned invalid JSON: {str(e)[:200]}")

    try:
        await process_extraction(user_id, email_obj, extraction)
    except Exception:
        pass

    return {"email": email_obj, "extraction": extraction, "input": payload}
