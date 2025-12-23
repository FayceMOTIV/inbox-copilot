from backend.routes.email_extract import router as email_extract_router
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import re
from dotenv import load_dotenv
import logging
from pathlib import Path

load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

import backend.database as database
from backend.database import get_db
from backend.ai_service import AIService
from backend.llm_router import resolve_and_call, LLMError
from backend import prompt_builder
from backend.email_service import EmailService
from backend.oauth_gmail import GmailOAuth
from backend.oauth_microsoft import MicrosoftOAuth
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from backend.routes.copilot import router as copilot_router
from backend.routes.memory import router as memory_router
from backend.routes.conversations import router as conversations_router
from backend.routes.notifications import router as notifications_router, learning_router
from backend.routes.automations import router as automations_router, tables_router
from backend.routes.digest import router as digest_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Assistant Email IA Backend")
router = APIRouter()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", os.getenv("NEXT_PUBLIC_BASE_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length"],
)

# Services
ai_service = AIService()
email_service = EmailService()
gmail_oauth = GmailOAuth()
microsoft_oauth = MicrosoftOAuth()

# Models (ChatRequest defined near the chat endpoint)

class SendEmailRequest(BaseModel):
    account_id: str
    to: str
    subject: str
    body: str
    signature_id: Optional[str] = None

class SearchEmailRequest(BaseModel):
    account_id: str
    query_string: str

class SignatureRequest(BaseModel):
    account_id: str
    name: str
    content: str
    is_default: bool = False

class ExpectedFileRequest(BaseModel):
    # Accept both naming conventions (doc_type/vendor/keyword OR title/contact/file_type)
    doc_type: Optional[str] = None
    vendor: Optional[str] = None
    keyword: Optional[str] = None
    # Legacy field names
    title: Optional[str] = None
    contact: Optional[str] = None
    file_type: Optional[str] = None
    # Common fields
    due_date: Optional[str] = ""
    user_id: Optional[str] = "default_user"

    def get_doc_type(self) -> str:
        return self.doc_type or self.file_type or "document"

    def get_vendor(self) -> str:
        return self.vendor or self.contact or ""

    def get_keyword(self) -> str:
        return self.keyword or ""

    def get_title(self) -> str:
        if self.title:
            return self.title
        vendor = self.get_vendor()
        doc_type = self.get_doc_type()
        return f"{doc_type} - {vendor}" if vendor else doc_type

@app.on_event("startup")
async def startup():
    await database.init_db()

    # Start automation scheduler
    from backend.automations.scheduler import automation_scheduler
    from backend.automations.engine import automation_engine
    automation_scheduler.set_engine(automation_engine)
    await automation_scheduler.start()

    logger.info("✅ Backend FastAPI démarré")

# === OAUTH ROUTES ===

@router.get("/api/auth/gmail/start")
async def gmail_auth_start():
    """Démarre le flux OAuth Gmail"""
    try:
        if not gmail_oauth.has_valid_credentials():
            logger.error("GOOGLE_CLIENT_ID/SECRET invalid or missing")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "GOOGLE_CLIENT_ID/SECRET invalid",
                    "how_to_fix": "Set valid GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env, then restart the backend."
                }
            )
        auth_url = gmail_oauth.get_auth_url()
        logger.info(f"GOOGLE AUTH URL = {auth_url}")
        return RedirectResponse(url=auth_url, status_code=302)
    except Exception as e:
        logger.error(f"Erreur Gmail OAuth start: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/gmail/callback")
async def gmail_auth_callback(code: str, state: Optional[str] = None):
    """Callback OAuth Gmail"""
    frontend_base = os.getenv("FRONTEND_BASE_URL", "http://localhost:3000")
    try:
        logger.info("CALLBACK HIT")
        logger.info(f"Callback params code_present={bool(code)}, state_present={bool(state)}")
        await gmail_oauth.handle_callback(code, state)
        return RedirectResponse(url=f"{frontend_base}/parametres?gmail=connected")
    except Exception as e:
        logger.exception("GMAIL CALLBACK ERROR")
        if "state" in str(e).lower():
            return RedirectResponse(url=f"{frontend_base}/parametres?error=gmail_state")
        return RedirectResponse(url=f"{frontend_base}/parametres?error=gmail_callback")

