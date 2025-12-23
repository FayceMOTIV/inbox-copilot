"""
Automation Scheduler
====================
APScheduler-based scheduling for automations.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from bson import ObjectId

from backend.database import get_db

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """Gestionnaire de planification des automatisations."""

    def __init__(self):
        self.scheduler: Optional[AsyncIOScheduler] = None
        self.engine = None  # Will be set later to avoid circular import
        self._started = False

    def set_engine(self, engine):
        """Set the automation engine reference."""
        self.engine = engine

    async def start(self):
        """Démarre le scheduler."""
        if self._started:
            return

        self.scheduler = AsyncIOScheduler()
        self.scheduler.start()
        self._started = True

        # Load existing automations
        await self._load_automations()

        logger.info("⏰ Automation scheduler started")

    async def stop(self):
        """Arrête le scheduler."""
        if self.scheduler:
            self.scheduler.shutdown()
            self._started = False
            logger.info("⏰ Automation scheduler stopped")

    async def _load_automations(self):
        """Load all active automations from database."""
        db = await get_db()
        cursor = db.automations.find({"status": "active"})

        count = 0
        async for automation in cursor:
            await self.schedule_automation(automation)
            count += 1

        logger.info(f"⏰ Loaded {count} automations")

    async def schedule_automation(self, automation: Dict[str, Any]) -> bool:
        """Schedule an automation."""
        if not self.scheduler:
            logger.warning("Scheduler not started")
            return False

        automation_id = str(automation.get("_id", automation.get("id")))
        trigger_config = automation.get("trigger", {})
        cron_expr = trigger_config.get("cron", "0 9 * * 0")

        try:
            # Parse cron expression (minute hour day month day_of_week)
            parts = cron_expr.split()
            if len(parts) >= 5:
                trigger = CronTrigger(
                    minute=parts[0],
                    hour=parts[1],
                    day=parts[2],
                    month=parts[3],
                    day_of_week=parts[4]
                )
            else:
                # Default: every Monday at 9 AM
                trigger = CronTrigger(hour=9, day_of_week=0)

            # Remove existing job if any
            existing = self.scheduler.get_job(automation_id)
            if existing:
                self.scheduler.remove_job(automation_id)

            # Add job
            self.scheduler.add_job(
                self._run_automation,
                trigger,
                id=automation_id,
                args=[automation_id],
                name=automation.get("name", "Automation"),
                replace_existing=True
            )

            # Update next_run in database
            next_run = trigger.get_next_fire_time(None, datetime.now())
            db = await get_db()
            await db.automations.update_one(
                {"_id": ObjectId(automation_id)},
                {"$set": {"next_run": next_run}}
            )

            logger.info(f"⏰ Scheduled automation {automation_id}: next run {next_run}")
            return True

        except Exception as e:
            logger.error(f"Failed to schedule automation {automation_id}: {e}")
            return False

    async def unschedule_automation(self, automation_id: str):
        """Remove an automation from the schedule."""
        if self.scheduler:
            try:
                self.scheduler.remove_job(automation_id)
                logger.info(f"⏰ Unscheduled automation {automation_id}")
            except Exception as e:
                logger.warning(f"Could not unschedule {automation_id}: {e}")

    async def _run_automation(self, automation_id: str):
        """Execute an automation (called by scheduler)."""
        if not self.engine:
            logger.error("Automation engine not set")
            return

        logger.info(f"⏰ Running scheduled automation {automation_id}")

        try:
            await self.engine.run_automation(automation_id)
        except Exception as e:
            logger.error(f"Failed to run automation {automation_id}: {e}")

    async def run_now(self, automation_id: str) -> Dict[str, Any]:
        """Run an automation immediately."""
        if not self.engine:
            return {"success": False, "error": "Engine not set"}

        return await self.engine.run_automation(automation_id)

    def get_next_run(self, automation_id: str) -> Optional[datetime]:
        """Get next scheduled run time."""
        if not self.scheduler:
            return None

        job = self.scheduler.get_job(automation_id)
        if job:
            return job.next_run_time
        return None

    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs."""
        if not self.scheduler:
            return []

        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            })
        return jobs


# Global scheduler instance
automation_scheduler = AutomationScheduler()
