from __future__ import annotations

import json
from pathlib import Path

from research_operator.schemas import RunArtifacts, RunResult


def ensure_run_dir(base_dir: Path, run_id: str) -> Path:
    run_dir = base_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_artifacts(result: RunResult, base_dir: Path) -> RunResult:
    run_dir = ensure_run_dir(base_dir, result.run_id)
    manifest_path = run_dir / "run_manifest.json"
    report_path = run_dir / "research_report.md"
    findings_path = run_dir / "findings.json"

    manifest_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    findings_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in result.findings], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    result.artifacts = RunArtifacts(
        manifest_path=manifest_path,
        report_path=report_path,
        findings_path=findings_path,
    )
    return result


def render_markdown_report(result: RunResult) -> str:
    lines = [
        f"# Run {result.run_id}",
        "",
        "## Objective",
        "",
        result.task,
        "",
        "## Plan",
        "",
    ]
    for step in result.plan.steps:
        lines.append(f"- `{step.id}` {step.title}: {step.description}")

    lines.extend(["", "## Findings", ""])
    for finding in result.findings:
        lines.append(f"- **{finding.title}** ({finding.confidence}): {finding.detail}")

    lines.extend(["", "## Sources", ""])
    if result.sources:
        for source in result.sources:
            lines.append(f"- `{source.kind}` {source.label}: {source.locator}")
    else:
        lines.append("- No live sources were collected in scaffold mode.")

    return "\n".join(lines) + "\n"

