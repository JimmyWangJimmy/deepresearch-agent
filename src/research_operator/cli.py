from __future__ import annotations

import shutil
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from research_operator.config import AppConfig
from research_operator.runtime.engine import execute_task

app = typer.Typer(help="DeepResearch Agent CLI")
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Natural-language task for the agent."),
    url: list[str] = typer.Option(
        None,
        "--url",
        help="Attach one or more URLs as explicit sources.",
    ),
    file: list[Path] = typer.Option(
        None,
        "--file",
        help="Attach one or more local files as explicit sources.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory where run artifacts are written.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print the final run result as JSON.",
    ),
) -> None:
    result = execute_task(task, artifacts_dir, urls=url, files=file)

    if json_output:
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2, ensure_ascii=False))
        return

    console.print(Panel.fit("DeepResearch Agent\nCLI-first research execution", title="Run"))
    console.print(f"[bold]Task[/bold]: {task}")
    console.print(f"[bold]Artifacts[/bold]: {artifacts_dir}")

    summary = Table(title="Run Summary")
    summary.add_column("Field")
    summary.add_column("Value")
    summary.add_row("Run ID", result.run_id)
    summary.add_row("Task Type", result.plan.task_type.value)
    summary.add_row("Report", str(result.artifacts.report_path))
    summary.add_row("HTML", str(result.artifacts.html_report_path))
    summary.add_row("Manifest", str(result.artifacts.manifest_path))
    console.print(summary)

    console.print("[bold]Findings[/bold]")
    for finding in result.findings:
        console.print(f"- {finding.title}: {finding.detail}")


@app.command()
def inspect(
    run_id: str = typer.Argument(..., help="Run identifier to inspect."),
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory that stores run artifacts.",
    ),
) -> None:
    manifest_path = artifacts_dir / run_id / "run_manifest.json"
    if not manifest_path.exists():
        raise typer.BadParameter(f"Run manifest not found: {manifest_path}")

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@app.command()
def runs(
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory that stores run artifacts.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print runs as JSON.",
    ),
) -> None:
    manifests = sorted(artifacts_dir.glob("*/run_manifest.json"), reverse=True)
    payloads = [
        json.loads(manifest_path.read_text(encoding="utf-8"))
        for manifest_path in manifests
    ]

    if json_output:
        typer.echo(json.dumps(payloads, indent=2, ensure_ascii=False))
        return

    table = Table(title="Runs")
    table.add_column("Run ID")
    table.add_column("Task Type")
    table.add_column("Task")
    table.add_column("Created At")

    for payload in payloads:
        table.add_row(
            payload["run_id"],
            payload["plan"]["task_type"],
            payload["task"],
            payload["created_at"],
        )

    console.print(table)


@app.command()
def export(
    run_id: str = typer.Argument(..., help="Run identifier to export."),
    format: str = typer.Option(..., "--format", help="Export format: html, markdown, manifest, findings, sources."),
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory that stores run artifacts.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        help="Optional explicit output path. Defaults to the artifact path for the format.",
    ),
) -> None:
    run_dir = artifacts_dir / run_id
    mapping = {
        "html": run_dir / "research_report.html",
        "markdown": run_dir / "research_report.md",
        "manifest": run_dir / "run_manifest.json",
        "findings": run_dir / "findings.json",
        "sources": run_dir / "source_ledger.json",
    }
    if format not in mapping:
        raise typer.BadParameter(f"Unsupported export format: {format}")
    source_path = mapping[format]
    if not source_path.exists():
        raise typer.BadParameter(f"Artifact not found: {source_path}")

    if output is None:
        typer.echo(str(source_path))
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output)
    typer.echo(str(output))


if __name__ == "__main__":
    app()
