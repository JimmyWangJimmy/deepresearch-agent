from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

import httpx

from research_operator.schemas import CollectedSource, ProviderKind, SourceRecord
from research_operator.runtime.source_io import fetch_json, fetch_url_text, fetch_xml, make_excerpt, read_file_text


class ProviderConfigurationError(RuntimeError):
    pass


class ProviderAdapter(ABC):
    kind: ProviderKind

    @abstractmethod
    def collect(self, locator: str) -> CollectedSource:
        raise NotImplementedError

    def collect_query(self, query: str) -> list[CollectedSource]:
        raise NotImplementedError(f"{self.kind.value} does not support query collection")


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


class WikipediaSearchProvider(ProviderAdapter):
    kind = ProviderKind.WIKIPEDIA_SEARCH

    def collect(self, locator: str) -> CollectedSource:
        text = fetch_url_text(locator)
        return CollectedSource(
            record=SourceRecord(
                label=locator,
                kind="url",
                locator=locator,
                excerpt=make_excerpt(text),
                content_chars=len(text),
                provider=self.kind,
            ),
            content=text,
        )

    def collect_query(self, query: str) -> list[CollectedSource]:
        collected: list[CollectedSource] = []
        for candidate in build_query_candidates(query):
            search_payload = fetch_json(
                "https://en.wikipedia.org/w/api.php",
                {
                    "action": "opensearch",
                    "search": candidate,
                    "limit": "3",
                    "namespace": "0",
                    "format": "json",
                },
            )
            if not isinstance(search_payload, list) or len(search_payload) < 2:
                continue
            titles = rank_titles(search_payload[1][:6], candidate)
            for title in titles[:3]:
                if not isinstance(title, str) or not title.strip():
                    continue
                summary_payload = fetch_json(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}"
                )
                if not isinstance(summary_payload, dict):
                    continue
                summary = str(summary_payload.get("extract") or "").strip()
                page_url = (
                    summary_payload.get("content_urls", {})
                    .get("desktop", {})
                    .get("page", f"https://en.wikipedia.org/wiki/{quote(title)}")
                )
                if not summary:
                    continue
                collected.append(
                    CollectedSource(
                        record=SourceRecord(
                            label=title,
                            kind="search_result",
                            locator=str(page_url),
                            excerpt=make_excerpt(summary),
                            content_chars=len(summary),
                            provider=self.kind,
                        ),
                        content=summary,
                    )
                )
            if collected:
                break
        return collected


class ArxivSearchProvider(ProviderAdapter):
    kind = ProviderKind.ARXIV_SEARCH

    def collect(self, locator: str) -> CollectedSource:
        text = fetch_url_text(locator)
        return CollectedSource(
            record=SourceRecord(
                label=locator,
                kind="url",
                locator=locator,
                excerpt=make_excerpt(text),
                content_chars=len(text),
                provider=self.kind,
            ),
            content=text,
        )

    def collect_query(self, query: str) -> list[CollectedSource]:
        feed = fetch_xml(
            "https://export.arxiv.org/api/query",
            {
                "search_query": f"all:{query}",
                "start": "0",
                "max_results": "3",
            },
        )
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        collected: list[CollectedSource] = []
        for entry in feed.findall("atom:entry", ns)[:3]:
            title = (entry.findtext("atom:title", default="", namespaces=ns) or "").strip()
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or "").strip()
            locator = (entry.findtext("atom:id", default="", namespaces=ns) or "").strip()
            if not title or not summary or not locator:
                continue
            collected.append(
                CollectedSource(
                    record=SourceRecord(
                        label=title,
                        kind="search_result",
                        locator=locator,
                        excerpt=make_excerpt(summary),
                        content_chars=len(summary),
                        provider=self.kind,
                    ),
                    content=summary,
                )
            )
        return collected


class OpenAIWebResearchProvider(ProviderAdapter):
    kind = ProviderKind.OPENAI_WEB_RESEARCH

    def collect(self, locator: str) -> CollectedSource:
        return self.collect_query(locator)[0]

    def collect_query(self, query: str) -> list[CollectedSource]:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderConfigurationError("OPENAI_API_KEY is required for openai_web_research provider")
        model = os.environ.get("OPENAI_RESEARCH_MODEL", "gpt-5.2")
        payload = {
            "model": model,
            "input": (
                "Research the following request. Return a concise evidence-backed brief with "
                "specific facts, dates, entities, and source URLs where available.\n\n"
                f"Request: {query}"
            ),
            "tools": [{"type": "web_search"}],
            "tool_choice": "auto",
        }
        with httpx.Client(timeout=90.0) as client:
            response = client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        text = extract_response_text(data)
        response_id = str(data.get("id") or "openai_response")
        return [
            CollectedSource(
                record=SourceRecord(
                    label=f"OpenAI Web Research: {query[:60]}",
                    kind="research_provider",
                    locator=f"openai:responses/{response_id}",
                    excerpt=make_excerpt(text),
                    content_chars=len(text),
                    provider=self.kind,
                ),
                content=text,
            )
        ]


def extract_response_text(data: dict) -> str:
    direct = data.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct.strip()
    parts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                parts.append(content["text"])
    return "\n\n".join(part.strip() for part in parts if part.strip())


def build_query_candidates(query: str) -> list[str]:
    candidates = [query.strip()]
    lowered = query.lower()
    for token in ["overview", "analysis", "report", "research", "industry", "market"]:
        lowered = lowered.replace(token, " ")
    simplified = " ".join(lowered.split())
    if simplified and simplified not in candidates:
        candidates.append(simplified)
    if simplified:
        first_two = " ".join(simplified.split()[:2])
        if first_two and first_two not in candidates:
            candidates.append(first_two)
        first_one = simplified.split()[0]
        if first_one and first_one not in candidates:
            candidates.append(first_one)
    return candidates


def rank_titles(titles: list[object], query: str) -> list[str]:
    normalized_query = normalize_query(query)
    query_terms = set(normalized_query.split())
    ranked: list[tuple[int, str]] = []
    for title in titles:
        if not isinstance(title, str):
            continue
        cleaned = title.strip()
        if not cleaned:
            continue
        if ";" in cleaned:
            continue
        score = 0
        lower = cleaned.lower()
        if any(bad in cleaned for bad in ["(", ")"]):
            score -= 3
        if lower == normalized_query:
            score += 5
        if lower.startswith(normalized_query):
            score += 3
        title_terms = set(normalize_query(cleaned).split())
        score += len(query_terms & title_terms) * 2
        ranked.append((score, cleaned))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [title for _, title in ranked if _ >= 0]


def normalize_query(value: str) -> str:
    return " ".join(value.lower().split())


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers = {
            ProviderKind.ATTACHED: AttachedFileProvider(),
            ProviderKind.WEB_FETCH: WebFetchProvider(),
            ProviderKind.WIKIPEDIA_SEARCH: WikipediaSearchProvider(),
            ProviderKind.ARXIV_SEARCH: ArxivSearchProvider(),
            ProviderKind.OPENAI_WEB_RESEARCH: OpenAIWebResearchProvider(),
        }

    def get(self, kind: ProviderKind) -> ProviderAdapter:
        return self._providers[kind]

    def available(self) -> list[str]:
        return [kind.value for kind in self._providers]
