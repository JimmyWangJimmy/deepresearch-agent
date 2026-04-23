from __future__ import annotations

import shutil
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from research_operator.config import AppConfig
from research_operator.runtime.doctor import run_doctor
from research_operator.runtime.engine import execute_task
from research_operator.runtime.monitoring import (
    build_watch_sources,
    execute_watch,
    inspect_watch,
    list_due_watches,
    list_watches,
    save_watch,
)
from research_operator.runtime.provider_registry import ProviderConfigurationError, ProviderRegistry
from research_operator.runtime.release_gate import run_release_gate
from research_operator.schemas import ProviderKind, WatchSpec

app = typer.Typer(help="DeepResearch Agent CLI")
watch_app = typer.Typer(help="Create and execute recurring watch definitions.")
app.add_typer(watch_app, name="watch")
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Natural-language task for the agent."),
    provider: ProviderKind | None = typer.Option(
        None,
        "--provider",
        help="Optional query-capable provider used when no --file or --url inputs are attached.",
    ),
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
    try:
        result = execute_task(
            task,
            artifacts_dir,
            urls=url,
            files=file,
            query_provider=provider,
        )
    except ProviderConfigurationError as exc:
        raise typer.BadParameter(str(exc)) from exc

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
    summary.add_row("Summary", str(result.artifacts.summary_path))
    summary.add_row("Quality", str(result.artifacts.quality_path))
    summary.add_row("Report", str(result.artifacts.report_path))
    summary.add_row("HTML", str(result.artifacts.html_report_path))
    summary.add_row("PDF", str(result.artifacts.pdf_report_path))
    summary.add_row("Workbook", str(result.artifacts.workbook_path))
    summary.add_row("Bundle", str(result.artifacts.bundle_path))
    summary.add_row("Chart", str(result.artifacts.chart_path))
    summary.add_row("Timeline", str(result.artifacts.timeline_chart_path))
    summary.add_row("Entities CSV", str(result.artifacts.entities_csv_path))
    summary.add_row("Events CSV", str(result.artifacts.events_csv_path))
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
def quality(
    run_id: str = typer.Argument(..., help="Run identifier to inspect quality for."),
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory that stores run artifacts.",
    ),
) -> None:
    quality_path = artifacts_dir / run_id / "quality.json"
    if not quality_path.exists():
        raise typer.BadParameter(f"Quality artifact not found: {quality_path}")
    typer.echo(quality_path.read_text(encoding="utf-8"))


@app.command()
def export(
    run_id: str = typer.Argument(..., help="Run identifier to export."),
    format: str = typer.Option(..., "--format", help="Export format: html, markdown, manifest, findings, sources, entities, entities_csv, events, events_csv, xlsx, chart, timeline_chart, pdf, bundle."),
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
        "pdf": run_dir / "research_report.pdf",
        "bundle": run_dir / "delivery_bundle.zip",
        "markdown": run_dir / "research_report.md",
        "manifest": run_dir / "run_manifest.json",
        "summary": run_dir / "run_summary.json",
        "findings": run_dir / "findings.json",
        "quality": run_dir / "quality.json",
        "xlsx": run_dir / "research_workbook.xlsx",
        "chart": run_dir / "source_scores.svg",
        "timeline_chart": run_dir / "event_timeline.svg",
        "sources": run_dir / "source_ledger.json",
        "entities": run_dir / "entities.json",
        "entities_csv": run_dir / "entities.csv",
        "events": run_dir / "events.json",
        "events_csv": run_dir / "events.csv",
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


@app.command()
def providers(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print providers as JSON.",
    ),
) -> None:
    registry = ProviderRegistry()
    available = registry.available()
    if json_output:
        typer.echo(json.dumps(available, indent=2, ensure_ascii=False))
        return
    table = Table(title="Providers")
    table.add_column("Provider")
    for name in available:
        table.add_row(name)
    console.print(table)


@app.command()
def doctor(
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory to test for artifact writes.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print doctor checks as JSON.",
    ),
) -> None:
    checks = run_doctor(artifacts_dir)
    payload = [
        {"name": item.name, "passed": item.passed, "detail": item.detail}
        for item in checks
    ]
    if json_output:
        typer.echo(json.dumps({"ready": all(item["passed"] for item in payload), "checks": payload}, indent=2))
        return

    table = Table(title="Doctor")
    table.add_column("Check")
    table.add_column("Passed")
    table.add_column("Detail")
    for item in payload:
        table.add_row(item["name"], str(item["passed"]), item["detail"])
    console.print(table)


