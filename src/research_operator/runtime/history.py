from __future__ import annotations

import json
from pathlib import Path

from research_operator.schemas import TaskType


def list_run_manifests(
    artifacts_dir: Path,
    task_type: TaskType | None = None,
    task_contains: str | None = None,
    has_warnings: bool | None = None,
    min_quality_score: float | None = None,
    max_quality_score: float | None = None,
    min_source_count: int | None = None,
    max_source_count: int | None = None,
    limit: int | None = None,
) -> list[dict]:
    manifests = sorted(artifacts_dir.glob("*/run_manifest.json"), reverse=True)
    payloads = [json.loads(manifest_path.read_text(encoding="utf-8")) for manifest_path in manifests]
    if task_type is not None:
        payloads = [payload for payload in payloads if payload.get("plan", {}).get("task_type") == task_type.value]
    if task_contains:
        needle = task_contains.lower()
        payloads = [payload for payload in payloads if needle in payload.get("task", "").lower()]
    if has_warnings is not None:
        payloads = [
            payload
            for payload in payloads
            if run_has_warnings(artifacts_dir / payload["run_id"]) is has_warnings
        ]
    if min_quality_score is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_quality_score(artifacts_dir / payload["run_id"]) >= min_quality_score
        ]
    if max_quality_score is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_quality_score(artifacts_dir / payload["run_id"]) <= max_quality_score
        ]
    if min_source_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_source_count(artifacts_dir / payload["run_id"]) >= min_source_count
        ]
    if max_source_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_source_count(artifacts_dir / payload["run_id"]) <= max_source_count
        ]
    if limit is not None:
        payloads = payloads[:limit]
    return payloads


def run_has_warnings(run_dir: Path) -> bool:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return False
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return bool(payload.get("warnings"))


def read_run_quality_score(run_dir: Path) -> float:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return 0.0
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return float(payload.get("score", 0.0))


def read_run_source_count(run_dir: Path) -> int:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return 0
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return int(payload.get("source_count", 0))
