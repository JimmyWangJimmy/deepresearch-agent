from __future__ import annotations

from research_operator.schemas import PlanStep, RunPlan, StepStatus, TaskType


def infer_task_type(task: str) -> TaskType:
    lowered = task.lower()
    if any(token in lowered for token in ["monitor", "监控", "track", "watch"]):
        return TaskType.MONITOR
    if any(
        token in lowered
        for token in ["pdf", "文件", "doc", "文档", "xlsx", "csv", "report"]
    ):
        return TaskType.FILE_INTELLIGENCE
    if any(
        token in lowered
        for token in ["research", "研究", "融资", "竞品", "行业", "analysis", "分析"]
    ):
        return TaskType.RESEARCH
    return TaskType.GENERAL


def build_plan(task: str) -> RunPlan:
    task_type = infer_task_type(task)
    steps = [
        PlanStep(
            id="scope",
            title="Scope task",
            description="Interpret the natural-language request and derive the execution scope.",
            status=StepStatus.COMPLETED,
        ),
        PlanStep(
            id="collect",
            title="Collect evidence",
            description="Select providers and gather raw sources for the run.",
            status=StepStatus.COMPLETED,
        ),
        PlanStep(
            id="process",
            title="Process and normalize",
            description="Clean, deduplicate, and organize source material into structured findings.",
            status=StepStatus.COMPLETED,
        ),
        PlanStep(
            id="deliver",
            title="Deliver artifacts",
            description="Render report and machine-readable outputs for downstream workflows.",
            status=StepStatus.COMPLETED,
        ),
    ]

    assumptions = [
        "This scaffold uses deterministic planning instead of live provider calls.",
        "Future versions will route across external deep research providers and internal tools.",
        "Artifacts are the primary delivery surface; chat text is secondary.",
    ]

    return RunPlan(
        task_type=task_type,
        objective=task,
        assumptions=assumptions,
        steps=steps,
    )

