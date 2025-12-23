import os
import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_EMERGENT_MODEL = os.getenv("EMERGENT_MODEL", "gpt-4o-mini")
DEFAULT_EMERGENT_BASE = os.getenv("EMERGENT_BASE_URL", "https://api.emergent.dev/v1")

class LLMError(Exception):
    pass

async def _post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    last_err = None
    for _ in range(2):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    return resp.json()
                last_err = f"status={resp.status_code} body={resp.text[:300]}"
        except Exception as e:
            last_err = str(e)
    raise LLMError(last_err or "LLM request failed")

async def call_openai(messages: List[Dict[str, Any]], api_key: str, model: Optional[str] = None) -> str:
    if not api_key:
        raise LLMError("Clé OpenAI manquante")
    url = "https://api.openai.com/v1/chat/completions"
    payload = {"model": model or DEFAULT_OPENAI_MODEL, "messages": messages, "temperature": 0.3}
    data = await _post_json(url, {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, payload)
    return data["choices"][0]["message"]["content"]

async def call_emergent(messages: List[Dict[str, Any]], api_key: str, model: Optional[str] = None, base_url: Optional[str] = None) -> str:
    if not api_key:
        raise LLMError("Clé Emergent manquante")
    url = (base_url or DEFAULT_EMERGENT_BASE).rstrip("/") + "/chat/completions"
    payload = {"model": model or DEFAULT_EMERGENT_MODEL, "messages": messages, "temperature": 0.3}
    data = await _post_json(url, {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, payload)
    return data["choices"][0]["message"]["content"]

async def resolve_and_call(settings: Dict[str, Any], messages: List[Dict[str, Any]]) -> str:
    provider = settings.get("provider", "auto")
    openai_key = settings.get("openai_api_key")
    emergent_key = settings.get("emergent_api_key")
    emergent_base = settings.get("emergent_base_url") or DEFAULT_EMERGENT_BASE

    def has_openai(): return bool(openai_key)
    def has_emergent(): return bool(emergent_key)

    if provider == "openai":
        if not has_openai():
            raise LLMError("Clé OpenAI manquante")
        chosen = "openai"
    elif provider == "emergent":
        if not has_emergent():
            raise LLMError("Clé Emergent manquante")
        chosen = "emergent"
    else:
        if has_emergent():
            chosen = "emergent"
        elif has_openai():
            chosen = "openai"
        else:
            raise LLMError("Aucune clé LLM configurée")

    logger.info(f"LLM provider chosen: {chosen}")
    if chosen == "openai":
        return await call_openai(messages, openai_key)
    return await call_emergent(messages, emergent_key, base_url=emergent_base)
