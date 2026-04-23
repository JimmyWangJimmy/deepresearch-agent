from __future__ import annotations

from pathlib import Path


def write_notification(target_dir: Path, title: str, body: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "notification.txt"
    path.write_text(f"{title}\n\n{body}\n", encoding="utf-8")
    return path
