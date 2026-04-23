from __future__ import annotations

import re

from research_operator.schemas import CollectedSource, ExtractedEntity, ExtractedEvent


def fuse_sources(collected: list[CollectedSource]) -> list[CollectedSource]:
    fused: list[CollectedSource] = []
    seen: set[tuple[str, str]] = set()
    for item in collected:
        key = (normalize_locator(item.record.locator), normalize_text(item.content))
        if key in seen:
            continue
        seen.add(key)
        fused.append(item)
    return fused


def fuse_entities(entities: list[ExtractedEntity]) -> list[ExtractedEntity]:
    fused: list[ExtractedEntity] = []
    seen: set[tuple[str, str]] = set()
    for entity in entities:
        key = (entity.category, canonical_value(entity.entity))
        if key in seen:
            continue
        seen.add(key)
        fused.append(entity)
    return fused


def fuse_events(events: list[ExtractedEvent]) -> list[ExtractedEvent]:
    fused: list[ExtractedEvent] = []
    seen: set[tuple[str, str, str, str]] = set()
    for event in events:
        key = (
            event.event_type,
            canonical_value(event.subject),
            canonical_value(event.amount),
            canonical_value(event.event_date),
        )
        if key in seen:
            continue
        seen.add(key)
        fused.append(event)
    return fused


def normalize_locator(value: str) -> str:
    return value.strip().lower().rstrip("/")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def canonical_value(value: str) -> str:
    lowered = normalize_text(value)
    lowered = lowered.replace("人民币", "")
    lowered = lowered.replace("inc.", "inc")
    return lowered.strip()
