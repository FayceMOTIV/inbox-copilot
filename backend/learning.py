"""
ARIA Learning System - Mémoire et Apprentissage
================================================
Système intelligent qui permet à ARIA de :
- Apprendre les correspondances expéditeurs (Promocash → noreply@promocash.fr)
- Retenir les préférences utilisateur
- Mémoriser les FAQ et réponses fréquentes
- Analyser les patterns d'emails importants
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from backend.database import get_db

logger = logging.getLogger(__name__)


# ============================================================
# SENDER MAPPING - Apprendre les vrais expéditeurs
# ============================================================

async def learn_sender(user_id: str, name: str, email: str, context: str = None):
    """
    Apprend la correspondance entre un nom (ex: "Promocash") et l'email réel.
    Appelé automatiquement quand on trouve un email d'un fournisseur.
    """
    db = await get_db()

    # Normaliser le nom
    name_lower = name.lower().strip()

    # Vérifier si on connaît déjà cet expéditeur
    existing = await db.sender_mappings.find_one({
        "user_id": user_id,
        "name": name_lower
    })

    if existing:
        # Mettre à jour si l'email est différent
        if email not in existing.get("emails", []):
            await db.sender_mappings.update_one(
                {"_id": existing["_id"]},
                {
                    "$addToSet": {"emails": email},
                    "$set": {"last_seen": datetime.utcnow()},
                    "$inc": {"seen_count": 1}
                }
            )
            logger.info(f"📚 Learned new email for {name}: {email}")
    else:
        # Créer une nouvelle entrée
        await db.sender_mappings.insert_one({
            "user_id": user_id,
            "name": name_lower,
            "emails": [email],
            "context": context,
            "created_at": datetime.utcnow(),
            "last_seen": datetime.utcnow(),
            "seen_count": 1
        })
        logger.info(f"📚 Learned new sender: {name} -> {email}")


async def get_sender_emails(user_id: str, name: str) -> List[str]:
    """
    Récupère tous les emails connus pour un expéditeur donné.
    """
    db = await get_db()
    name_lower = name.lower().strip()

    # Recherche exacte
    mapping = await db.sender_mappings.find_one({
        "user_id": user_id,
        "name": name_lower
    })

    if mapping:
        return mapping.get("emails", [])

    # Recherche partielle (contient le nom)
    cursor = db.sender_mappings.find({
        "user_id": user_id,
        "name": {"$regex": name_lower, "$options": "i"}
    })

    all_emails = []
    async for doc in cursor:
        all_emails.extend(doc.get("emails", []))

    return list(set(all_emails))


async def get_all_known_senders(user_id: str) -> List[Dict]:
    """
    Récupère tous les expéditeurs connus pour un utilisateur.
    """
    db = await get_db()
    cursor = db.sender_mappings.find({"user_id": user_id}).sort("seen_count", -1)
    return await cursor.to_list(100)


# ============================================================
# KNOWLEDGE BASE - FAQ et réponses apprises
# ============================================================

async def learn_faq(user_id: str, question: str, answer: str, category: str = "general"):
    """
    Enregistre une question fréquente et sa réponse.
    """
    db = await get_db()

    await db.knowledge_base.update_one(
        {"user_id": user_id, "question": question.lower()},
        {
            "$set": {
                "answer": answer,
                "category": category,
                "updated_at": datetime.utcnow()
            },
            "$inc": {"asked_count": 1},
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )
    logger.info(f"📚 FAQ learned: {question[:50]}...")


async def find_similar_question(user_id: str, question: str) -> Optional[Dict]:
    """
    Cherche une question similaire dans la base de connaissances.
    """
    db = await get_db()

    # Mots clés de la question
    keywords = [w for w in question.lower().split() if len(w) > 3]

    if not keywords:
        return None

    # Recherche par mots clés
    regex_pattern = "|".join(keywords[:5])
    cursor = db.knowledge_base.find({
        "user_id": user_id,
        "question": {"$regex": regex_pattern, "$options": "i"}
    }).sort("asked_count", -1).limit(1)

    results = await cursor.to_list(1)
    return results[0] if results else None


# ============================================================
# USER PREFERENCES - Préférences utilisateur
# ============================================================

async def set_preference(user_id: str, key: str, value: Any):
    """
    Enregistre une préférence utilisateur.
    """
    db = await get_db()

    await db.user_preferences.update_one(
        {"user_id": user_id, "key": key},
        {
            "$set": {"value": value, "updated_at": datetime.utcnow()},
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )


async def get_preference(user_id: str, key: str, default: Any = None) -> Any:
    """
    Récupère une préférence utilisateur.
    """
    db = await get_db()
    doc = await db.user_preferences.find_one({"user_id": user_id, "key": key})
    return doc.get("value", default) if doc else default


async def get_all_preferences(user_id: str) -> Dict[str, Any]:
    """
    Récupère toutes les préférences d'un utilisateur.
    """
    db = await get_db()
    cursor = db.user_preferences.find({"user_id": user_id})
    prefs = {}
    async for doc in cursor:
        prefs[doc["key"]] = doc["value"]
    return prefs


# ============================================================
# IMPORTANT PATTERNS - Patterns d'emails importants
# ============================================================

async def learn_important_pattern(
    user_id: str,
    pattern_type: str,  # "sender", "subject", "keyword"
    pattern_value: str,
    importance: str = "high",  # "high", "medium", "low"
    notify: bool = True
):
    """
    Apprend un pattern qui indique un email important.
    Ex: emails de "banque" = toujours important
    """
    db = await get_db()

    await db.important_patterns.update_one(
        {
            "user_id": user_id,
            "pattern_type": pattern_type,
            "pattern_value": pattern_value.lower()
        },
        {
            "$set": {
                "importance": importance,
                "notify": notify,
                "updated_at": datetime.utcnow()
            },
            "$setOnInsert": {"created_at": datetime.utcnow()}
        },
        upsert=True
    )
    logger.info(f"📚 Important pattern learned: {pattern_type}={pattern_value} ({importance})")


async def get_important_patterns(user_id: str) -> List[Dict]:
    """
    Récupère tous les patterns importants.
    """
    db = await get_db()
    cursor = db.important_patterns.find({"user_id": user_id})
    return await cursor.to_list(100)


async def is_email_important(user_id: str, email_data: Dict) -> Dict[str, Any]:
    """
    Analyse un email et détermine s'il est important.
    Retourne: {"important": bool, "reason": str, "notify": bool}
    """
    db = await get_db()
    patterns = await get_important_patterns(user_id)

    subject = email_data.get("subject", "").lower()
    sender = email_data.get("from", "").lower()
    sender_email = email_data.get("from_email", "").lower()

    for pattern in patterns:
        ptype = pattern["pattern_type"]
        pvalue = pattern["pattern_value"]

        match = False
        if ptype == "sender" and (pvalue in sender or pvalue in sender_email):
            match = True
        elif ptype == "subject" and pvalue in subject:
            match = True
        elif ptype == "keyword" and (pvalue in subject or pvalue in sender):
            match = True

        if match:
            return {
                "important": True,
                "reason": f"Match: {ptype}={pvalue}",
                "importance": pattern.get("importance", "high"),
                "notify": pattern.get("notify", True)
            }

    # Patterns par défaut (toujours importants)
    default_important = [
        "facture", "paiement", "urgent", "important", "rappel",
        "banque", "impot", "urssaf", "tresor", "huissier"
    ]

    for keyword in default_important:
        if keyword in subject or keyword in sender:
            return {
                "important": True,
                "reason": f"Keyword: {keyword}",
                "importance": "high",
                "notify": True
            }

    return {"important": False, "reason": None, "notify": False}


# ============================================================
# EMAIL HISTORY - Historique pour éviter les doublons
# ============================================================

async def mark_email_processed(user_id: str, email_id: str, action: str = "seen"):
    """
    Marque un email comme traité pour éviter les notifications en double.
    """
    db = await get_db()

    await db.processed_emails.update_one(
        {"user_id": user_id, "email_id": email_id},
        {
            "$set": {"action": action, "processed_at": datetime.utcnow()},
            "$setOnInsert": {"first_seen": datetime.utcnow()}
        },
        upsert=True
    )


async def is_email_processed(user_id: str, email_id: str) -> bool:
    """
    Vérifie si un email a déjà été traité.
    """
    db = await get_db()
    doc = await db.processed_emails.find_one({"user_id": user_id, "email_id": email_id})
    return doc is not None


# ============================================================
# AUTO-LEARNING FROM INTERACTIONS
# ============================================================

async def learn_from_search(user_id: str, query: str, results: List[Dict]):
    """
    Apprend automatiquement des recherches réussies.
    Extrait les expéditeurs et les associe aux termes de recherche.
    """
    if not results:
        return

    # Extraire les noms mentionnés dans la requête
    query_lower = query.lower()

    # Liste de fournisseurs/contacts potentiels à apprendre
    for email_data in results[:5]:
        sender = email_data.get("from", "")
        sender_email = email_data.get("from_email", "")
        sender_name = email_data.get("from_name", "")

        if not sender_email:
            continue

        # Si le nom du sender correspond à un mot de la requête
        for word in query_lower.split():
            if len(word) > 3:
                if word in sender.lower() or word in sender_name.lower():
                    await learn_sender(user_id, word, sender_email, f"from search: {query[:50]}")


async def get_learning_stats(user_id: str) -> Dict[str, Any]:
    """
    Statistiques d'apprentissage pour un utilisateur.
    """
    db = await get_db()

    return {
        "senders_known": await db.sender_mappings.count_documents({"user_id": user_id}),
        "faq_entries": await db.knowledge_base.count_documents({"user_id": user_id}),
        "preferences_set": await db.user_preferences.count_documents({"user_id": user_id}),
        "important_patterns": await db.important_patterns.count_documents({"user_id": user_id}),
        "emails_processed": await db.processed_emails.count_documents({"user_id": user_id})
    }
