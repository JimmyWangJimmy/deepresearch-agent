from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(UTC)


class TaskType(str, Enum):
    RESEARCH = "research"
    MONITOR = "monitor"
    FILE_INTELLIGENCE = "file_intelligence"
    GENERAL = "general"


class StepStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class OutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"
    XLSX = "xlsx"


class ProviderKind(str, Enum):
    ATTACHED = "attached"
    WEB_FETCH = "web_fetch"
    WIKIPEDIA_SEARCH = "wikipedia_search"
    ARXIV_SEARCH = "arxiv_search"


class PlanStep(BaseModel):
    id: str
    title: str
    description: str
    status: StepStatus = StepStatus.PENDING


class RunPlan(BaseModel):
    task_type: TaskType
    objective: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[PlanStep]


class Finding(BaseModel):
    title: str
    detail: str
    confidence: str = "medium"


class ExtractedEntity(BaseModel):
    entity: str
    category: str
    source_label: str
    source_locator: str


class ExtractedEvent(BaseModel):
    event_type: str
    subject: str
    amount: str = ""
    event_date: str = ""
    source_label: str
    source_locator: str
    evidence: str = ""


class SourceRecord(BaseModel):
    label: str
    kind: str
    locator: str
    excerpt: str = ""
    content_chars: int = 0
    provider: ProviderKind = ProviderKind.ATTACHED


class CollectedSource(BaseModel):
    record: SourceRecord
    content: str


class RunArtifacts(BaseModel):
    manifest_path: Path
    report_path: Path
    findings_path: Path
    html_report_path: Path
    workbook_path: Path
    source_ledger_path: Path
    entities_path: Path
    entities_csv_path: Path
    events_path: Path
    events_csv_path: Path


class RunResult(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=utc_now)
    task: str
    plan: RunPlan
    findings: list[Finding]
    entities: list[ExtractedEntity] = Field(default_factory=list)
    events: list[ExtractedEvent] = Field(default_factory=list)
    sources: list[SourceRecord] = Field(default_factory=list)
    outputs: list[OutputFormat] = Field(
        default_factory=lambda: [OutputFormat.MARKDOWN, OutputFormat.JSON]
    )
    artifacts: RunArtifacts | None = None


class WatchSource(BaseModel):
    kind: str
    locator: str


class WatchSpec(BaseModel):
    watch_id: str = Field(default_factory=lambda: uuid4().hex[:10])
    name: str
    task: str
    created_at: datetime = Field(default_factory=utc_now)
    sources: list[WatchSource]
    interval_minutes: int = 60
    enabled: bool = True
    webhook_url: str | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class WatchSourceState(BaseModel):
    locator: str
    digest: str
    excerpt: str = ""
    content_chars: int = 0


class WatchExecution(BaseModel):
    watch_id: str
    executed_at: datetime = Field(default_factory=utc_now)
    changed_sources: list[WatchSourceState] = Field(default_factory=list)
    unchanged_sources: list[WatchSourceState] = Field(default_factory=list)
    new_run_id: str | None = None
    skipped_reason: str | None = None
