from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from research_operator.runtime.engine import execute_task
from research_operator.runtime.monitoring import (
    build_watch_sources,
    execute_watch,
    inspect_watch,
    inspect_watch_delivery_manifest,
    list_watches,
    save_watch,
)
from research_operator.runtime.provider_registry import ProviderConfigurationError, ProviderRegistry
from research_operator.runtime.release_gate import run_release_gate
from research_operator.runtime.verification import verify_run_dir
from research_operator.schemas import ProviderKind, WatchSpec


app = FastAPI(title="DeepResearch Agent API", version="0.1.0")


class RunRequest(BaseModel):
    task: str
    provider: ProviderKind | None = None
    urls: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    artifacts_dir: str = "artifacts"


class WatchRequest(BaseModel):
    name: str
    task: str
    urls: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    interval_minutes: int = 60
    webhook_url: str | None = None
    watches_dir: str = ".dra/watches"


class WatchRunRequest(BaseModel):
    artifacts_dir: str = "artifacts"
    watches_dir: str = ".dra/watches"
    force: bool = False


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/providers")
def providers() -> dict[str, list[str]]:
    return {"providers": ProviderRegistry().available()}


@app.get("/doctor")
def doctor(artifacts_dir: str = "artifacts") -> dict:
    from research_operator.runtime.doctor import run_doctor

    checks = run_doctor(Path(artifacts_dir))
    return {
        "ready": all(item.passed for item in checks),
        "checks": [
            {
                "name": item.name,
                "passed": item.passed,
                "detail": item.detail,
            }
            for item in checks
        ],
    }


@app.post("/runs")
def create_run(request: RunRequest) -> dict:
    try:
        result = execute_task(
            request.task,
            Path(request.artifacts_dir),
            urls=request.urls,
            files=[Path(item) for item in request.files],
            query_provider=request.provider,
        )
    except ProviderConfigurationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result.model_dump(mode="json")


@app.get("/runs")
def list_runs(artifacts_dir: str = "artifacts") -> dict[str, list[dict]]:
    base = Path(artifacts_dir)
    manifests = sorted(base.glob("*/run_manifest.json"), reverse=True)
    items = [json.loads(path.read_text(encoding="utf-8")) for path in manifests]
    return {"runs": items}


@app.get("/runs/{run_id}")
def get_run(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    manifest_path = Path(artifacts_dir) / run_id / "run_manifest.json"
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return json.loads(manifest_path.read_text(encoding="utf-8"))


@app.get("/runs/{run_id}/deliverables")
def get_run_deliverables(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    run_dir = require_run_dir(run_id, artifacts_dir)
    deliverables = {
        name: {
            "path": str(path),
            "exists": path.exists(),
            "size_bytes": path.stat().st_size if path.exists() else 0,
        }
        for name, path in artifact_mapping(run_dir).items()
    }
    return {"run_id": run_id, "deliverables": deliverables}


@app.get("/runs/{run_id}/delivery-manifest")
def get_run_delivery_manifest(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    run_dir = require_run_dir(run_id, artifacts_dir)
    mapping = artifact_mapping(run_dir)
    summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    manifest = {
        "run_id": run_id,
        "primary": {
            "bundle": str(mapping["delivery_bundle"]),
            "pdf_report": str(mapping["pdf_report"]),
            "html_report": str(mapping["html_report"]),
            "quality": str(mapping["quality"]),
            "summary": str(mapping["summary"]),
        },
        "highlights": {
            "quality_score": summary["quality_score"],
            "warnings": summary["warnings"],
            "top_sources": summary["source_highlights"],
            "recent_events": summary["recent_events"],
        },
        "all": {
            name: str(path)
            for name, path in mapping.items()
            if path.exists()
        },
    }
    return manifest


@app.get("/runs/{run_id}/quality")
def get_run_quality(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    run_dir = require_run_dir(run_id, artifacts_dir)
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        raise HTTPException(status_code=404, detail=f"Quality not found for run: {run_id}")
    return json.loads(quality_path.read_text(encoding="utf-8"))


@app.get("/runs/{run_id}/verify")
def verify_run(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    run_dir = require_run_dir(run_id, artifacts_dir)
    report = verify_run_dir(run_dir)
    return {
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


@app.get("/runs/{run_id}/deliverables/{artifact_name}")
def download_run_deliverable(run_id: str, artifact_name: str, artifacts_dir: str = "artifacts") -> FileResponse:
    run_dir = require_run_dir(run_id, artifacts_dir)
    mapping = artifact_mapping(run_dir)
    if artifact_name not in mapping:
        raise HTTPException(status_code=404, detail=f"Unknown deliverable: {artifact_name}")
    path = mapping[artifact_name]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Deliverable not found: {artifact_name}")
    return FileResponse(path, filename=path.name)


@app.post("/watches")
def create_watch(request: WatchRequest) -> dict:
    sources = build_watch_sources(
        urls=request.urls,
        files=[Path(item) for item in request.files],
    )
    if not sources:
        raise HTTPException(status_code=400, detail="At least one url or file source is required.")
    spec = WatchSpec(
        name=request.name,
        task=request.task,
        sources=sources,
        interval_minutes=request.interval_minutes,
        webhook_url=request.webhook_url,
    )
    save_watch(spec, Path(request.watches_dir))
    return spec.model_dump(mode="json")


@app.get("/watches")
def get_watches(watches_dir: str = ".dra/watches") -> dict[str, list[dict]]:
    return {"watches": [item.model_dump(mode="json") for item in list_watches(Path(watches_dir))]}


@app.get("/watches/{watch_id}")
def get_watch(watch_id: str, watches_dir: str = ".dra/watches") -> dict:
    return inspect_watch(watch_id, Path(watches_dir))


@app.get("/watches/{watch_id}/delivery-manifest")
def get_watch_delivery_manifest(watch_id: str, watches_dir: str = ".dra/watches") -> dict:
    return inspect_watch_delivery_manifest(watch_id, Path(watches_dir))


@app.post("/watches/{watch_id}/run")
def run_watch(watch_id: str, request: WatchRunRequest) -> dict:
    execution = execute_watch(
        watch_id,
        artifacts_dir=Path(request.artifacts_dir),
        watches_dir=Path(request.watches_dir),
        force=request.force,
    )
    return execution.model_dump(mode="json")


@app.get("/gate")
def gate() -> dict:
    report = run_release_gate(Path.cwd())
    return {
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


def require_run_dir(run_id: str, artifacts_dir: str) -> Path:
    run_dir = Path(artifacts_dir) / run_id
    if not (run_dir / "run_manifest.json").exists():
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run_dir


def artifact_mapping(run_dir: Path) -> dict[str, Path]:
    return {
        "manifest": run_dir / "run_manifest.json",
        "summary": run_dir / "run_summary.json",
        "quality": run_dir / "quality.json",
        "markdown_report": run_dir / "research_report.md",
        "html_report": run_dir / "research_report.html",
        "pdf_report": run_dir / "research_report.pdf",
        "workbook": run_dir / "research_workbook.xlsx",
        "delivery_bundle": run_dir / "delivery_bundle.zip",
        "source_score_chart": run_dir / "source_scores.svg",
        "event_timeline_chart": run_dir / "event_timeline.svg",
        "findings": run_dir / "findings.json",
        "source_ledger": run_dir / "source_ledger.json",
        "entities_json": run_dir / "entities.json",
        "entities_csv": run_dir / "entities.csv",
        "events_json": run_dir / "events.json",
        "events_csv": run_dir / "events.csv",
    }
