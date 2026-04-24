from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile


@dataclass
class VerificationCheck:
    name: str
    passed: bool
    detail: str


@dataclass
class VerificationReport:
    ready: bool
    checks: list[VerificationCheck]


def verify_run_dir(run_dir: Path) -> VerificationReport:
    checks = [
        check_core_artifacts(run_dir),
        check_delivery_bundle(run_dir),
        check_quality_artifact(run_dir),
        check_summary_artifact(run_dir),
    ]
    return VerificationReport(ready=all(item.passed for item in checks), checks=checks)


def check_core_artifacts(run_dir: Path) -> VerificationCheck:
    required = [
        run_dir / "run_manifest.json",
        run_dir / "run_summary.json",
        run_dir / "quality.json",
        run_dir / "research_report.html",
        run_dir / "research_report.pdf",
        run_dir / "research_workbook.xlsx",
        run_dir / "delivery_bundle.zip",
        run_dir / "source_ledger.json",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        return VerificationCheck("core_artifacts", False, f"missing artifacts: {', '.join(missing)}")
    return VerificationCheck("core_artifacts", True, f"{len(required)} core artifacts present")


def check_delivery_bundle(run_dir: Path) -> VerificationCheck:
    bundle_path = run_dir / "delivery_bundle.zip"
    if not bundle_path.exists():
        return VerificationCheck("delivery_bundle", False, "delivery_bundle.zip missing")

    try:
        with ZipFile(bundle_path) as archive:
            names = set(archive.namelist())
    except BadZipFile:
        return VerificationCheck("delivery_bundle", False, "delivery_bundle.zip is not a valid zip archive")

    expected = {
        "run_manifest.json",
        "run_summary.json",
        "quality.json",
        "research_report.html",
        "research_report.pdf",
        "research_workbook.xlsx",
    }
    missing = sorted(expected - names)
    if missing:
        return VerificationCheck("delivery_bundle", False, f"bundle missing members: {', '.join(missing)}")
    return VerificationCheck("delivery_bundle", True, f"bundle contains {len(names)} members")


def check_quality_artifact(run_dir: Path) -> VerificationCheck:
    quality_path = run_dir / "quality.json"
    if not quality_path.exists():
        return VerificationCheck("quality", False, "quality.json missing")
    payload = json.loads(quality_path.read_text(encoding="utf-8"))
    if payload.get("score", 0) <= 0:
        return VerificationCheck("quality", False, "quality score must be > 0")
    return VerificationCheck("quality", True, f"quality score={payload['score']}")


def check_summary_artifact(run_dir: Path) -> VerificationCheck:
    summary_path = run_dir / "run_summary.json"
    if not summary_path.exists():
        return VerificationCheck("summary", False, "run_summary.json missing")
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    deliverables = payload.get("primary_deliverables", {})
    if not deliverables.get("bundle"):
        return VerificationCheck("summary", False, "summary missing primary bundle path")
    if not payload.get("source_highlights"):
        return VerificationCheck("summary", False, "summary missing source_highlights")
    return VerificationCheck("summary", True, f"summary exposes {len(payload['source_highlights'])} source highlights")
