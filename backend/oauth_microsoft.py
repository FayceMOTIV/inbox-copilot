import msal
import os
from backend.database import db
from uuid import uuid4
import logging
import aiohttp

logger = logging.getLogger(__name__)

SCOPES = [
    "User.Read",
    "Mail.ReadWrite",
    "Mail.Send"
]

class MicrosoftOAuth:
    def __init__(self):
        self.client_id = os.getenv("MICROSOFT_CLIENT_ID")
        self.client_secret = os.getenv("MICROSOFT_CLIENT_SECRET")
        self.tenant_id = os.getenv("MICROSOFT_TENANT_ID", "common")
        self.redirect_uri = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:3000/api/auth/microsoft/callback")
        self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
    
    def get_auth_url(self) -> str:
        """Générer l'URL d'authentification OAuth"""
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        auth_url = app.get_authorization_request_url(
            scopes=SCOPES,
            redirect_uri=self.redirect_uri
        )
        
        return auth_url
    
    async def handle_callback(self, code: str) -> dict:
        """Gérer le callback OAuth et sauvegarder les tokens"""
        try:
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_by_authorization_code(
                code,
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            
            if "error" in result:
                raise Exception(f"Microsoft OAuth error: {result.get('error_description')}")
            
            access_token = result["access_token"]
            refresh_token = result.get("refresh_token")
            
            # Récupérer les infos utilisateur
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://graph.microsoft.com/v1.0/me",
                    headers={"Authorization": f"Bearer {access_token}"}
                ) as response:
                    user_info = await response.json()
            
            # Sauvegarder en base
            account_id = str(uuid4())
            account = {
                "account_id": account_id,
                "user_id": "default_user",
                "type": "microsoft",
                "email": user_info.get("mail") or user_info.get("userPrincipalName"),
                "name": user_info.get("displayName", user_info.get("mail")),
                "access_token": access_token,
                "refresh_token": refresh_token
            }
            
            # Vérifier si le compte existe déjà
            existing = await db.accounts.find_one({"email": account["email"], "type": "microsoft"})
            if existing:
                await db.accounts.update_one(
                    {"_id": existing["_id"]},
                    {"$set": account}
                )
            else:
                await db.accounts.insert_one(account)
            
            logger.info(f"✅ Compte Microsoft connecté: {account['email']}")
            return account
        
        except Exception as e:
            logger.error(f"Erreur Microsoft callback: {e}")
            raise
    
    async def get_access_token(self, account_id: str) -> str:
        """Récupérer le token d'accès d'un compte"""
        account = await db.accounts.find_one({"account_id": account_id})
        if not account:
            raise Exception(f"Compte {account_id} non trouvé")
        
        # TODO: Gérer le refresh token si expiré
        return account["access_token"]