@app.command()
def gate(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print gate report as JSON.",
    ),
) -> None:
    report = run_release_gate(Path.cwd())
    payload = {
        "ready": report.ready,
        "checks": [
            {
                "name": item.name,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in report.checks
        ],
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        raise typer.Exit(code=0 if report.ready else 2)

    table = Table(title="Release Gate")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    for item in report.checks:
        table.add_row(item.name, "PASS" if item.passed else "BLOCK", item.detail)
    console.print(table)
    console.print("READY" if report.ready else "BLOCKED")
    raise typer.Exit(code=0 if report.ready else 2)


@watch_app.command("create")
def watch_create(
    name: str = typer.Argument(..., help="Watch name."),
    task: str = typer.Option(..., "--task", help="Task to execute when sources change."),
    interval_minutes: int = typer.Option(
        60,
        "--interval-minutes",
        min=1,
        help="Target execution interval in minutes.",
    ),
    webhook_url: str | None = typer.Option(
        None,
        "--webhook-url",
        help="Optional webhook endpoint to receive watch notifications.",
    ),
    url: list[str] = typer.Option(
        None,
        "--url",
        help="Attach one or more URLs to monitor.",
    ),
    file: list[Path] = typer.Option(
        None,
        "--file",
        help="Attach one or more local files to monitor.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
    watches_dir: Path = typer.Option(
        AppConfig().watches_dir,
        "--watches-dir",
        help="Directory where watch definitions are stored.",
    ),
) -> None:
    sources = build_watch_sources(urls=url, files=file)
    if not sources:
        raise typer.BadParameter("At least one --url or --file is required.")

    spec = WatchSpec(
        name=name,
        task=task,
        sources=sources,
        interval_minutes=interval_minutes,
        webhook_url=webhook_url,
    )
    save_watch(spec, watches_dir)
    typer.echo(json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False))


@watch_app.command("run")
def watch_run(
    watch_id: str = typer.Argument(..., help="Watch identifier."),
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory where run artifacts are written.",
    ),
    watches_dir: Path = typer.Option(
        AppConfig().watches_dir,
        "--watches-dir",
        help="Directory where watch definitions are stored.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Execute even if the watch is not due yet.",
    ),
) -> None:
    execution = execute_watch(watch_id, artifacts_dir=artifacts_dir, watches_dir=watches_dir, force=force)
    typer.echo(json.dumps(execution.model_dump(mode="json"), indent=2, ensure_ascii=False))


@watch_app.command("run-all")
def watch_run_all(
    artifacts_dir: Path = typer.Option(
        AppConfig().artifacts_dir,
        "--artifacts-dir",
        help="Directory where run artifacts are written.",
    ),
    watches_dir: Path = typer.Option(
        AppConfig().watches_dir,
        "--watches-dir",
        help="Directory where watch definitions are stored.",
    ),
    due_only: bool = typer.Option(
        True,
        "--due-only/--all",
        help="Only execute watches that are due.",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Force execution regardless of due time.",
    ),
) -> None:
    specs = list_due_watches(watches_dir) if due_only and not force else list_watches(watches_dir)
    payload = [
        execute_watch(spec.watch_id, artifacts_dir=artifacts_dir, watches_dir=watches_dir, force=force).model_dump(mode="json")
        for spec in specs
    ]
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@watch_app.command("inspect")
def watch_inspect(
    watch_id: str = typer.Argument(..., help="Watch identifier."),
    watches_dir: Path = typer.Option(
        AppConfig().watches_dir,
        "--watches-dir",
        help="Directory where watch definitions are stored.",
    ),
) -> None:
    payload = inspect_watch(watch_id, watches_dir)
    typer.echo(json.dumps(payload, indent=2, ensure_ascii=False))


@watch_app.command("list")
def watch_list(
    watches_dir: Path = typer.Option(
        AppConfig().watches_dir,
        "--watches-dir",
        help="Directory where watch definitions are stored.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Print watches as JSON.",
    ),
    due_only: bool = typer.Option(
        False,
        "--due-only",
        help="Only list watches that are due.",
    ),
) -> None:
    specs = list_due_watches(watches_dir) if due_only else list_watches(watches_dir)
    if json_output:
        typer.echo(json.dumps([spec.model_dump(mode="json") for spec in specs], indent=2, ensure_ascii=False))
        return

    table = Table(title="Watches")
    table.add_column("Watch ID")
    table.add_column("Name")
    table.add_column("Sources")
    table.add_column("Interval")
    table.add_column("Next Run")
    table.add_column("Task")
    for spec in specs:
        table.add_row(
            spec.watch_id,
            spec.name,
            str(len(spec.sources)),
            str(spec.interval_minutes),
            str(spec.next_run_at or "pending"),
            spec.task,
        )
    console.print(table)


if __name__ == "__main__":
    app()
