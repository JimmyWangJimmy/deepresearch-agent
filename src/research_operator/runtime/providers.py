from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from research_operator.schemas import SourceRecord


@dataclass
class CollectedSource:
    record: SourceRecord
    content: str


def collect_sources(urls: list[str] | None = None, files: list[Path] | None = None) -> list[CollectedSource]:
    collected: list[CollectedSource] = []

    for url in urls or []:
        text = fetch_url_text(url)
        collected.append(
            CollectedSource(
                record=SourceRecord(
                    label=urlparse(url).netloc or url,
                    kind="url",
                    locator=url,
                    excerpt=make_excerpt(text),
                    content_chars=len(text),
                ),
                content=text,
            )
        )

    for file_path in files or []:
        resolved = file_path.expanduser().resolve()
        text = read_file_text(resolved)
        collected.append(
            CollectedSource(
                record=SourceRecord(
                    label=resolved.name,
                    kind="file",
                    locator=str(resolved),
                    excerpt=make_excerpt(text),
                    content_chars=len(text),
                ),
                content=text,
            )
        )

    return collected


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
