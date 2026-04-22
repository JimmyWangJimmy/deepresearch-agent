from __future__ import annotations

import re

from research_operator.schemas import CollectedSource, ExtractedEntity, ExtractedEvent


ORG_SUFFIXES = (
    "公司",
    "集团",
    "资本",
    "基金",
    "银行",
    "研究院",
    "科技",
    "智能",
    "机器人",
    "实验室",
    "Inc",
    "Corp",
    "Ltd",
    "LLC",
)

EVENT_KEYWORDS = (
    ("financing", ("融资", "投资", "领投", "跟投", "募资")),
    ("partnership", ("合作", "签约", "联合", "共建")),
    ("launch", ("发布", "推出", "上线")),
    ("policy", ("政策", "监管", "办法", "通知")),
)


def extract_entities(collected: list[CollectedSource]) -> list[ExtractedEntity]:
    entities: list[ExtractedEntity] = []
    seen: set[tuple[str, str, str]] = set()

    for source in collected:
        text = source.content
        for match in find_organizations(text):
            key = (match, source.record.label, source.record.locator)
            if key in seen:
                continue
            seen.add(key)
            entities.append(
                ExtractedEntity(
                    entity=match,
                    category="organization",
                    source_label=source.record.label,
                    source_locator=source.record.locator,
                )
            )

        for date in find_dates(text):
            key = (date, source.record.label, "date")
            if key in seen:
                continue
            seen.add(key)
            entities.append(
                ExtractedEntity(
                    entity=date,
                    category="date",
                    source_label=source.record.label,
                    source_locator=source.record.locator,
                )
            )

        for amount in find_amounts(text):
            key = (amount, source.record.label, "amount")
            if key in seen:
                continue
            seen.add(key)
            entities.append(
                ExtractedEntity(
                    entity=amount,
                    category="amount",
                    source_label=source.record.label,
                    source_locator=source.record.locator,
                )
            )

    return entities


def extract_events(collected: list[CollectedSource]) -> list[ExtractedEvent]:
    events: list[ExtractedEvent] = []
    seen: set[tuple[str, str, str, str]] = set()

    for source in collected:
        sentences = split_sentences(source.content)
        for sentence in sentences:
            event_type = detect_event_type(sentence)
            if not event_type:
                continue
            organizations = find_organizations(sentence)
            amounts = find_amounts(sentence)
            dates = find_dates(sentence)
            subject = organizations[0] if organizations else source.record.label
            amount = amounts[0] if amounts else ""
            event_date = dates[0] if dates else ""
            key = (event_type, subject, amount, source.record.locator)
            if key in seen:
                continue
            seen.add(key)
            events.append(
                ExtractedEvent(
                    event_type=event_type,
                    subject=subject,
                    amount=amount,
                    event_date=event_date,
                    source_label=source.record.label,
                    source_locator=source.record.locator,
                    evidence=sentence[:280],
                )
            )

    return events


def find_organizations(text: str) -> list[str]:
    pattern = r"([A-Z][A-Za-z0-9&.\- ]{1,40}(?:Inc|Corp|Ltd|LLC)|[\u4e00-\u9fffA-Za-z0-9]{2,30}(?:公司|集团|资本|基金|银行|研究院|科技|智能|机器人|实验室))"
    raw = re.findall(pattern, text)
    return dedupe_clean(raw)


def find_amounts(text: str) -> list[str]:
    pattern = r"((?:\d+(?:\.\d+)?)\s*(?:亿美元|亿元|万元|万美金|万美元|million|billion|M|B|亿元人民币|人民币))"
    return dedupe_clean(re.findall(pattern, text, flags=re.IGNORECASE))


def find_dates(text: str) -> list[str]:
    patterns = [
        r"(\d{4}-\d{2}-\d{2})",
        r"(\d{4}/\d{2}/\d{2})",
        r"(\d{4}年\d{1,2}月\d{1,2}日)",
        r"([A-Z][a-z]+ \d{1,2}, \d{4})",
    ]
    found: list[str] = []
    for pattern in patterns:
        found.extend(re.findall(pattern, text))
    return dedupe_clean(found)


def detect_event_type(text: str) -> str | None:
    for event_type, keywords in EVENT_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return event_type
    return None


def split_sentences(text: str) -> list[str]:
    candidates = re.split(r"(?<=[。！？.!?])\s+|\n+", text)
    return [item.strip() for item in candidates if item.strip()]


def dedupe_clean(items: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        value = re.sub(r"\s+", " ", item).strip(" ,;:()[]{}")
        if len(value) < 2:
            continue
        if value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned
