from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from research_operator.schemas import CollectedSource, ProviderKind, SourceRecord
from research_operator.runtime.source_io import fetch_url_text, make_excerpt, read_file_text


class ProviderAdapter(ABC):
    kind: ProviderKind

    @abstractmethod
    def collect(self, locator: str) -> CollectedSource:
        raise NotImplementedError


class AttachedFileProvider(ProviderAdapter):
    kind = ProviderKind.ATTACHED

    def collect(self, locator: str) -> CollectedSource:
        path = Path(locator).expanduser().resolve()
        text = read_file_text(path)
        return CollectedSource(
            record=SourceRecord(
                label=path.name,
                kind="file",
                locator=str(path),
                excerpt=make_excerpt(text),
                content_chars=len(text),
                provider=self.kind,
            ),
            content=text,
        )


class WebFetchProvider(ProviderAdapter):
    kind = ProviderKind.WEB_FETCH

    def collect(self, locator: str) -> CollectedSource:
        from urllib.parse import urlparse

        text = fetch_url_text(locator)
        return CollectedSource(
            record=SourceRecord(
                label=urlparse(locator).netloc or locator,
                kind="url",
                locator=locator,
                excerpt=make_excerpt(text),
                content_chars=len(text),
                provider=self.kind,
            ),
            content=text,
        )


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers = {
            ProviderKind.ATTACHED: AttachedFileProvider(),
            ProviderKind.WEB_FETCH: WebFetchProvider(),
        }

    def get(self, kind: ProviderKind) -> ProviderAdapter:
        return self._providers[kind]

    def available(self) -> list[str]:
        return [kind.value for kind in self._providers]
