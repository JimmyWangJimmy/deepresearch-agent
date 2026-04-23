from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from research_operator.runtime.provider_registry import ProviderRegistry


@dataclass
class GateCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class GateReport:
    ready: bool
    checks: list[GateCheck]


def run_release_gate(repo_root: Path) -> GateReport:
    checks = [
        check_tests(repo_root),
        check_provider_breadth(),
        check_cli_surface(repo_root),
        check_watch_surface(repo_root),
        check_structured_outputs(repo_root),
        check_report_quality_surface(repo_root),
        check_query_provider_diversity(),
        check_api_surface(repo_root),
        check_notification_surface(repo_root),
        check_source_fusion_surface(repo_root),
        check_demo_acceptance_surface(repo_root),
    ]
    return GateReport(ready=all(item.passed for item in checks), checks=checks)


def check_tests(repo_root: Path) -> GateCheck:
    result = subprocess.run(
        ["uv", "run", "pytest", "-q"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    passed = result.returncode == 0
    output = (result.stdout or result.stderr).strip().splitlines()
    tail = output[-1] if output else "no test output"
    return GateCheck("tests", passed, tail)


def check_provider_breadth() -> GateCheck:
    available = ProviderRegistry().available()
    passed = "wikipedia_search" in available and len(available) >= 3
    return GateCheck(
        "provider_breadth",
        passed,
        f"available providers: {', '.join(available)}",
    )


def check_cli_surface(repo_root: Path) -> GateCheck:
    cli_path = repo_root / "src" / "research_operator" / "cli.py"
    text = cli_path.read_text(encoding="utf-8")
    required_tokens = ["def run(", "def export(", "def providers(", "def runs("]
    missing = [token for token in required_tokens if token not in text]
    passed = not missing
    detail = "cli surface complete" if passed else f"missing CLI commands: {', '.join(missing)}"
    return GateCheck("cli_surface", passed, detail)


def check_watch_surface(repo_root: Path) -> GateCheck:
    cli_path = repo_root / "src" / "research_operator" / "cli.py"
    text = cli_path.read_text(encoding="utf-8")
    required_tokens = ["watch_create", "watch_run", "watch_run_all", "watch_list"]
    missing = [token for token in required_tokens if token not in text]
    passed = not missing
    detail = "watch surface complete" if passed else f"missing watch commands: {', '.join(missing)}"
    return GateCheck("watch_surface", passed, detail)


def check_structured_outputs(repo_root: Path) -> GateCheck:
    artifacts_path = repo_root / "src" / "research_operator" / "runtime" / "artifacts.py"
    text = artifacts_path.read_text(encoding="utf-8")
    required_tokens = ["entities.csv", "events.csv", "source_ledger.json", "research_report.html"]
    missing = [token for token in required_tokens if token not in text]
    passed = not missing
    detail = "structured outputs wired" if passed else f"missing artifacts: {', '.join(missing)}"
    return GateCheck("structured_outputs", passed, detail)


def check_report_quality_surface(repo_root: Path) -> GateCheck:
    artifacts_path = repo_root / "src" / "research_operator" / "runtime" / "artifacts.py"
    text = artifacts_path.read_text(encoding="utf-8")
    required_tokens = ["Executive Summary", "Key Evidence", "Limitations", "Citations"]
    missing = [token for token in required_tokens if token not in text]
    passed = not missing
    detail = "report quality sections present" if passed else f"missing report sections: {', '.join(missing)}"
    return GateCheck("report_quality_surface", passed, detail)


def check_query_provider_diversity() -> GateCheck:
    available = ProviderRegistry().available()
    query_capable = [name for name in available if name not in {"attached", "web_fetch"}]
    passed = len(query_capable) >= 2
    return GateCheck(
        "query_provider_diversity",
        passed,
        f"query-capable providers: {', '.join(query_capable) if query_capable else 'none'}",
    )


def check_api_surface(repo_root: Path) -> GateCheck:
    api_files = [
        repo_root / "src" / "research_operator" / "api.py",
        repo_root / "src" / "research_operator" / "api" / "__init__.py",
    ]
    passed = any(path.exists() for path in api_files)
    detail = "api surface present" if passed else "missing API surface for non-CLI customers"
    return GateCheck("api_surface", passed, detail)


def check_notification_surface(repo_root: Path) -> GateCheck:
    candidates = [
        repo_root / "src" / "research_operator" / "runtime" / "notifications.py",
        repo_root / "src" / "research_operator" / "runtime" / "delivery.py",
    ]
    passed = any(path.exists() for path in candidates)
    detail = "notification surface present" if passed else "missing notification/delivery surface"
    return GateCheck("notification_surface", passed, detail)


def check_source_fusion_surface(repo_root: Path) -> GateCheck:
    candidates = [
        repo_root / "src" / "research_operator" / "runtime" / "fusion.py",
        repo_root / "src" / "research_operator" / "runtime" / "dedupe.py",
    ]
    passed = any(path.exists() for path in candidates)
    detail = "source fusion present" if passed else "missing multi-source fusion/deduplication layer"
    return GateCheck("source_fusion_surface", passed, detail)


def check_demo_acceptance_surface(repo_root: Path) -> GateCheck:
    acceptance_test = repo_root / "tests" / "test_acceptance.py"
    passed = acceptance_test.exists()
    detail = "acceptance demo tests present" if passed else "missing customer demo acceptance tests"
    return GateCheck("demo_acceptance_surface", passed, detail)
