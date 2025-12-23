"""
API Routes pour les Automatisations
====================================
Endpoints pour créer, gérer et exécuter des automatisations.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.automations.engine import automation_engine
from backend.automations.parser import parse_automation_request, format_automation_summary
from backend.automations.scheduler import automation_scheduler
from backend.automations.tables import TableManager

router = APIRouter(prefix="/api/automations", tags=["Automations"])
tables_router = APIRouter(prefix="/api/tables", tags=["Tables"])


# ============================================================
# AUTOMATIONS ENDPOINTS
# ============================================================

class CreateAutomationRequest(BaseModel):
    message: str  # Natural language request
    account_id: str


class AutomationAction(BaseModel):
    action: str  # "pause", "resume", "run", "delete"


@router.post("")
async def create_automation(
    request: CreateAutomationRequest,
    user_id: str = Query(default="default_user")
):
    """
    Crée une automatisation à partir d'une requête en langage naturel.

    Exemple:
    {
        "message": "Récupère chaque semaine les factures de distram et promocash",
        "account_id": "xxx"
    }
    """
    # Parse the natural language request
    config = parse_automation_request(request.message)

    if not config:
        raise HTTPException(
            status_code=400,
            detail="Impossible de comprendre la demande d'automatisation"
        )

    # Create the automation
    result = await automation_engine.create_automation(
        user_id=user_id,
        account_id=request.account_id,
        config=config
    )

    return {
        "success": True,
        "automation": result,
        "message": f"Automatisation '{result['name']}' créée avec succès"
    }


@router.get("")
async def list_automations(user_id: str = Query(default="default_user")):
    """Liste toutes les automatisations de l'utilisateur."""
    automations = await automation_engine.get_user_automations(user_id)

    # Enrich with next run info
    for auto in automations:
        next_run = automation_scheduler.get_next_run(auto["id"])
        if next_run:
            auto["next_run"] = next_run.isoformat()

    return {
        "automations": automations,
        "count": len(automations)
    }


@router.get("/{automation_id}")
async def get_automation(automation_id: str):
    """Récupère une automatisation par ID."""
    automation = await automation_engine.get_automation(automation_id)

    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    # Add next run
    next_run = automation_scheduler.get_next_run(automation_id)
    if next_run:
        automation["next_run"] = next_run.isoformat()

    return automation


@router.post("/{automation_id}/run")
async def run_automation(automation_id: str):
    """Exécute une automatisation immédiatement."""
    result = await automation_scheduler.run_now(automation_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))

    return result


@router.post("/{automation_id}/pause")
async def pause_automation(automation_id: str):
    """Met en pause une automatisation."""
    success = await automation_engine.pause_automation(automation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Automation not found")

    return {"success": True, "message": "Automatisation mise en pause"}


@router.post("/{automation_id}/resume")
async def resume_automation(automation_id: str):
    """Reprend une automatisation en pause."""
    success = await automation_engine.resume_automation(automation_id)

    if not success:
        raise HTTPException(status_code=404, detail="Automation not found")

    return {"success": True, "message": "Automatisation reprise"}


@router.delete("/{automation_id}")
async def delete_automation(
    automation_id: str,
    delete_table: bool = Query(default=False)
):
    """Supprime une automatisation."""
    success = await automation_engine.delete_automation(automation_id, delete_table)

    if not success:
        raise HTTPException(status_code=404, detail="Automation not found")

    return {"success": True, "message": "Automatisation supprimée"}


@router.get("/{automation_id}/runs")
async def get_automation_runs(
    automation_id: str,
    limit: int = Query(default=10, le=50)
):
    """Historique des exécutions."""
    runs = await automation_engine.get_automation_runs(automation_id, limit)
    return {"runs": runs, "count": len(runs)}


# ============================================================
# TABLES ENDPOINTS
# ============================================================

@tables_router.get("")
async def list_tables(user_id: str = Query(default="default_user")):
    """Liste tous les tableaux de l'utilisateur."""
    tables = await TableManager.get_user_tables(user_id)

    # Add row counts
    for table in tables:
        table["row_count"] = len(table.get("rows", []))

    return {
        "tables": tables,
        "count": len(tables)
    }


@tables_router.get("/{table_id}")
async def get_table(table_id: str):
    """Récupère un tableau avec toutes ses données."""
    table = await TableManager.get_table(table_id)

    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return table


@tables_router.get("/{table_id}/stats")
async def get_table_stats(table_id: str):
    """Statistiques d'un tableau."""
    stats = await TableManager.get_table_stats(table_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Table not found")

    return stats


@tables_router.get("/{table_id}/export")
async def export_table_csv(table_id: str):
    """Exporte un tableau en CSV."""
    from fastapi.responses import Response

    csv_content = await TableManager.export_csv(table_id)

    if not csv_content:
        raise HTTPException(status_code=404, detail="Table not found")

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=table_{table_id}.csv"
        }
    )


class AddRowRequest(BaseModel):
    date: str
    fournisseur: str
    montant: float
    n_facture: Optional[str] = ""
    payee: bool = False


@tables_router.post("/{table_id}/rows")
async def add_table_row(table_id: str, row: AddRowRequest):
    """Ajoute une ligne manuellement."""
    row_id = await TableManager.add_row(
        table_id,
        row.model_dump()
    )
    return {"success": True, "row_id": row_id}


@tables_router.post("/{table_id}/rows/{row_id}/toggle-paid")
async def toggle_row_paid(table_id: str, row_id: str):
    """Toggle le statut payé."""
    success = await TableManager.toggle_paid(table_id, row_id)

    if not success:
        raise HTTPException(status_code=404, detail="Row not found")

    return {"success": True}


@tables_router.delete("/{table_id}/rows/{row_id}")
async def delete_table_row(table_id: str, row_id: str):
    """Supprime une ligne."""
    success = await TableManager.delete_row(table_id, row_id)

    if not success:
        raise HTTPException(status_code=404, detail="Row not found")

    return {"success": True}


@tables_router.delete("/{table_id}")
async def delete_table(table_id: str):
    """Supprime un tableau."""
    success = await TableManager.delete_table(table_id)

    if not success:
        raise HTTPException(status_code=404, detail="Table not found")

    return {"success": True}
