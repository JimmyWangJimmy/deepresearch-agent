from __future__ import annotations

from pathlib import Path

from research_operator.schemas import RunResult
from research_operator.runtime.analyzer import generate_findings
from research_operator.runtime.artifacts import write_artifacts
from research_operator.runtime.planner import build_plan


def execute_task(task: str, artifacts_dir: Path) -> RunResult:
    plan = build_plan(task)
    findings = generate_findings(task, plan)
    result = RunResult(task=task, plan=plan, findings=findings)
    return write_artifacts(result, artifacts_dir)

