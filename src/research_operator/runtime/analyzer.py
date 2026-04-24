from __future__ import annotations

import re

from research_operator.schemas import CollectedSource, ExtractedEntity, ExtractedEvent, Finding, RunPlan, TaskType


def generate_findings(
    task: str,
    plan: RunPlan,
    collected: list[CollectedSource],
    entities: list[ExtractedEntity],
    events: list[ExtractedEvent],
) -> list[Finding]:
    base = [
        Finding(
            title="Agent-native execution model",
            detail=(
                "The product should treat the request as a run with explicit planning, "
                "execution state, and exportable artifacts instead of a chat-only interaction."
            ),
            confidence="high",
        ),
        Finding(
            title="Artifact-first delivery contract",
            detail=(
                "Every run should emit a manifest, report, structured findings, and a source ledger "
                "so results can be audited and reused by teams."
            ),
            confidence="high",
        ),
    ]

    if plan.task_type == TaskType.RESEARCH:
        base.append(
            Finding(
                title="Research workflow fit",
                detail=(
                    "This request maps to a research task, so the runtime should prioritize provider routing, "
                    "source collection, extraction, and synthesis."
                ),
                confidence="high",
            )
        )
    elif plan.task_type == TaskType.MONITOR:
        base.append(
            Finding(
                title="Monitoring workflow fit",
                detail=(
                    "This request maps to monitoring. The next product increment should add recurring runs, "
                    "change detection, and digest generation."
                ),
                confidence="high",
            )
        )
    elif plan.task_type == TaskType.FILE_INTELLIGENCE:
        base.append(
            Finding(
                title="File intelligence workflow fit",
                detail=(
                    "This request maps to file intelligence. The runtime should prioritize file parsers, "
                    "table extraction, and evidence citation from uploaded material."
                ),
                confidence="high",
            )
        )
    else:
        base.append(
            Finding(
                title="General workflow fit",
                detail=(
                    "This request does not yet map to a specialized flow. The runtime should fall back to "
                    "generic planning and then route into collection, processing, and delivery."
                ),
                confidence="medium",
            )
        )

    base.extend(generate_task_aligned_findings(task, collected))

    base.append(
        Finding(
            title="Task captured",
            detail=f"The current run objective is: {task}",
            confidence="high",
        )
    )
    if collected:
        base.append(
            Finding(
                title="Evidence intake",
                detail=(
                    f"The run ingested {len(collected)} source(s) spanning "
                    f"{sum(item.record.content_chars for item in collected)} characters of raw content."
                ),
                confidence="high",
            )
            )
        if entities:
            base.append(
                Finding(
                    title="Structured entities extracted",
                    detail=(
                        f"The run extracted {len(entities)} entity records "
                        f"across organizations, dates, and amounts."
                    ),
                    confidence="high",
                )
            )
        if events:
            base.append(
                Finding(
                    title="Structured events extracted",
                    detail=(
                        f"The run extracted {len(events)} event candidates that can be exported "
                        "to CSV for downstream analysis."
                    ),
                    confidence="high",
                )
            )
        if len(collected) > 1:
            base.append(
                Finding(
                    title="Multi-source fusion applied",
                    detail=(
                        "The runtime deduplicated collected sources and collapsed overlapping "
                        "entity/event records before artifact generation."
                    ),
                    confidence="medium",
                )
            )
        first = collected[0].record
        if first.excerpt:
            base.append(
                Finding(
                    title="First-source preview",
                    detail=f"{first.label}: {first.excerpt}",
                    confidence="medium",
                )
            )
    else:
        base.append(
            Finding(
                title="No evidence attached",
                detail=(
                    "This run did not include explicit files or URLs. It still produced artifacts, "
                    "but live research providers need to be connected for evidence-backed output."
                ),
                confidence="medium",
            )
        )
    return base