@app.get("/api/auth/gmail/debug")
async def gmail_auth_debug():
    """Debug credentials sans exposer les secrets."""
    preview = ""
    if gmail_oauth.client_id:
        preview = gmail_oauth.client_id[:4] + "..." + gmail_oauth.client_id[-4:]
    return {
        "has_client_id": gmail_oauth._is_valid_value(gmail_oauth.client_id),
        "has_client_secret": gmail_oauth._is_valid_value(gmail_oauth.client_secret),
        "redirect_uri": gmail_oauth.redirect_uri,
        "client_id_preview": preview
    }

@app.get("/api/auth/gmail/_debug_last_callback")
async def gmail_debug_last():
    from backend.oauth_gmail import DEBUG_LAST_CALLBACK
    return DEBUG_LAST_CALLBACK

@app.get("/api/auth/gmail/_debug_db")
async def gmail_debug_db():
    db = await database.get_db()
    docs = await db.accounts.find({}, {"email": 1, "provider": 1, "_id": 0}).to_list(5)
    count = await db.accounts.count_documents({})
    return {"count": count, "accounts": docs}


# === LLM SETTINGS ===
@app.get("/api/settings/llm")
async def get_llm_settings(user_id: str = "default_user"):
    db = await database.get_db()
    doc = await db.settings.find_one({"user_id": user_id}) or {}
    return {
        "provider": doc.get("provider", "auto"),
        "openai_set": bool(doc.get("openai_api_key")),
        "emergent_set": bool(doc.get("emergent_api_key")),
    }

@app.post("/api/settings/llm")
async def save_llm_settings(payload: Dict[str, Any], user_id: str = "default_user"):
    db = await database.get_db()
    update = {"provider": payload.get("provider", "auto")}
    if payload.get("openai_api_key"):
        update["openai_api_key"] = payload["openai_api_key"]
    if payload.get("emergent_api_key"):
        update["emergent_api_key"] = payload["emergent_api_key"]
    if payload.get("emergent_base_url"):
        update["emergent_base_url"] = payload["emergent_base_url"]

    await db.settings.update_one({"user_id": user_id}, {"$set": update}, upsert=True)
    doc = await db.settings.find_one({"user_id": user_id}) or {}
    return {
        "provider": doc.get("provider", "auto"),
        "openai_set": bool(doc.get("openai_api_key")),
        "emergent_set": bool(doc.get("emergent_api_key")),
    }

@app.post("/api/settings/llm/test")
async def test_llm_settings(payload: Dict[str, Any] = None, user_id: str = "default_user"):
    payload = payload or {}
    db = await database.get_db()
    doc = await db.settings.find_one({"user_id": user_id}) or {}

    settings = {
        "provider": payload.get("provider") or doc.get("provider", "auto"),
        "openai_api_key": doc.get("openai_api_key"),
        "emergent_api_key": doc.get("emergent_api_key"),
        "emergent_base_url": doc.get("emergent_base_url"),
    }

    try:
        msg = [{"role": "system", "content": "Ping"}, {"role": "user", "content": "Réponds OK"}]
        await resolve_and_call(settings, msg)
        return {"ok": True}
    except Exception as e:
        logger.error(f"LLM test error: {e}")
        return {"ok": False, "error": str(e)}


app.include_router(router)
app.include_router(email_extract_router)
app.include_router(copilot_router)
app.include_router(memory_router)
app.include_router(conversations_router)
app.include_router(notifications_router)
app.include_router(learning_router)
app.include_router(automations_router)
app.include_router(tables_router)
app.include_router(digest_router)

@app.get("/api/gmail/search_debug")
async def gmail_search_debug(q: str = "newer_than:30d", user_id: str = "default_user"):
    """Debug: exécute une recherche Gmail directement (sans LLM)"""
    try:
        db = await database.get_db()
        acc = await db.accounts.find_one(
            {"user_id": user_id, "$or": [{"type": "gmail"}, {"provider": "gmail"}]},
            {"_id": 0, "account_id": 1, "email": 1, "type": 1, "provider": 1}
        )
        if not acc:
            raise HTTPException(status_code=404, detail="No Gmail account connected for this user_id")

        emails = await email_service.search_emails(acc["account_id"], q)
        return {"account": acc, "query": q, "count": len(emails), "emails": emails[:3]}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("gmail_search_debug error")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/auth/microsoft/start")
async def microsoft_auth_start():
    """Démarre le flux OAuth Microsoft"""
    try:
        auth_url = microsoft_oauth.get_auth_url()
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error(f"Erreur Microsoft OAuth start: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/auth/microsoft/callback")
async def microsoft_auth_callback(code: str, state: Optional[str] = None):
    """Callback OAuth Microsoft"""
    try:
        account = await microsoft_oauth.handle_callback(code)
        return RedirectResponse(url=f"http://localhost:3000/parametres?success=microsoft")
    except Exception as e:
        logger.error(f"Erreur Microsoft callback: {e}")
        return RedirectResponse(url=f"http://localhost:3000/parametres?error=microsoft")

# === CHAT / IA ===

from backend.copilot_engine import build_action_context, format_results_for_llm, Intent

class ChatRequest(BaseModel):
    message: str
    mode: str  # "actions" or "discussion"
    user_id: Optional[str] = "default_user"
    history: Optional[List[Dict[str, str]]] = None
    active_email: Optional[Dict[str, Any]] = None  # Currently discussed email


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """
    Endpoint principal de chat avec l'IA.
    Utilise le copilot engine unifié pour:
    - Détecter l'intention
    - Chercher emails avec mémoire (aliases, contacts, vendors)
    - Résoudre les références
    - Exécuter des actions (télécharger PJ, etc.)
    - Puis appeler le LLM
    """
    try:
        db = await database.get_db()

        accounts = await db.accounts.find({"user_id": request.user_id}, {"_id": 0}).to_list(50)
        prefs = await db.settings.find_one({"user_id": request.user_id}) or {}

        # Use copilot engine to build context (search, resolve, etc.)
        context = await build_action_context(
            user_id=request.user_id,
            message=request.message,
            accounts=accounts,
            active_email=request.active_email
        )

        tool_results_text = format_results_for_llm(context)

        # Build LLM messages with conversation history
        messages = prompt_builder.build_messages(
            request.message,
            accounts,
            tool_results=tool_results_text,
            prefs=prefs,
            history=request.history
        )

        settings_doc = await db.settings.find_one({"user_id": request.user_id}) or {}
        llm_settings = {
            "provider": settings_doc.get("provider", "auto"),
            "openai_api_key": settings_doc.get("openai_api_key"),
            "emergent_api_key": settings_doc.get("emergent_api_key"),
            "emergent_base_url": settings_doc.get("emergent_base_url"),
        }

        try:
            reply = await resolve_and_call(llm_settings, messages)
        except LLMError as e:
            logger.error(f"LLM error: {e}")
            reply = "Le moteur IA est temporairement indisponible."

        # Determine action based on context
        action = "none"
        if context["intent"] == Intent.COUNT_ANALYZE:
            # COUNT_ANALYZE with attachments = open download panel
            if context.get("attachments"):
                action = "download_attachments"
            elif context.get("search_results"):
                action = "show_email"
        elif context["intent"] in [Intent.SEARCH_EMAIL, Intent.OPEN_EMAIL] and context.get("search_results"):
            action = "show_email"
        elif context["intent"] == Intent.DOWNLOAD_ATTACHMENT:
            action = "download_attachments"
        elif context["intent"] == Intent.REPLY_EMAIL:
            action = "compose_reply"
        elif context["intent"] == Intent.SEND_EMAIL:
            action = "compose_email"
        elif context["intent"] == Intent.CREATE_AUTOMATION:
            action = "automation_created" if context.get("automation_created") else "none"

        # Get account ID for actions
        account = next((a for a in accounts if a.get("type") == "gmail"), accounts[0] if accounts else None)
        account_id = account.get("account_id") if account else None

        # Check if multi-email mode
        is_multi = context.get("multi_email", False)

        return {
            "reply": reply,
            "action": action,
            "account_id": account_id,
            "email": context.get("email_details") or context.get("target_email"),
            "attachments": context.get("attachments", []),
            "suggested_actions": context.get("suggested_actions", []),
            # Multi-email support
            "multi_email": is_multi,
            "emails_with_attachments": context.get("emails_with_attachments", []) if is_multi else [],
            # Automation support
            "automation": context.get("automation_created"),
            "context": {
                "intent": context["intent"],
                "search_results": context.get("search_results", [])[:5],
                "resolved_refs": context.get("resolved_refs", [])
            }
        }

    except Exception as e:
        logger.error(f"Erreur chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))



# === EMAIL OPERATIONS ===

@app.post("/api/email/send")
async def send_email(request: SendEmailRequest):
    """Envoyer un email"""
    try:
        result = await email_service.send_email(
            account_id=request.account_id,
            to=request.to,
            subject=request.subject,
            body=request.body,
            signature_id=request.signature_id
        )
        return result
    except Exception as e:
        logger.error(f"Erreur envoi email: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/email/search")
async def search_emails(request: SearchEmailRequest):
    """Rechercher des emails"""
    try:
        results = await email_service.search_emails(
            account_id=request.account_id,
            query_string=request.query_string
        )
        return {"results": results}
    except Exception as e:
        logger.error(f"Erreur recherche email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AttachmentsRequest(BaseModel):
    account_id: str
    message_id: str
    save_dir: Optional[str] = "/tmp/attachments"


@app.get("/api/email/{message_id}")
async def get_email_details(message_id: str, account_id: str):
    """Get full email details including attachments info"""
    try:
        email = await email_service.get_email_by_id(account_id, message_id)
        return email
    except Exception as e:
        logger.error(f"Erreur récupération email: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/email/attachments/download")
async def download_email_attachments(request: AttachmentsRequest):
    """Download all attachments from an email to server"""
    import os
    try:
        os.makedirs(request.save_dir, exist_ok=True)

        downloaded = await email_service.download_all_attachments(
            account_id=request.account_id,
            message_id=request.message_id,
            save_dir=request.save_dir
        )
        return {
            "success": True,
            "message": f"{len(downloaded)} pièce(s) jointe(s) téléchargée(s)",
            "files": downloaded
        }
    except Exception as e:
        logger.error(f"Erreur téléchargement pièces jointes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


from fastapi.responses import StreamingResponse
import io

@app.get("/api/email/{message_id}/attachment/{attachment_id}")
async def download_single_attachment(
    message_id: str,
    attachment_id: str,
    account_id: str
):
    """Download a single attachment - returns file for browser download"""
    try:
        data, filename, mime_type = await email_service.download_attachment(
            account_id=account_id,
            message_id=message_id,
            attachment_id=attachment_id
        )

        # Return as downloadable file
        return StreamingResponse(
            io.BytesIO(data),
            media_type=mime_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(data))
            }
        )
    except Exception as e:
        logger.error(f"Erreur téléchargement: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === ACCOUNTS ===

@app.get("/api/accounts")
async def get_accounts(user_id: str = "default_user"):
    """Liste des comptes email connectés"""
    try:
        db = await database.get_db()
        accounts = await db.accounts.find({"user_id": user_id}, {
            "_id": 0,
            "account_id": 1,
            "provider": 1,
            "type": 1,
            "email": 1,
            "name": 1,
            "scopes": 1,
            "connected_at": 1,
            "created_at": 1,
            "user_id": 1
        }).to_list(100)
        return {"accounts": accounts}
    except Exception as e:
        logger.error(f"Erreur get accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.delete("/api/accounts/{account_id}")
async def delete_account(account_id: str):
    """Supprimer un compte"""
    try:
        db = await get_db()
        result = await db.accounts.delete_one({"account_id": account_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Compte non trouvé")
        return {"success": True}
    except Exception as e:
        logger.error(f"Erreur delete account: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === SIGNATURES ===

@app.get("/api/signatures")
async def get_signatures(account_id: Optional[str] = None, user_id: str = "default_user"):
    """Liste des signatures"""
    try:
        db = await get_db()
        query = {"user_id": user_id}
        if account_id:
            query["account_id"] = account_id
        signatures = await db.signatures.find(query).to_list(100)
        return {"signatures": signatures}
    except Exception as e:
        logger.error(f"Erreur get signatures: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/signatures")
async def create_signature(request: SignatureRequest, user_id: str = "default_user"):
    """Créer une signature"""
    try:
        db = await get_db()
        # Si c'est la signature par défaut, retirer le flag des autres
        if request.is_default:
            await db.signatures.update_many(
                {"account_id": request.account_id, "user_id": user_id},
                {"$set": {"is_default": False}}
            )
        
        from uuid import uuid4
        signature = {
            "signature_id": str(uuid4()),
            "account_id": request.account_id,
            "user_id": user_id,
            "name": request.name,
            "content": request.content,
            "is_default": request.is_default
        }
        await db.signatures.insert_one(signature)
        return {"signature": signature}
    except Exception as e:
        logger.error(f"Erreur create signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/signatures/{signature_id}")
async def update_signature(signature_id: str, request: SignatureRequest):
    """Mettre à jour une signature"""
    try:
        db = await get_db()
        if request.is_default:
            await db.signatures.update_many(
                {"account_id": request.account_id},
                {"$set": {"is_default": False}}
            )
        
        result = await db.signatures.update_one(
            {"signature_id": signature_id},
            {"$set": {
                "name": request.name,
                "content": request.content,
                "is_default": request.is_default
            }}
        )
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Signature non trouvée")
        return {"success": True}
    except Exception as e:
        logger.error(f"Erreur update signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/signatures/{signature_id}")
async def delete_signature(signature_id: str):
    """Supprimer une signature"""
    try:
        db = await get_db()
        result = await db.signatures.delete_one({"signature_id": signature_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Signature non trouvée")
        return {"success": True}
    except Exception as e:
        logger.error(f"Erreur delete signature: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# === EXPECTED FILES ===

@app.get("/api/expected-files")
async def get_expected_files(user_id: str = "default_user"):
    """Liste des fichiers attendus"""
    try:
        db = await get_db()
        files = await db.expected_files.find({"user_id": user_id}, {"_id": 0}).to_list(100)
        return {"files": files}
    except Exception as e:
        logger.error(f"Erreur get expected files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expected-files")
async def create_expected_file(request: ExpectedFileRequest):
    """Créer un fichier attendu. Accepts both field naming conventions."""
    try:
        # Extract normalized values
        vendor = request.get_vendor()
        doc_type = request.get_doc_type()
        keyword = request.get_keyword()
        title = request.get_title()

        # Validate vendor is provided
        if not vendor or not vendor.strip():
            raise HTTPException(status_code=400, detail="vendor (or contact) is required")

        db = await get_db()
        from uuid import uuid4
        expected_file = {
            "file_id": str(uuid4()),
            "user_id": request.user_id,
            # Store with canonical field names
            "doc_type": doc_type,
            "vendor": vendor.strip(),
            "keyword": keyword,
            "title": title,
            "due_date": request.due_date or "",
            "status": "pending",
            "last_check": None,
            "associated_email": None
        }
        await db.expected_files.insert_one(expected_file)
        # Remove ObjectId before returning
        expected_file.pop("_id", None)
        return {"file": expected_file}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur create expected file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/expected-files/scan")
async def scan_expected_files(user_id: str = "default_user"):
    """Scanner les emails pour trouver les fichiers attendus"""
    try:
        db = await get_db()
        files = await db.expected_files.find({"user_id": user_id, "status": "pending"}).to_list(100)
        accounts = await db.accounts.find({"user_id": user_id}).to_list(100)

        results = []
        for file in files:
            for account in accounts:
                # Support both old and new field names
                vendor = file.get('vendor') or file.get('contact', '')
                doc_type = file.get('doc_type') or file.get('file_type', '')
                # Construire une requête de recherche
                query = f"from:{vendor} {doc_type} has:attachment"
                
                try:
                    emails = await email_service.search_emails(
                        account_id=account["account_id"],
                        query_string=query
                    )
                    
                    if emails:
                        # Fichier trouvé !
                        await db.expected_files.update_one(
                            {"file_id": file["file_id"]},
                            {"$set": {
                                "status": "received",
                                "last_check": "now",
                                "associated_email": emails[0]
                            }}
                        )
                        results.append({
                            "file_id": file["file_id"],
                            "status": "found",
                            "email": emails[0]
                        })
                        break
                except Exception as e:
                    logger.error(f"Erreur scan file {file['file_id']}: {e}")
                    continue
        
        return {"scanned": len(files), "found": len(results), "results": results}
    except Exception as e:
        logger.error(f"Erreur scan expected files: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/expected-files/{file_id}")
async def delete_expected_file(file_id: str):
    """Supprimer un fichier attendu"""
    try:
        db = await get_db()
        result = await db.expected_files.delete_one({"file_id": file_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Fichier non trouvé")
        return {"success": True}
    except Exception as e:
        logger.error(f"Erreur delete expected file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health():
    """Health check"""
    mongo_ok = False
    try:
        db = await database.get_db()
        mongo_ok = (db is not None)
    except Exception as e:
        logger.error(f"Health check Mongo error: {e}")
        mongo_ok = False
    return {"status": "ok", "mongo": mongo_ok}
