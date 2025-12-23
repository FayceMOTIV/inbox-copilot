"""
Table Manager
=============
Gestion des tableaux de données générés par les automatisations.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from bson import ObjectId
import csv
import io

from backend.database import get_db
from .models import Table, TableColumn, TableRow

logger = logging.getLogger(__name__)


class TableManager:
    """Gestionnaire de tableaux."""

    # Colonnes par défaut pour un tableau de factures
    INVOICE_COLUMNS = [
        TableColumn(name="date", type="date"),
        TableColumn(name="fournisseur", type="text"),
        TableColumn(name="montant", type="currency"),
        TableColumn(name="n_facture", type="text"),
        TableColumn(name="email_id", type="text"),
        TableColumn(name="payee", type="boolean"),
    ]

    @staticmethod
    async def create_table(
        user_id: str,
        name: str,
        columns: Optional[List[TableColumn]] = None,
        year: Optional[int] = None,
        automation_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """Crée un nouveau tableau."""
        db = await get_db()

        if columns is None:
            columns = TableManager.INVOICE_COLUMNS

        if year is None:
            year = datetime.now().year

        table_doc = {
            "user_id": user_id,
            "name": name,
            "description": description,
            "columns": [col.model_dump() for col in columns],
            "rows": [],
            "year": year,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "automation_id": automation_id,
            "total_amount": 0.0
        }

        result = await db.tables.insert_one(table_doc)
        table_id = str(result.inserted_id)
        logger.info(f"📊 Created table '{name}' ({table_id}) for user {user_id}")
        return table_id

    @staticmethod
    async def get_table(table_id: str) -> Optional[Dict[str, Any]]:
        """Récupère un tableau par ID."""
        db = await get_db()
        table = await db.tables.find_one({"_id": ObjectId(table_id)})
        if table:
            table["id"] = str(table.pop("_id"))
        return table

    @staticmethod
    async def get_user_tables(user_id: str) -> List[Dict[str, Any]]:
        """Récupère tous les tableaux d'un utilisateur."""
        db = await get_db()
        cursor = db.tables.find({"user_id": user_id}).sort("created_at", -1)
        tables = []
        async for table in cursor:
            table["id"] = str(table.pop("_id"))
            tables.append(table)
        return tables

    @staticmethod
    async def add_row(
        table_id: str,
        data: Dict[str, Any],
        source_email_id: Optional[str] = None,
        source_automation_id: Optional[str] = None
    ) -> str:
        """Ajoute une ligne au tableau."""
        db = await get_db()

        row_id = str(ObjectId())
        row = {
            "id": row_id,
            "data": data,
            "created_at": datetime.utcnow(),
            "source_email_id": source_email_id,
            "source_automation_id": source_automation_id
        }

        # Update total if montant is present
        amount_update = {}
        if "montant" in data and isinstance(data["montant"], (int, float)):
            amount_update = {"$inc": {"total_amount": data["montant"]}}

        await db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {
                "$push": {"rows": row},
                "$set": {"updated_at": datetime.utcnow()},
                **amount_update
            }
        )

        logger.info(f"📊 Added row to table {table_id}")
        return row_id

    @staticmethod
    async def add_rows_bulk(
        table_id: str,
        rows_data: List[Dict[str, Any]],
        source_automation_id: Optional[str] = None
    ) -> int:
        """Ajoute plusieurs lignes en une fois."""
        db = await get_db()

        rows = []
        total_amount = 0.0

        for data in rows_data:
            row = {
                "id": str(ObjectId()),
                "data": data,
                "created_at": datetime.utcnow(),
                "source_email_id": data.get("email_id"),
                "source_automation_id": source_automation_id
            }
            rows.append(row)

            if "montant" in data and isinstance(data["montant"], (int, float)):
                total_amount += data["montant"]

        if rows:
            await db.tables.update_one(
                {"_id": ObjectId(table_id)},
                {
                    "$push": {"rows": {"$each": rows}},
                    "$set": {"updated_at": datetime.utcnow()},
                    "$inc": {"total_amount": total_amount}
                }
            )

        logger.info(f"📊 Added {len(rows)} rows to table {table_id}")
        return len(rows)

    @staticmethod
    async def check_duplicate(
        table_id: str,
        email_id: str
    ) -> bool:
        """Vérifie si un email a déjà été traité."""
        db = await get_db()
        table = await db.tables.find_one(
            {
                "_id": ObjectId(table_id),
                "rows.source_email_id": email_id
            }
        )
        return table is not None

    @staticmethod
    async def update_row(
        table_id: str,
        row_id: str,
        data: Dict[str, Any]
    ) -> bool:
        """Met à jour une ligne."""
        db = await get_db()

        result = await db.tables.update_one(
            {"_id": ObjectId(table_id), "rows.id": row_id},
            {
                "$set": {
                    "rows.$.data": data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0

    @staticmethod
    async def toggle_paid(table_id: str, row_id: str) -> bool:
        """Toggle le statut payé d'une ligne."""
        db = await get_db()

        # Get current value
        table = await db.tables.find_one(
            {"_id": ObjectId(table_id), "rows.id": row_id},
            {"rows.$": 1}
        )

        if not table or not table.get("rows"):
            return False

        current = table["rows"][0].get("data", {}).get("payee", False)

        result = await db.tables.update_one(
            {"_id": ObjectId(table_id), "rows.id": row_id},
            {"$set": {"rows.$.data.payee": not current}}
        )
        return result.modified_count > 0

    @staticmethod
    async def delete_row(table_id: str, row_id: str) -> bool:
        """Supprime une ligne."""
        db = await get_db()

        result = await db.tables.update_one(
            {"_id": ObjectId(table_id)},
            {
                "$pull": {"rows": {"id": row_id}},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0

    @staticmethod
    async def delete_table(table_id: str) -> bool:
        """Supprime un tableau."""
        db = await get_db()
        result = await db.tables.delete_one({"_id": ObjectId(table_id)})
        return result.deleted_count > 0

    @staticmethod
    async def export_csv(table_id: str) -> str:
        """Exporte le tableau en CSV."""
        table = await TableManager.get_table(table_id)
        if not table:
            return ""

        output = io.StringIO()

        # Get column names
        columns = [col["name"] for col in table.get("columns", [])]

        writer = csv.DictWriter(output, fieldnames=columns)
        writer.writeheader()

        for row in table.get("rows", []):
            row_data = row.get("data", {})
            # Format currency
            if "montant" in row_data and isinstance(row_data["montant"], (int, float)):
                row_data["montant"] = f"{row_data['montant']:.2f} €"
            writer.writerow({col: row_data.get(col, "") for col in columns})

        return output.getvalue()

    @staticmethod
    async def get_table_stats(table_id: str) -> Dict[str, Any]:
        """Statistiques du tableau."""
        table = await TableManager.get_table(table_id)
        if not table:
            return {}

        rows = table.get("rows", [])
        total = table.get("total_amount", 0)

        # Count by vendor
        by_vendor = {}
        for row in rows:
            vendor = row.get("data", {}).get("fournisseur", "Autre")
            if vendor not in by_vendor:
                by_vendor[vendor] = {"count": 0, "total": 0}
            by_vendor[vendor]["count"] += 1
            by_vendor[vendor]["total"] += row.get("data", {}).get("montant", 0)

        # Count paid
        paid_count = sum(1 for r in rows if r.get("data", {}).get("payee", False))
        paid_amount = sum(
            r.get("data", {}).get("montant", 0)
            for r in rows
            if r.get("data", {}).get("payee", False)
        )

        return {
            "row_count": len(rows),
            "total_amount": total,
            "by_vendor": by_vendor,
            "paid_count": paid_count,
            "paid_amount": paid_amount,
            "unpaid_count": len(rows) - paid_count,
            "unpaid_amount": total - paid_amount
        }
