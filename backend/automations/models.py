"""
Automation Models
=================
Pydantic models for automations and tables.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class TriggerType(str, Enum):
    SCHEDULE = "schedule"      # Cron-based
    REALTIME = "realtime"      # On new email
    MANUAL = "manual"          # User triggered


class ActionType(str, Enum):
    SEARCH_INVOICES = "search_invoices"
    EXTRACT_AMOUNTS = "extract_amounts"
    UPDATE_TABLE = "update_table"
    SEND_ALERT = "send_alert"
    EXPORT_CSV = "export_csv"


class AutomationTrigger(BaseModel):
    type: TriggerType
    cron: Optional[str] = None          # "0 9 * * 1" = lundi 9h
    frequency: Optional[str] = None      # "weekly", "daily", "monthly"
    day_of_week: Optional[int] = None    # 0=lundi, 6=dimanche
    hour: int = 9
    minute: int = 0


class AutomationAction(BaseModel):
    type: ActionType
    vendors: Optional[List[str]] = None
    table_id: Optional[str] = None
    alert_threshold: Optional[float] = None
    params: Optional[Dict[str, Any]] = None


class AutomationConfig(BaseModel):
    name: str
    description: Optional[str] = None
    trigger: AutomationTrigger
    actions: List[AutomationAction]
    vendors: List[str] = []


class Automation(BaseModel):
    id: Optional[str] = None
    user_id: str
    account_id: str
    name: str
    description: Optional[str] = None
    trigger: AutomationTrigger
    actions: List[AutomationAction]
    vendors: List[str] = []
    table_id: Optional[str] = None
    status: Literal["active", "paused", "error"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    last_error: Optional[str] = None


class TableColumn(BaseModel):
    name: str
    type: Literal["date", "text", "number", "currency", "boolean"] = "text"
    width: Optional[int] = None


class TableRow(BaseModel):
    id: str
    data: Dict[str, Any]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source_email_id: Optional[str] = None
    source_automation_id: Optional[str] = None


class Table(BaseModel):
    id: Optional[str] = None
    user_id: str
    name: str
    description: Optional[str] = None
    columns: List[TableColumn]
    rows: List[TableRow] = []
    year: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    automation_id: Optional[str] = None
    total_amount: float = 0.0


class AutomationRun(BaseModel):
    id: Optional[str] = None
    automation_id: str
    user_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    status: Literal["running", "success", "error"] = "running"
    results: Dict[str, Any] = {}
    emails_processed: int = 0
    rows_added: int = 0
    error: Optional[str] = None
