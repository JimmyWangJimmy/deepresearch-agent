from __future__ import annotations

import json
from pathlib import Path

from research_operator.schemas import TaskType


def list_run_manifests(
    artifacts_dir: Path,
    task_type: TaskType | None = None,
    limit: int | None = None,
) -> list[dict]:
    manifests = sorted(artifacts_dir.glob("*/run_manifest.json"), reverse=True)
    payloads = [json.loads(manifest_path.read_text(encoding="utf-8")) for manifest_path in manifests]
    if task_type is not None:
        payloads = [payload for payload in payloads if payload.get("plan", {}).get("task_type") == task_type.value]
    if limit is not None:
        payloads = payloads[:limit]
    return payloads
