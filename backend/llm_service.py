import json
import logging
from typing import List, Dict, Any
from backend.llm_router import resolve_and_call, LLMError
from backend.database import get_db

logger = logging.getLogger(__name__)

async def llm_chat(messages: List[Dict[str, Any]], user_id: str = "default_user") -> Dict[str, Any]:
    db = await get_db()
    settings_doc = await db.settings.find_one({"user_id": user_id}) or {}
    llm_settings = {
        "provider": settings_doc.get("provider", "auto"),
        "openai_api_key": settings_doc.get("openai_api_key"),
        "emergent_api_key": settings_doc.get("emergent_api_key"),
        "emergent_base_url": settings_doc.get("emergent_base_url"),
    }
    messages = list(messages) + [
        {"role": "system", "content": "Return ONLY raw JSON. No markdown, no code fences."}
    ]
    content = await resolve_and_call(llm_settings, messages)
    if isinstance(content, dict):
        return content
    if isinstance(content, str):
        text = content.strip()
        if text.startswith("```json"):
            text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
        elif text.startswith("```"):
            text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()
        try:
            return json.loads(text)
        except Exception as e:
            raise LLMError(f"Invalid JSON from LLM: {text[:200]}")
    raise LLMError("Invalid LLM response type")
