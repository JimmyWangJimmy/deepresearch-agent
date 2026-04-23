from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from research_operator.runtime.engine import execute_task
from research_operator.runtime.provider_registry import ProviderConfigurationError, ProviderRegistry
from research_operator.runtime.release_gate import run_release_gate
from research_operator.schemas import ProviderKind


app = FastAPI(title="DeepResearch Agent API", version="0.1.0")


class RunRequest(BaseModel):
    task: str
    provider: ProviderKind | None = None
    urls: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    artifacts_dir: str = "artifacts"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/providers")
def providers() -> dict[str, list[str]]:
    return {"providers": ProviderRegistry().available()}


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


@app.get("/runs/{run_id}/quality")
def get_run_quality(run_id: str, artifacts_dir: str = "artifacts") -> dict:
    run_dir = require_run_dir(run_id, artifacts_dir)
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        raise HTTPException(status_code=404, detail=f"Quality not found for run: {run_id}")
    return json.loads(quality_path.read_text(encoding="utf-8"))


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
