import os
import json
import logging
from typing import Dict, Any
import requests
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("EMERGENT_LLM_KEY")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = "gpt-4o"
        self.session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
    
    async def process_message(self, message: str, mode: str, user_id: str) -> Dict[str, Any]:
        """Traiter un message avec l'IA"""
        try:
            if mode == "discussion":
                # Mode discussion simple
                messages = [
                    {
                        "role": "system",
                        "content": "Tu es un assistant email intelligent et serviable. Tu aides l'utilisateur avec ses emails, mais en mode discussion, tu ne déclenches AUCUNE action. Tu conseilles, reformules, et brainstormes uniquement."
                    },
                    {"role": "user", "content": message}
                ]
                
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7
                    },
                    timeout=30
                )
                if response.status_code != 200:
                    raise Exception("LLM error")
                data = response.json()
                return {
                    "reply": data["choices"][0]["message"]["content"],
                    "action": "none"
                }
            
            else:
                # Mode actions
                system_prompt = """Tu es un assistant email intelligent. Tu peux déclencher des actions.

Quand l'utilisateur demande :
- Écrire/envoyer un email → action "send_email" avec emailDraft
- Chercher des emails → action "search_email" avec searchQuery
- Suivre un fichier attendu → action "track_file" avec expectedFile
- Sinon → action "none"

Réponds TOUJOURS en JSON :
{
  "reply": "ton message à l'utilisateur",
  "action": "none" | "send_email" | "search_email" | "track_file",
  "emailDraft": {
    "accountId": "id du compte (si connu, sinon null)",
    "to": "destinataire",
    "subject": "objet",
    "body": "corps sans signature",
    "signatureId": null
  },
  "searchQuery": {
    "accountId": null,
    "queryString": "requête Gmail/Outlook"
  },
  "expectedFile": {
    "title": "titre du fichier",
    "contact": "contact/fournisseur",
    "type": "facture/contrat/devis",
    "dueDate": "YYYY-MM-DD"
  }
}
"""
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ]
                
                response = self.session.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.3,
                        "response_format": {"type": "json_object"}
                    },
                    timeout=30
                )
                if response.status_code != 200:
                    raise Exception("LLM error")
                data = response.json()
                result = json.loads(data["choices"][0]["message"]["content"])
                return result
        
        except Exception as e:
            logger.error(f"Erreur IA: {e}")
            return {
                "reply": "Le moteur IA est temporairement indisponible.",
                "action": "none"
            }
