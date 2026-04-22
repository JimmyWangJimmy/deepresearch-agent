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


class SourceRecord(BaseModel):
    label: str
    kind: str
    locator: str


class RunArtifacts(BaseModel):
    manifest_path: Path
    report_path: Path
    findings_path: Path


class RunResult(BaseModel):
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    created_at: datetime = Field(default_factory=utc_now)
    task: str
    plan: RunPlan
    findings: list[Finding]
    sources: list[SourceRecord] = Field(default_factory=list)
    outputs: list[OutputFormat] = Field(
        default_factory=lambda: [OutputFormat.MARKDOWN, OutputFormat.JSON]
    )
    artifacts: RunArtifacts | None = None

