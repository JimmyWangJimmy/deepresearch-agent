from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from research_operator.runtime.engine import execute_task
from research_operator.runtime.provider_registry import ProviderRegistry
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
    result = execute_task(
        request.task,
        Path(request.artifacts_dir),
        urls=request.urls,
        files=[Path(item) for item in request.files],
        query_provider=request.provider,
    )
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
