from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_operator.schemas import TaskType


RUN_SORT_FIELDS = {
    "created_at_desc": ("created_at", True),
    "created_at_asc": ("created_at", False),
    "quality_desc": ("quality_score", True),
    "quality_asc": ("quality_score", False),
    "source_count_desc": ("source_count", True),
    "source_count_asc": ("source_count", False),
}


def list_run_manifests(
    artifacts_dir: Path,
    task_type: TaskType | None = None,
    task_contains: str | None = None,
    has_deliverables: bool | None = None,
    has_warnings: bool | None = None,
    min_quality_score: float | None = None,
    max_quality_score: float | None = None,
    min_average_evidence_score: float | None = None,
    max_average_evidence_score: float | None = None,
    min_source_count: int | None = None,
    max_source_count: int | None = None,
    min_event_count: int | None = None,
    max_event_count: int | None = None,
    min_entity_count: int | None = None,
    max_entity_count: int | None = None,
    sort_by: str = "created_at_desc",
    limit: int | None = None,
) -> list[dict]:
    manifests = sorted(artifacts_dir.glob("*/run_manifest.json"), reverse=True)
    payloads = [json.loads(manifest_path.read_text(encoding="utf-8")) for manifest_path in manifests]
    if task_type is not None:
        payloads = [payload for payload in payloads if payload.get("plan", {}).get("task_type") == task_type.value]
    if task_contains:
        needle = task_contains.lower()
        payloads = [payload for payload in payloads if needle in payload.get("task", "").lower()]
    if has_deliverables is not None:
        payloads = [
            payload
            for payload in payloads
            if run_has_deliverables(artifacts_dir / payload["run_id"]) is has_deliverables
        ]
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
    if min_average_evidence_score is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_average_evidence_score(artifacts_dir / payload["run_id"]) >= min_average_evidence_score
        ]
    if max_average_evidence_score is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_average_evidence_score(artifacts_dir / payload["run_id"]) <= max_average_evidence_score
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
    if min_event_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_event_count(artifacts_dir / payload["run_id"]) >= min_event_count
        ]
    if max_event_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_event_count(artifacts_dir / payload["run_id"]) <= max_event_count
        ]
    if min_entity_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_entity_count(artifacts_dir / payload["run_id"]) >= min_entity_count
        ]
    if max_entity_count is not None:
        payloads = [
            payload
            for payload in payloads
            if read_run_entity_count(artifacts_dir / payload["run_id"]) <= max_entity_count
        ]
    payloads = sort_run_payloads(payloads, artifacts_dir, sort_by)
    if limit is not None:
        payloads = payloads[:limit]
    return payloads


def summarize_run_manifests(payloads: list[dict], artifacts_dir: Path) -> dict[str, Any]:
    if not payloads:
        return {
            "run_count": 0,
            "task_types": {},
            "average_quality_score": 0.0,
            "average_evidence_score": 0.0,
            "average_source_count": 0.0,
            "average_event_count": 0.0,
            "average_entity_count": 0.0,
            "deliverable_run_count": 0,
            "warning_run_count": 0,
        }

    task_types: dict[str, int] = {}
    quality_scores: list[float] = []
    evidence_scores: list[float] = []
    source_counts: list[int] = []
    event_counts: list[int] = []
    entity_counts: list[int] = []
    deliverable_run_count = 0
    warning_run_count = 0

    for payload in payloads:
        run_dir = artifacts_dir / payload["run_id"]
        task_type = payload.get("plan", {}).get("task_type", "unknown")
        task_types[task_type] = task_types.get(task_type, 0) + 1
        quality_scores.append(read_run_quality_score(run_dir))
        evidence_scores.append(read_run_average_evidence_score(run_dir))
        source_counts.append(read_run_source_count(run_dir))
        event_counts.append(read_run_event_count(run_dir))
        entity_counts.append(read_run_entity_count(run_dir))
        if run_has_deliverables(run_dir):
            deliverable_run_count += 1
        if run_has_warnings(run_dir):
            warning_run_count += 1

    def avg(values: list[float | int]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0

    return {
        "run_count": len(payloads),
        "task_types": task_types,
        "average_quality_score": avg(quality_scores),
        "average_evidence_score": avg(evidence_scores),
        "average_source_count": avg(source_counts),
        "average_event_count": avg(event_counts),
        "average_entity_count": avg(entity_counts),
        "deliverable_run_count": deliverable_run_count,
        "warning_run_count": warning_run_count,
    }


def sort_run_payloads(payloads: list[dict], artifacts_dir: Path, sort_by: str) -> list[dict]:
    field, reverse = RUN_SORT_FIELDS.get(sort_by, RUN_SORT_FIELDS["created_at_desc"])
    return sorted(
        payloads,
        key=lambda payload: sort_key_for_payload(payload, artifacts_dir, field),
        reverse=reverse,
    )


def sort_key_for_payload(payload: dict, artifacts_dir: Path, field: str) -> Any:
    run_dir = artifacts_dir / payload["run_id"]
    if field == "quality_score":
        return read_run_quality_score(run_dir)
    if field == "source_count":
        return read_run_source_count(run_dir)
    return payload.get("created_at", "")


def run_has_warnings(run_dir: Path) -> bool:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return False
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return bool(payload.get("warnings"))


def run_has_deliverables(run_dir: Path) -> bool:
    return (run_dir / "delivery_bundle.zip").exists()


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


def read_run_average_evidence_score(run_dir: Path) -> float:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return 0.0
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return float(payload.get("average_evidence_score", 0.0))


def read_run_event_count(run_dir: Path) -> int:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return 0
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return int(payload.get("event_count", 0))


def read_run_entity_count(run_dir: Path) -> int:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return 0
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    return int(payload.get("entity_count", 0))
