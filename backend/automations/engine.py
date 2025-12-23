"""
Automation Engine
=================
Exécution des automatisations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from bson import ObjectId

from backend.database import get_db
from backend.email_service import EmailService
from .models import (
    Automation, AutomationConfig, AutomationRun,
    ActionType, TriggerType
)
from .tables import TableManager
from .parser import format_automation_summary

logger = logging.getLogger(__name__)


class AutomationEngine:
    """Moteur d'exécution des automatisations."""

    def __init__(self):
        self.email_service = EmailService()

    async def create_automation(
        self,
        user_id: str,
        account_id: str,
        config: AutomationConfig
    ) -> Dict[str, Any]:
        """
        Crée une nouvelle automatisation à partir d'une config parsée.
        """
        db = await get_db()

        # Create associated table
        table_name = f"Factures {datetime.now().year}"
        if config.vendors:
            if len(config.vendors) <= 3:
                table_name = f"Factures {', '.join(v.title() for v in config.vendors)} {datetime.now().year}"

        table_id = await TableManager.create_table(
            user_id=user_id,
            name=table_name,
            year=datetime.now().year,
            description=f"Généré par: {config.name}"
        )

        # Create automation document
        automation_doc = {
            "user_id": user_id,
            "account_id": account_id,
            "name": config.name,
            "description": config.description,
            "trigger": config.trigger.model_dump(),
            "actions": [a.model_dump() for a in config.actions],
            "vendors": config.vendors,
            "table_id": table_id,
            "status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_run": None,
            "next_run": None,
            "run_count": 0,
            "last_error": None
        }

        result = await db.automations.insert_one(automation_doc)
        automation_id = str(result.inserted_id)

        # Schedule it
        from .scheduler import automation_scheduler
        automation_doc["_id"] = result.inserted_id
        await automation_scheduler.schedule_automation(automation_doc)

        logger.info(f"🤖 Created automation '{config.name}' ({automation_id})")

        return {
            "id": automation_id,
            "name": config.name,
            "table_id": table_id,
            "table_name": table_name,
            "trigger": config.trigger.model_dump(),
            "vendors": config.vendors,
            "summary": format_automation_summary(config)
        }

    async def get_automation(self, automation_id: str) -> Optional[Dict[str, Any]]:
        """Récupère une automatisation."""
        db = await get_db()
        automation = await db.automations.find_one({"_id": ObjectId(automation_id)})
        if automation:
            automation["id"] = str(automation.pop("_id"))
        return automation

    async def get_user_automations(self, user_id: str) -> List[Dict[str, Any]]:
        """Récupère toutes les automatisations d'un utilisateur."""
        db = await get_db()
        cursor = db.automations.find({"user_id": user_id}).sort("created_at", -1)
        automations = []
        async for auto in cursor:
            auto["id"] = str(auto.pop("_id"))
            automations.append(auto)
        return automations

    async def run_automation(self, automation_id: str) -> Dict[str, Any]:
        """
        Exécute une automatisation.
        """
        db = await get_db()

        # Get automation
        automation = await db.automations.find_one({"_id": ObjectId(automation_id)})
        if not automation:
            return {"success": False, "error": "Automation not found"}

        # Create run record
        run_doc = {
            "automation_id": automation_id,
            "user_id": automation["user_id"],
            "started_at": datetime.utcnow(),
            "status": "running",
            "results": {},
            "emails_processed": 0,
            "rows_added": 0
        }
        run_result = await db.automation_runs.insert_one(run_doc)
        run_id = str(run_result.inserted_id)

        try:
            # Execute actions
            result = await self._execute_actions(automation)

            # Update run record
            await db.automation_runs.update_one(
                {"_id": run_result.inserted_id},
                {
                    "$set": {
                        "completed_at": datetime.utcnow(),
                        "status": "success",
                        "results": result,
                        "emails_processed": result.get("emails_processed", 0),
                        "rows_added": result.get("rows_added", 0)
                    }
                }
            )

            # Update automation
            await db.automations.update_one(
                {"_id": ObjectId(automation_id)},
                {
                    "$set": {
                        "last_run": datetime.utcnow(),
                        "last_error": None
                    },
                    "$inc": {"run_count": 1}
                }
            )

            logger.info(f"🤖 Automation {automation_id} completed: {result.get('rows_added', 0)} rows added")

            return {
                "success": True,
                "run_id": run_id,
                **result
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"🤖 Automation {automation_id} failed: {error_msg}")

            # Update run record
            await db.automation_runs.update_one(
                {"_id": run_result.inserted_id},
                {
                    "$set": {
                        "completed_at": datetime.utcnow(),
                        "status": "error",
                        "error": error_msg
                    }
                }
            )

            # Update automation
            await db.automations.update_one(
                {"_id": ObjectId(automation_id)},
                {
                    "$set": {
                        "last_run": datetime.utcnow(),
                        "last_error": error_msg
                    }
                }
            )

            return {"success": False, "error": error_msg}

    async def _execute_actions(self, automation: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the actions of an automation."""
        account_id = automation["account_id"]
        vendors = automation.get("vendors", [])
        table_id = automation.get("table_id")
        actions = automation.get("actions", [])

        # Determine date range (last week by default)
        now = datetime.utcnow()
        start_date = now - timedelta(days=7)

        # Build search query
        date_filter = f"after:{start_date.strftime('%Y/%m/%d')}"

        all_invoices = []
        emails_processed = 0

        # Search for each vendor
        for vendor in vendors:
            # Get vendor email from learning
            vendor_emails = await self._get_vendor_emails(automation["user_id"], vendor)

            for vendor_email in vendor_emails:
                query = f"{date_filter} from:{vendor_email} subject:facture"
                logger.info(f"🔍 Searching: {query}")

                try:
                    emails = await self.email_service.search_emails(
                        account_id=account_id,
                        query_string=query
                    )

                    for email in emails:
                        emails_processed += 1

                        # Check if already in table
                        if table_id:
                            is_duplicate = await TableManager.check_duplicate(
                                table_id, email["id"]
                            )
                            if is_duplicate:
                                continue

                        # Get attachments and extract amount
                        try:
                            full_email = await self.email_service.get_email_by_id(
                                account_id, email["id"]
                            )
                            attachments = full_email.get("attachments", [])

                            for att in attachments:
                                filename = att.get("filename", "").lower()
                                if "cgv" in filename or "condition" in filename:
                                    continue

                                if att.get("mimeType") == "application/pdf" or filename.endswith('.pdf'):
                                    invoice_data = await self.email_service.extract_invoice_data(
                                        account_id,
                                        email["id"],
                                        att.get("attachmentId")
                                    )

                                    if invoice_data.get("total"):
                                        all_invoices.append({
                                            "date": email.get("date", ""),
                                            "fournisseur": vendor.title(),
                                            "montant": invoice_data["total"]["value"],
                                            "n_facture": invoice_data.get("invoice_number", ""),
                                            "email_id": email["id"],
                                            "payee": False
                                        })
                                        break  # One invoice per email

                        except Exception as e:
                            logger.warning(f"Could not process email {email['id']}: {e}")

                except Exception as e:
                    logger.warning(f"Search failed for {vendor}: {e}")

        # Add to table
        rows_added = 0
        if table_id and all_invoices:
            rows_added = await TableManager.add_rows_bulk(
                table_id,
                all_invoices,
                source_automation_id=str(automation.get("_id", automation.get("id")))
            )

        return {
            "emails_processed": emails_processed,
            "invoices_found": len(all_invoices),
            "rows_added": rows_added,
            "invoices": all_invoices
        }

    async def _get_vendor_emails(self, user_id: str, vendor: str) -> List[str]:
        """Get known email addresses for a vendor."""
        db = await get_db()

        # Check learned senders
        sender = await db.learned_senders.find_one({
            "user_id": user_id,
            "name": {"$regex": vendor, "$options": "i"}
        })

        if sender:
            return sender.get("emails", [vendor])

        # Default mappings
        default_mappings = {
            "distram": ["facturation@distram.com"],
            "promocash": ["no-reply@promocash.com"],
            "metro": ["factures@metro.fr"],
            "khadispal": ["khadispal"],
            "orcun": ["orcun"],
        }

        return default_mappings.get(vendor.lower(), [vendor])

    async def pause_automation(self, automation_id: str) -> bool:
        """Pause an automation."""
        db = await get_db()
        from .scheduler import automation_scheduler

        await automation_scheduler.unschedule_automation(automation_id)

        result = await db.automations.update_one(
            {"_id": ObjectId(automation_id)},
            {"$set": {"status": "paused", "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def resume_automation(self, automation_id: str) -> bool:
        """Resume a paused automation."""
        db = await get_db()
        from .scheduler import automation_scheduler

        automation = await db.automations.find_one({"_id": ObjectId(automation_id)})
        if not automation:
            return False

        await automation_scheduler.schedule_automation(automation)

        result = await db.automations.update_one(
            {"_id": ObjectId(automation_id)},
            {"$set": {"status": "active", "updated_at": datetime.utcnow()}}
        )
        return result.modified_count > 0

    async def delete_automation(self, automation_id: str, delete_table: bool = False) -> bool:
        """Delete an automation."""
        db = await get_db()
        from .scheduler import automation_scheduler

        automation = await db.automations.find_one({"_id": ObjectId(automation_id)})
        if not automation:
            return False

        await automation_scheduler.unschedule_automation(automation_id)

        if delete_table and automation.get("table_id"):
            await TableManager.delete_table(automation["table_id"])

        result = await db.automations.delete_one({"_id": ObjectId(automation_id)})
        return result.deleted_count > 0

    async def get_automation_runs(
        self,
        automation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get run history for an automation."""
        db = await get_db()
        cursor = db.automation_runs.find(
            {"automation_id": automation_id}
        ).sort("started_at", -1).limit(limit)

        runs = []
        async for run in cursor:
            run["id"] = str(run.pop("_id"))
            runs.append(run)
        return runs


# Global engine instance
automation_engine = AutomationEngine()
