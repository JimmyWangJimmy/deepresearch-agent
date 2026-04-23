from __future__ import annotations

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
