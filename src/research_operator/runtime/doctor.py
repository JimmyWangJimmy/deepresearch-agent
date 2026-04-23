from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from research_operator.runtime.provider_registry import ProviderRegistry


@dataclass
class DoctorCheck:
    name: str
    passed: bool
    detail: str


def run_doctor(artifacts_dir: Path) -> list[DoctorCheck]:
    return [
        check_artifacts_dir(artifacts_dir),
        check_provider_registry(),
        check_openai_configuration(),
    ]


def check_artifacts_dir(artifacts_dir: Path) -> DoctorCheck:
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        probe = artifacts_dir / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return DoctorCheck("artifacts_dir", False, f"not writable: {exc}")
    return DoctorCheck("artifacts_dir", True, f"writable: {artifacts_dir}")


def check_provider_registry() -> DoctorCheck:
    providers = ProviderRegistry().available()
    required = {"attached", "web_fetch", "wikipedia_search", "arxiv_search", "openai_web_research"}
    missing = sorted(required - set(providers))
    if missing:
        return DoctorCheck("providers", False, f"missing providers: {', '.join(missing)}")
    return DoctorCheck("providers", True, f"registered providers: {', '.join(providers)}")


def check_openai_configuration() -> DoctorCheck:
    if os.environ.get("OPENAI_API_KEY"):
        model = os.environ.get("OPENAI_RESEARCH_MODEL", "gpt-5.2")
        return DoctorCheck("openai_web_research", True, f"configured with model: {model}")
    return DoctorCheck(
        "openai_web_research",
        False,
        "OPENAI_API_KEY not set; openai_web_research provider will be unavailable",
    )
