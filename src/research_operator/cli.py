from __future__ import annotations

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
    result = execute_task(task, artifacts_dir)

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


if __name__ == "__main__":
    app()
