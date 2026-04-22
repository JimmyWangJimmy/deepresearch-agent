from __future__ import annotations

from pathlib import Path

from research_operator.schemas import RunResult
from research_operator.runtime.analyzer import generate_findings
from research_operator.runtime.artifacts import write_artifacts
from research_operator.runtime.planner import build_plan
from research_operator.runtime.providers import collect_sources


def execute_task(
    task: str,
    artifacts_dir: Path,
    urls: list[str] | None = None,
    files: list[Path] | None = None,
) -> RunResult:
    plan = build_plan(task)
    collected = collect_sources(urls=urls, files=files)
    findings = generate_findings(task, plan, collected)
    result = RunResult(
        task=task,
        plan=plan,
        findings=findings,
        sources=[item.record for item in collected],
        outputs=[output for output in result_outputs()],
    )
    return write_artifacts(result, artifacts_dir)


def result_outputs():
    from research_operator.schemas import OutputFormat

    return [OutputFormat.MARKDOWN, OutputFormat.JSON, OutputFormat.HTML]
