from __future__ import annotations

import csv
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
    html_report_path = run_dir / "research_report.html"
    source_ledger_path = run_dir / "source_ledger.json"
    entities_path = run_dir / "entities.json"
    entities_csv_path = run_dir / "entities.csv"
    events_path = run_dir / "events.json"
    events_csv_path = run_dir / "events.csv"

    result.artifacts = RunArtifacts(
        manifest_path=manifest_path,
        report_path=report_path,
        findings_path=findings_path,
        html_report_path=html_report_path,
        source_ledger_path=source_ledger_path,
        entities_path=entities_path,
        entities_csv_path=entities_csv_path,
        events_path=events_path,
        events_csv_path=events_csv_path,
    )

    manifest_path.write_text(
        json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(render_markdown_report(result), encoding="utf-8")
    html_report_path.write_text(render_html_report(result), encoding="utf-8")
    findings_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in result.findings], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    source_ledger_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in result.sources], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    entities_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in result.entities], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    events_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in result.events], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(
        entities_csv_path,
        ["entity", "category", "source_label", "source_locator"],
        [
            {
                "entity": item.entity,
                "category": item.category,
                "source_label": item.source_label,
                "source_locator": item.source_locator,
            }
            for item in result.entities
        ],
    )
    write_csv(
        events_csv_path,
        ["event_type", "subject", "amount", "event_date", "source_label", "source_locator", "evidence"],
        [
            {
                "event_type": item.event_type,
                "subject": item.subject,
                "amount": item.amount,
                "event_date": item.event_date,
                "source_label": item.source_label,
                "source_locator": item.source_locator,
                "evidence": item.evidence,
            }
            for item in result.events
        ],
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
        lines.append("- No explicit sources attached to this run.")

    lines.extend(["", "## Structured Outputs", ""])
    lines.append(f"- Entities: `{result.artifacts.entities_path}`")
    lines.append(f"- Entities CSV: `{result.artifacts.entities_csv_path}`")
    lines.append(f"- Events: `{result.artifacts.events_path}`")
    lines.append(f"- Events CSV: `{result.artifacts.events_csv_path}`")

    return "\n".join(lines) + "\n"


def render_html_report(result: RunResult) -> str:
    findings = "".join(
        f"<li><strong>{escape_html(item.title)}</strong> "
        f"<span>({escape_html(item.confidence)})</span>: {escape_html(item.detail)}</li>"
        for item in result.findings
    )
    sources = "".join(
        (
            "<li>"
            f"<strong>{escape_html(source.label)}</strong> "
            f"<span>{escape_html(source.kind)}</span> "
            f"<code>{escape_html(source.locator)}</code>"
            f"<p>{escape_html(source.excerpt)}</p>"
            "</li>"
        )
        for source in result.sources
    )
    if not sources:
        sources = "<li>No explicit sources attached to this run.</li>"

    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>DeepResearch Agent Run {escape_html(result.run_id)}</title>
    <style>
      :root {{
        --bg: #f6f2e8;
        --card: #fffdf8;
        --ink: #141312;
        --muted: #665f55;
        --accent: #0f766e;
        --line: #ddd4c5;
      }}
      body {{ font-family: Georgia, 'Iowan Old Style', serif; background: var(--bg); color: var(--ink); margin: 0; }}
      main {{ max-width: 960px; margin: 0 auto; padding: 48px 24px 80px; }}
      h1, h2 {{ margin: 0 0 16px; }}
      .hero {{ padding: 28px; background: linear-gradient(135deg, #fffefb, #efe5d2); border: 1px solid var(--line); border-radius: 20px; }}
      .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 20px; margin-top: 24px; }}
      .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 20px; }}
      ul {{ padding-left: 20px; }}
      code {{ background: #f1ecdf; padding: 2px 6px; border-radius: 6px; }}
      .meta {{ color: var(--muted); }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p class="meta">DeepResearch Agent run</p>
        <h1>{escape_html(result.task)}</h1>
        <p>Run ID: <code>{escape_html(result.run_id)}</code></p>
        <p>Created at: <code>{escape_html(str(result.created_at))}</code></p>
      </section>
      <section class="grid">
        <article class="card">
          <h2>Plan</h2>
          <ul>
            {"".join(f"<li><strong>{escape_html(step.title)}</strong>: {escape_html(step.description)}</li>" for step in result.plan.steps)}
          </ul>
        </article>
        <article class="card">
          <h2>Findings</h2>
          <ul>{findings}</ul>
        </article>
      </section>
      <section class="grid">
        <article class="card">
          <h2>Entities</h2>
          <p>{len(result.entities)} extracted</p>
        </article>
        <article class="card">
          <h2>Events</h2>
          <p>{len(result.events)} extracted</p>
        </article>
      </section>
      <section class="card" style="margin-top: 24px;">
        <h2>Sources</h2>
        <ul>{sources}</ul>
      </section>
    </main>
  </body>
</html>
"""


def escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
