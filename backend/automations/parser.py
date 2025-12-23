"""
Automation Parser
=================
Parse natural language requests into automation configurations.
"""

import re
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime

from .models import (
    AutomationConfig,
    AutomationTrigger,
    AutomationAction,
    TriggerType,
    ActionType
)

logger = logging.getLogger(__name__)

# Known vendors mapping
KNOWN_VENDORS = {
    "distram": ["distram", "facturation@distram.com"],
    "promocash": ["promocash", "no-reply@promocash.com"],
    "metro": ["metro", "factures@metro.fr"],
    "transgourmet": ["transgourmet"],
    "brake": ["brake"],
    "davigel": ["davigel"],
    "sysco": ["sysco"],
    "pomona": ["pomona"],
    "khadispal": ["khadispal"],
    "orcun": ["orcun"],
}

# Frequency patterns
FREQUENCY_PATTERNS = {
    "daily": [r"chaque\s+jour", r"tous\s+les\s+jours", r"quotidien"],
    "weekly": [r"chaque\s+semaine", r"toutes?\s+les\s+semaines?", r"hebdomadaire"],
    "monthly": [r"chaque\s+mois", r"tous\s+les\s+mois", r"mensuel"],
    "monday": [r"chaque\s+lundi", r"tous\s+les\s+lundis?"],
    "friday": [r"chaque\s+vendredi", r"tous\s+les\s+vendredis?"],
}

DAY_MAPPING = {
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3,
    "vendredi": 4, "samedi": 5, "dimanche": 6,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def extract_vendors(text: str) -> List[str]:
    """Extract vendor names from text."""
    text_lower = text.lower()
    found_vendors = []

    for vendor_key, aliases in KNOWN_VENDORS.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                if vendor_key not in found_vendors:
                    found_vendors.append(vendor_key)
                break

    return found_vendors


def extract_frequency(text: str) -> Tuple[str, Optional[int]]:
    """Extract frequency and day of week from text."""
    text_lower = text.lower()

    # Check for specific day
    for day_name, day_num in DAY_MAPPING.items():
        if day_name in text_lower:
            return "weekly", day_num

    # Check frequency patterns
    for freq, patterns in FREQUENCY_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                if freq in ["monday", "friday"]:
                    return "weekly", DAY_MAPPING.get(freq.replace("monday", "lundi").replace("friday", "vendredi"), 0)
                return freq, None

    # Default to weekly on Monday
    return "weekly", 0


def extract_hour(text: str) -> int:
    """Extract hour from text."""
    # Look for patterns like "à 9h", "9 heures", "à 14h"
    hour_match = re.search(r'[àa]\s*(\d{1,2})\s*h', text.lower())
    if hour_match:
        return int(hour_match.group(1))

    # Look for "matin" (morning) or "soir" (evening)
    if "matin" in text.lower():
        return 9
    if "soir" in text.lower():
        return 18

    return 9  # Default to 9 AM


def detect_automation_intent(text: str) -> bool:
    """Detect if the text is requesting an automation."""
    automation_patterns = [
        r"(crée|créer|créez|fais|faire|met|mets|mettre)\s*(en place)?\s*(une?|l[ea])?\s*automatisation",
        r"automatise",
        r"chaque\s+(semaine|jour|mois|lundi|mardi|mercredi|jeudi|vendredi)",
        r"tous\s+les\s+(jours|semaines|mois|lundis?|mardis?)",
        r"récupère.*automatiquement",
        r"surveille.*et.*(alerte|notifie)",
        r"(envoie|envoi).*rapport.*chaque",
        r"met.*dans.*tableau.*chaque",
    ]

    text_lower = text.lower()
    for pattern in automation_patterns:
        if re.search(pattern, text_lower):
            return True
    return False


def extract_table_name(text: str, vendors: List[str]) -> str:
    """Generate a table name from the request."""
    year = datetime.now().year

    # Check if user specified a name
    name_match = re.search(r"tableau\s+['\"]?([^'\"]+)['\"]?", text.lower())
    if name_match:
        return name_match.group(1).strip().title()

    # Generate from vendors
    if vendors:
        if len(vendors) == 1:
            return f"Factures {vendors[0].title()} {year}"
        elif len(vendors) <= 3:
            return f"Factures {', '.join(v.title() for v in vendors)} {year}"
        else:
            return f"Factures Fournisseurs {year}"

    return f"Factures {year}"


def extract_automation_name(text: str, vendors: List[str]) -> str:
    """Generate an automation name."""
    if vendors:
        if len(vendors) == 1:
            return f"Suivi factures {vendors[0].title()}"
        elif len(vendors) <= 3:
            return f"Suivi {', '.join(v.title() for v in vendors)}"
        else:
            return "Suivi factures fournisseurs"

    return "Suivi automatique"


def parse_automation_request(text: str) -> Optional[AutomationConfig]:
    """
    Parse a natural language request into an automation configuration.

    Examples:
    - "Crée une automatisation qui récupère chaque semaine les factures de distram et promocash"
    - "Chaque lundi, récupère les factures et mets les dans un tableau"
    - "Automatise le suivi des factures Metro tous les mois"
    """
    if not detect_automation_intent(text):
        return None

    # Extract components
    vendors = extract_vendors(text)
    frequency, day_of_week = extract_frequency(text)
    hour = extract_hour(text)

    # Build trigger
    if frequency == "daily":
        cron = f"0 {hour} * * *"
    elif frequency == "weekly":
        dow = day_of_week if day_of_week is not None else 0
        cron = f"0 {hour} * * {dow}"
    elif frequency == "monthly":
        cron = f"0 {hour} 1 * *"  # First day of month
    else:
        cron = f"0 {hour} * * 0"  # Default: every Monday

    trigger = AutomationTrigger(
        type=TriggerType.SCHEDULE,
        cron=cron,
        frequency=frequency,
        day_of_week=day_of_week,
        hour=hour,
        minute=0
    )

    # Build actions
    actions = [
        AutomationAction(
            type=ActionType.SEARCH_INVOICES,
            vendors=vendors
        ),
        AutomationAction(
            type=ActionType.EXTRACT_AMOUNTS
        ),
        AutomationAction(
            type=ActionType.UPDATE_TABLE
        )
    ]

    # Check for alert request
    if re.search(r"(alerte|notifie|préviens)", text.lower()):
        # Look for threshold
        threshold_match = re.search(r"(\d+(?:[.,]\d+)?)\s*€", text)
        threshold = float(threshold_match.group(1).replace(",", ".")) if threshold_match else None

        actions.append(AutomationAction(
            type=ActionType.SEND_ALERT,
            alert_threshold=threshold
        ))

    # Build config
    config = AutomationConfig(
        name=extract_automation_name(text, vendors),
        description=text[:200],
        trigger=trigger,
        actions=actions,
        vendors=vendors
    )

    logger.info(f"🤖 Parsed automation: {config.name} ({frequency}, vendors={vendors})")
    return config


def format_automation_summary(config: AutomationConfig) -> str:
    """Format automation config as a human-readable summary."""
    freq_text = {
        "daily": "Chaque jour",
        "weekly": "Chaque semaine",
        "monthly": "Chaque mois"
    }.get(config.trigger.frequency, "Régulièrement")

    if config.trigger.day_of_week is not None:
        day_names = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
        freq_text = f"Chaque {day_names[config.trigger.day_of_week]}"

    freq_text += f" à {config.trigger.hour}h"

    vendors_text = ", ".join(v.title() for v in config.vendors) if config.vendors else "Tous fournisseurs"

    return f"""**{config.name}**
⏰ {freq_text}
🏢 {vendors_text}"""
