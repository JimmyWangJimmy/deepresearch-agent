from __future__ import annotations

from pathlib import Path

from research_operator.schemas import ProviderKind, RunResult
from research_operator.runtime.analyzer import generate_findings
from research_operator.runtime.artifacts import write_artifacts
from research_operator.runtime.extraction import extract_entities, extract_events
from research_operator.runtime.fusion import fuse_entities, fuse_events, fuse_sources
from research_operator.runtime.planner import build_plan
from research_operator.runtime.providers import collect_sources


def execute_task(
    task: str,
    artifacts_dir: Path,
    urls: list[str] | None = None,
    files: list[Path] | None = None,
    query_provider: ProviderKind | None = None,
) -> RunResult:
    plan = build_plan(task)
    collected = collect_sources(
        urls=urls,
        files=files,
        query=task,
        query_provider=query_provider,
    )
    collected = fuse_sources(collected)
    entities = fuse_entities(extract_entities(collected))
    events = fuse_events(extract_events(collected))
    findings = generate_findings(task, plan, collected, entities, events)
    result = RunResult(
        task=task,
        plan=plan,
        findings=findings,
        entities=entities,
        events=events,
        sources=[item.record for item in collected],
        outputs=[output for output in result_outputs()],
    )
    return write_artifacts(result, artifacts_dir)


def result_outputs():
    from research_operator.schemas import OutputFormat

    return [OutputFormat.MARKDOWN, OutputFormat.JSON, OutputFormat.HTML, OutputFormat.XLSX]
