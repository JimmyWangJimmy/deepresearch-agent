from __future__ import annotations

import csv
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def fetch_url_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "DeepResearchAgent/0.1 (+https://github.com/JimmyWangJimmy/deepresearch-agent)"
            )
        },
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        html = response.read().decode(charset, errors="replace")
    return html_to_text(html)


def fetch_json(url: str, params: dict[str, str] | None = None) -> object:
    final_url = f"{url}?{urlencode(params)}" if params else url
    request = Request(
        final_url,
        headers={
            "User-Agent": (
                "DeepResearchAgent/0.1 (+https://github.com/JimmyWangJimmy/deepresearch-agent)"
            )
        },
    )
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(charset, errors="replace")
    return json.loads(payload)


def read_file_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md", ".html", ".htm"}:
        raw = path.read_text(encoding="utf-8", errors="replace")
        return html_to_text(raw) if suffix in {".html", ".htm"} else normalize_whitespace(raw)
    if suffix == ".csv":
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.reader(handle)
            rows = [" | ".join(cell.strip() for cell in row) for row in reader]
        return normalize_whitespace("\n".join(rows))
    raise ValueError(f"Unsupported file type: {path.suffix}")


def html_to_text(html: str) -> str:
    without_scripts = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    no_tags = re.sub(r"(?s)<[^>]+>", " ", without_scripts)
    return normalize_whitespace(unescape(no_tags))


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def make_excerpt(text: str, limit: int = 240) -> str:
    normalized = normalize_whitespace(text)
    return normalized[:limit]
