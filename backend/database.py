from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import logging
from pathlib import Path

load_dotenv()
load_dotenv(Path(__file__).resolve().parent / ".env")

logger = logging.getLogger(__name__)

# MongoDB client
client = None
db = None

async def init_db():
    global client, db
    try:
        mongo_url = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        db_name = os.getenv("DB_NAME", "assistant_email_ia")
        client = AsyncIOMotorClient(mongo_url)
        db = client.get_database(db_name)
        
        # Test connection
        await client.admin.command('ping')
        logger.info("✅ MongoDB connecté")
        
        # Create indexes
        await db.accounts.create_index("account_id", unique=True)
        await db.accounts.create_index([("email",1),("provider",1)], unique=True)
        await db.signatures.create_index("signature_id", unique=True)
        await db.expected_files.create_index("file_id", unique=True)
        await db.settings.create_index("user_id", unique=True)
        await db.contacts.create_index([("user_id",1),("email",1)], unique=True)
        await db.aliases.create_index([("user_id",1),("key",1)], unique=True)
        await db.vendors.create_index([("user_id",1),("name",1)], unique=True)
        await db.conversations.create_index("conversation_id", unique=True)
        await db.conversations.create_index([("user_id",1),("updated_at",-1)])

        # Threads tracking
        await db.threads.create_index([("user_id",1),("thread_id",1)], unique=True)
        await db.threads.create_index([("user_id",1),("status",1),("last_activity_at",-1)])
        await db.threads.create_index([("user_id",1),("next_followup_at",1)])

        # Digests
        await db.digests.create_index([("user_id",1),("date",1)], unique=True)
        await db.digests.create_index([("user_id",1),("generated_at",-1)])

        # Notifications (if not already)
        await db.notifications.create_index([("user_id",1),("read",1),("created_at",-1)])

        return db
    except Exception as e:
        logger.error(f"❌ Erreur connexion MongoDB: {e}")
        raise

async def get_db():
    if db is None:
        await init_db()
    return db