def generate_task_aligned_findings(task: str, collected: list[CollectedSource]) -> list[Finding]:
    sections = collect_markdown_sections(collected)
    if not sections:
        return []

    task_lower = task.lower()
    findings: list[Finding] = []

    if "产品定位" in task or "position" in task_lower or "定位" in task:
        section = find_section(sections, ("product position", "产品定位", "position"))
        if section:
            findings.append(
                Finding(
                    title="产品定位",
                    detail=summarize_section(section),
                    confidence="high",
                )
            )

    if "交付" in task or "deliver" in task_lower or "artifact" in task_lower or "能力" in task:
        section = find_section(sections, ("current scope", "delivery standard", "artifact", "交付"))
        if section:
            findings.append(
                Finding(
                    title="交付能力",
                    detail=summarize_section(section),
                    confidence="high",
                )
            )

    if "验收" in task or "commercial" in task_lower or "acceptance" in task_lower or "市场" in task:
        section = find_section(sections, ("delivery standard", "current commands", "api service", "quick start", "gate"))
        if section:
            findings.append(
                Finding(
                    title="商业化验收点",
                    detail=summarize_section(section),
                    confidence="high",
                )
            )

    return dedupe_findings(findings)


def collect_markdown_sections(collected: list[CollectedSource]) -> list[tuple[str, str, str]]:
    sections: list[tuple[str, str, str]] = []
    for source in collected:
        current_title = ""
        current_lines: list[str] = []
        for line in source.content.splitlines():
            heading = re.match(r"^#{1,3}\s+(.+?)\s*$", line)
            if heading:
                if current_title and current_lines:
                    sections.append((current_title, "\n".join(current_lines), source.record.label))
                current_title = heading.group(1).strip()
                current_lines = []
                continue
            if current_title:
                current_lines.append(line)
        if current_title and current_lines:
            sections.append((current_title, "\n".join(current_lines), source.record.label))
    return sections


def find_section(sections: list[tuple[str, str, str]], keywords: tuple[str, ...]) -> tuple[str, str, str] | None:
    for keyword in keywords:
        for section in sections:
            title = section[0].lower()
            if contains_keyword(title, keyword):
                return section
    for keyword in keywords:
        for section in sections:
            body = section[1].lower()
            if contains_keyword(body, keyword):
                return section
    return None


def contains_keyword(text: str, keyword: str) -> bool:
    normalized_keyword = keyword.lower()
    if re.fullmatch(r"[a-z0-9_ -]+", normalized_keyword):
        return re.search(rf"(?<![a-z0-9]){re.escape(normalized_keyword)}(?![a-z0-9])", text) is not None
    return normalized_keyword in text


def summarize_section(section: tuple[str, str, str]) -> str:
    title, body, source_label = section
    points = extract_section_points(body)
    evidence = "; ".join(points[:4]) if points else compact_text(body)
    return f"{source_label} / {title}: {evidence}"


def extract_section_points(body: str) -> list[str]:
    points: list[str] = []
    for line in body.splitlines():
        value = line.strip()
        if not value:
            continue
        if value.startswith("```"):
            break
        value = value.lstrip("-0123456789. )`").strip()
        if len(value) < 3:
            continue
        points.append(compact_text(value))
    return points


def compact_text(text: str, limit: int = 280) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def dedupe_findings(findings: list[Finding]) -> list[Finding]:
    seen: set[str] = set()
    unique: list[Finding] = []
    for finding in findings:
        if finding.title in seen:
            continue
        seen.add(finding.title)
        unique.append(finding)
    return unique


def score_sources(
    collected: list[CollectedSource],
    entities: list[ExtractedEntity],
    events: list[ExtractedEvent],
) -> list[CollectedSource]:
    entity_count_by_locator: dict[str, int] = {}
    for item in entities:
        entity_count_by_locator[item.source_locator] = entity_count_by_locator.get(item.source_locator, 0) + 1

    event_count_by_locator: dict[str, int] = {}
    for item in events:
        event_count_by_locator[item.source_locator] = event_count_by_locator.get(item.source_locator, 0) + 1

    for source in collected:
        score = 0.0
        score += min(source.record.content_chars / 400.0, 1.0)
        score += entity_count_by_locator.get(source.record.locator, 0) * 0.2
        score += event_count_by_locator.get(source.record.locator, 0) * 0.4
        if source.record.provider.value in {"wikipedia_search", "arxiv_search"}:
            score += 0.2
        source.record.evidence_score = round(score, 2)

    return sorted(collected, key=lambda item: item.record.evidence_score, reverse=True)
