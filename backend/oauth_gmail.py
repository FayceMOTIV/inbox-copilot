from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
from typing import Optional, Dict
from backend.database import get_db
from uuid import uuid4
import logging
from datetime import datetime, timedelta
import re
import time
logger = logging.getLogger(__name__)

DEBUG_LAST_CALLBACK: Dict[str, Optional[str]] = {
    "last_hit_at": None,
    "had_code": False,
    "had_state": False,
    "state_ok": False,
    "token_ok": False,
    "userinfo_ok": False,
    "saved_ok": False,
    "email": None,
    "error": None,
}

SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile'
]

class GmailOAuth:
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or "http://127.0.0.1:8000/api/auth/gmail/callback"
        self._state_store: Dict[str, float] = {}
        self.state_ttl_seconds = 600  # 10 minutes

    def _is_valid_value(self, value: Optional[str]) -> bool:
        if not value:
            return False
        bad_patterns = ["xxxxx", "XXXX", "123456", "PASTE", "YOUR_", "your_", "paste"]
        return not any(p.lower() in value.lower() for p in bad_patterns)

    def has_valid_credentials(self) -> bool:
        return self._is_valid_value(self.client_id) and self._is_valid_value(self.client_secret)

    def _store_state(self, state: str):
        # Simple in-memory state store with TTL
        now = time.time()
        # prune old
        self._state_store = {k: v for k, v in self._state_store.items() if now - v < self.state_ttl_seconds}
        self._state_store[state] = now

    def _consume_state(self, state: Optional[str]) -> bool:
        if not state:
            return False
        now = time.time()
        ts = self._state_store.pop(state, None)
        if ts is None:
            return False
        return now - ts < self.state_ttl_seconds
    
    def get_auth_url(self) -> str:
        """Générer l'URL d'authentification OAuth"""
        if not self.has_valid_credentials():
            logger.error("GOOGLE_CLIENT_ID/SECRET invalid. Set them in backend/.env.")
            raise Exception("GOOGLE_CLIENT_ID/SECRET invalid")
        logger.info(f"Using GOOGLE_REDIRECT_URI={self.redirect_uri}")
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        self._store_state(state)
        logger.info(f"Gmail OAuth start redirect_uri={self.redirect_uri}")
        
        return auth_url
    
    async def handle_callback(self, code: str, state: Optional[str] = None) -> dict:
        """Gérer le callback OAuth et sauvegarder les tokens"""
        try:
            DEBUG_LAST_CALLBACK.update({
                "last_hit_at": datetime.utcnow().isoformat() + "Z",
                "had_code": bool(code),
                "had_state": bool(state),
                "state_ok": False,
                "token_ok": False,
                "userinfo_ok": False,
                "saved_ok": False,
                "email": None,
                "error": None,
            })
            if not self._consume_state(state):
                DEBUG_LAST_CALLBACK["error"] = "Invalid state"
                raise Exception("Invalid OAuth state")
            DEBUG_LAST_CALLBACK["state_ok"] = True
            logger.info(f"CALLBACK HIT with redirect_uri={self.redirect_uri}")
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            # Échanger le code contre des tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            DEBUG_LAST_CALLBACK["token_ok"] = True
            logger.info(f"Gmail OAuth callback redirect_uri={self.redirect_uri}")
            
            # Récupérer les infos utilisateur
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            DEBUG_LAST_CALLBACK["userinfo_ok"] = True
            
            db = await get_db()

            now_iso = datetime.utcnow().isoformat() + "Z"
            # Sauvegarder en base
            account_id = str(uuid4())
            account = {
                "account_id": account_id,
                "user_id": "default_user",
                "type": "gmail",
                "provider": "gmail",
                "email": user_info.get("email"),
                "name": user_info.get("name", user_info.get("email")),
                "access_token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "token_uri": credentials.token_uri,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes,
                "connected_at": now_iso,
            }
            
            # Upsert par provider+email
            await db.accounts.update_one(
                {"email": user_info.get("email"), "provider": "gmail"},
                {"$set": account, "$setOnInsert": {"created_at": now_iso}},
                upsert=True
            )
            DEBUG_LAST_CALLBACK["saved_ok"] = True
            DEBUG_LAST_CALLBACK["email"] = user_info.get("email")
            
            logger.info(f"GMAIL SAVED {user_info.get('email')}")
            return account
        
        except Exception as e:
            DEBUG_LAST_CALLBACK["error"] = str(e)
            logger.exception(f"Erreur Gmail callback: {e}")
            raise
    
    async def get_credentials(self, account_id: str) -> Credentials:
        """Récupérer les credentials d'un compte"""
        db = await get_db()
        account = await db.accounts.find_one({"account_id": account_id})
        if not account:
            raise Exception(f"Compte {account_id} non trouvé")
        
        credentials = Credentials(
            token=account["access_token"],
            refresh_token=account.get("refresh_token"),
            token_uri=account.get("token_uri"),
            client_id=account.get("client_id"),
            client_secret=account.get("client_secret"),
            scopes=account.get("scopes")
        )
        
        # Rafraîchir si expiré
        if credentials.expired and credentials.refresh_token:
            from google.auth.transport.requests import Request
            credentials.refresh(Request())
            
            # Mettre à jour en base
            await db.accounts.update_one(
                {"account_id": account_id},
                {"$set": {"access_token": credentials.token}}
            )
        
        return credentials
