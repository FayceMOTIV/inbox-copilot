"""
Prompt builder for Inbox Copilot.
Builds system prompts and messages for LLM calls.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


def load_prompt(name: str) -> str:
    """Load a prompt template from file."""
    path = PROMPTS_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def build_system_prompt(
    accounts: List[Dict[str, Any]],
    preferences: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build the system prompt with:
    - Core identity (ACTION-FIRST)
    - Policy rules
    - Tools/format instructions
    - Connected accounts
    - User preferences
    """
    prefs = preferences or {}

    # Connected accounts section
    if accounts:
        accounts_lines = "\n".join([
            f"- {a.get('provider', a.get('type', '?'))}: {a.get('email', '?')}"
            for a in accounts
        ])
    else:
        accounts_lines = "- Aucun compte connecté"

    parts = [
        load_prompt("system"),
        load_prompt("policy"),
        load_prompt("tools"),
        f"COMPTES CONNECTÉS:\n{accounts_lines}",
    ]

    # User preferences
    if prefs.get("confirm_before_send"):
        parts.append("PRÉFÉRENCE: Toujours demander confirmation avant d'envoyer un email.")

    return "\n\n---\n\n".join(parts)


def build_messages(
    user_message: str,
    accounts: List[Dict[str, Any]],
    tool_results: Optional[str] = None,
    prefs: Optional[Dict[str, Any]] = None,
    history: Optional[List[Dict[str, str]]] = None
) -> List[Dict[str, str]]:
    """
    Build messages array for LLM call.
    Includes system prompt, conversation history, and current message with tool results.
    """
    system = build_system_prompt(accounts, prefs)

    messages = [{"role": "system", "content": system}]

    # Add conversation history (last 6 messages max for context)
    if history:
        for msg in history[-6:]:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

    # Build current user content
    content_parts = [
        "[DEMANDE UTILISATEUR]",
        user_message,
    ]

    if tool_results:
        content_parts.extend([
            "",
            "[RÉSULTATS RECHERCHE]",
            tool_results,
        ])

    content_parts.extend([
        "",
        "[INSTRUCTIONS]",
        "Réponds selon le format défini. Sois concis et ACTION-FIRST.",
        "Si le message est une correction (ex: 'non, en 2025'), réinterprète la demande précédente avec cette correction.",
    ])

    messages.append({"role": "user", "content": "\n".join(content_parts)})

    return messages


def build_extraction_prompt(email_content: str, email_metadata: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build prompt for email extraction (contact info, intent, etc.).
    Forces JSON output.
    """
    system = """Tu es un extracteur de données email. Tu extrais UNIQUEMENT les informations présentes.

RÈGLES:
- Retourne UNIQUEMENT du JSON valide, sans backticks, sans explication
- Si une info n'est pas présente, utilise null
- Ne devine pas, n'invente pas

FORMAT ATTENDU:
{
  "contact": {
    "first_name": string|null,
    "last_name": string|null,
    "email": string|null,
    "phone": string|null,
    "company": string|null,
    "role": string|null
  },
  "documents": {
    "attachments": [{"name": string, "type": string}],
    "missing": string|null
  },
  "intent": string|null,
  "summary": string,
  "is_invoice": boolean,
  "vendor_name": string|null
}"""

    user = f"""Email à analyser:

De: {email_metadata.get('from', 'N/A')}
Sujet: {email_metadata.get('subject', 'N/A')}
Date: {email_metadata.get('date', 'N/A')}

Contenu:
{email_content[:3000]}

Extrais les informations et retourne le JSON."""

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
