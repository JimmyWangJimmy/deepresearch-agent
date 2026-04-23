from __future__ import annotations

import json
from pathlib import Path

import httpx


def write_notification(target_dir: Path, title: str, body: str) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "notification.txt"
    path.write_text(f"{title}\n\n{body}\n", encoding="utf-8")
    return path


def post_webhook(url: str, payload: dict) -> None:
    with httpx.Client(timeout=10.0) as client:
        response = client.post(url, json=payload)
        response.raise_for_status()


def build_notification_payload(title: str, body: str) -> dict[str, str]:
    return {
        "title": title,
        "body": body,
        "format": "plain_text",
    }


def write_notification_json(target_dir: Path, payload: dict) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "notification.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
