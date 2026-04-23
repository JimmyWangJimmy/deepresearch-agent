from __future__ import annotations

from pathlib import Path

from research_operator.runtime.provider_registry import ProviderRegistry
from research_operator.schemas import CollectedSource, ProviderKind


def collect_sources(
    urls: list[str] | None = None,
    files: list[Path] | None = None,
    query: str | None = None,
    query_provider: ProviderKind | None = None,
) -> list[CollectedSource]:
    collected: list[CollectedSource] = []
    registry = ProviderRegistry()

    for url in urls or []:
        collected.append(registry.get(ProviderKind.WEB_FETCH).collect(url))

    for file_path in files or []:
        collected.append(registry.get(ProviderKind.ATTACHED).collect(str(file_path)))

    if not collected and query and query_provider is not None:
        collected.extend(registry.get(query_provider).collect_query(query))

    return collected
