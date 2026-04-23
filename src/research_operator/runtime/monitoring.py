from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research_operator.config import AppConfig
from research_operator.runtime.engine import execute_task
from research_operator.runtime.notifications import write_notification
from research_operator.runtime.provider_registry import ProviderRegistry
from research_operator.schemas import (
    ProviderKind,
    WatchExecution,
    WatchSource,
    WatchSourceState,
    WatchSpec,
)


def ensure_watches_dir(watches_dir: Path | None = None) -> Path:
    path = watches_dir or AppConfig().watches_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_watch(spec: WatchSpec, watches_dir: Path | None = None) -> Path:
    base = ensure_watches_dir(watches_dir)
    watch_dir = base / spec.watch_id
    watch_dir.mkdir(parents=True, exist_ok=True)
    spec_path = watch_dir / "watch.json"
    spec_path.write_text(json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False), encoding="utf-8")
    return spec_path


def load_watch(watch_id: str, watches_dir: Path | None = None) -> WatchSpec:
    spec_path = ensure_watches_dir(watches_dir) / watch_id / "watch.json"
    payload = json.loads(spec_path.read_text(encoding="utf-8"))
    return WatchSpec.model_validate(payload)


def list_watches(watches_dir: Path | None = None) -> list[WatchSpec]:
    base = ensure_watches_dir(watches_dir)
    specs: list[WatchSpec] = []
    for spec_path in sorted(base.glob("*/watch.json")):
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
        specs.append(WatchSpec.model_validate(payload))
    return specs


def execute_watch(
    watch_id: str,
    artifacts_dir: Path,
    watches_dir: Path | None = None,
    force: bool = False,
) -> WatchExecution:
    spec = load_watch(watch_id, watches_dir)
    if not spec.enabled:
        return WatchExecution(watch_id=spec.watch_id, skipped_reason="watch_disabled")
    if not force and not is_watch_due(spec):
        return WatchExecution(watch_id=spec.watch_id, skipped_reason="watch_not_due")

    watch_dir = ensure_watches_dir(watches_dir) / spec.watch_id
    state_path = watch_dir / "state.json"
    prior_state = load_watch_state(state_path)

    registry = ProviderRegistry()
    changed: list[WatchSourceState] = []
    unchanged: list[WatchSourceState] = []

    urls: list[str] = []
    files: list[Path] = []

    for source in spec.sources:
        kind = ProviderKind(source.kind)
        collected = registry.get(kind).collect(source.locator)
        digest = hashlib.sha256(collected.content.encode("utf-8")).hexdigest()
        current = WatchSourceState(
            locator=source.locator,
            digest=digest,
            excerpt=collected.record.excerpt,
            content_chars=collected.record.content_chars,
        )
        if prior_state.get(source.locator) == digest:
            unchanged.append(current)
        else:
            changed.append(current)
            if kind == ProviderKind.WEB_FETCH:
                urls.append(source.locator)
            else:
                files.append(Path(source.locator))

    new_run_id: str | None = None
    if changed:
        result = execute_task(spec.task, artifacts_dir, urls=urls, files=files)
        new_run_id = result.run_id

    execution = WatchExecution(
        watch_id=spec.watch_id,
        changed_sources=changed,
        unchanged_sources=unchanged,
        new_run_id=new_run_id,
    )
    state_path.write_text(
        json.dumps({item.locator: item.digest for item in changed + unchanged}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    execution_path = watch_dir / "last_execution.json"
    execution_path.write_text(
        json.dumps(execution.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    digest_path = watch_dir / "last_digest.md"
    digest_path.write_text(render_watch_digest(spec, execution), encoding="utf-8")
    write_notification(
        watch_dir,
        title=f"Watch {spec.name} execution",
        body=render_notification_body(spec, execution),
    )
    spec.last_run_at = execution.executed_at
    spec.next_run_at = execution.executed_at + timedelta(minutes=spec.interval_minutes)
    save_watch(spec, watches_dir)
    return execution


def load_watch_state(state_path: Path) -> dict[str, str]:
    if not state_path.exists():
        return {}
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in payload.items()}


def build_watch_sources(urls: list[str] | None = None, files: list[Path] | None = None) -> list[WatchSource]:
    sources: list[WatchSource] = []
    for url in urls or []:
        sources.append(WatchSource(kind=ProviderKind.WEB_FETCH.value, locator=url))
    for file_path in files or []:
        sources.append(WatchSource(kind=ProviderKind.ATTACHED.value, locator=str(file_path.expanduser().resolve())))
    return sources


def is_watch_due(spec: WatchSpec) -> bool:
    if not spec.enabled:
        return False
    if spec.next_run_at is None:
        return True
    return spec.next_run_at <= datetime.now(UTC)


def list_due_watches(watches_dir: Path | None = None) -> list[WatchSpec]:
    return [spec for spec in list_watches(watches_dir) if is_watch_due(spec)]


def render_watch_digest(spec: WatchSpec, execution: WatchExecution) -> str:
    lines = [
        f"# Watch {spec.name}",
        "",
        f"- Watch ID: `{spec.watch_id}`",
        f"- Task: {spec.task}",
        f"- Executed at: `{execution.executed_at}`",
        f"- New run ID: `{execution.new_run_id or 'none'}`",
        f"- Skipped reason: `{execution.skipped_reason or 'none'}`",
        f"- Interval minutes: `{spec.interval_minutes}`",
        f"- Next run at: `{spec.next_run_at or 'pending'}`",
        "",
        "## Changed Sources",
        "",
    ]
    if execution.changed_sources:
        for item in execution.changed_sources:
            lines.append(
                f"- `{item.locator}` ({item.content_chars} chars): {item.excerpt or 'No excerpt available.'}"
            )
    else:
        lines.append("- No changed sources detected.")

    lines.extend(["", "## Unchanged Sources", ""])
    if execution.unchanged_sources:
        for item in execution.unchanged_sources:
            lines.append(f"- `{item.locator}`")
    else:
        lines.append("- No unchanged sources recorded.")

    return "\n".join(lines) + "\n"


def render_notification_body(spec: WatchSpec, execution: WatchExecution) -> str:
    return (
        f"watch_id={spec.watch_id}\n"
        f"task={spec.task}\n"
        f"new_run_id={execution.new_run_id or 'none'}\n"
        f"changed_sources={len(execution.changed_sources)}\n"
        f"unchanged_sources={len(execution.unchanged_sources)}\n"
        f"skipped_reason={execution.skipped_reason or 'none'}"
    )
