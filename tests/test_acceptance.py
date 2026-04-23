from __future__ import annotations

import json

from typer.testing import CliRunner

from research_operator.cli import app
from research_operator.schemas import CollectedSource, ProviderKind, SourceRecord


runner = CliRunner()


def test_acceptance_research_deliverable(tmp_path, monkeypatch):
    from research_operator.runtime.provider_registry import WikipediaSearchProvider

    def fake_collect_query(self, query: str):
        return [
            CollectedSource(
                record=SourceRecord(
                    label="Robotics",
                    kind="search_result",
                    locator="https://example.com/robotics",
                    excerpt="Robotics overview excerpt.",
                    content_chars=25,
                    provider=ProviderKind.WIKIPEDIA_SEARCH,
                ),
                content="Robotics overview excerpt. 2026年4月20日，星海机器人公司完成2亿元人民币融资。",
            )
        ]

    monkeypatch.setattr(WikipediaSearchProvider, "collect_query", fake_collect_query)

    result = runner.invoke(
        app,
        [
            "run",
            "robotics industry overview",
            "--provider",
            "wikipedia_search",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    run_dir = tmp_path / payload["run_id"]
    assert (run_dir / "run_summary.json").exists()
    assert (run_dir / "research_report.md").exists()
    assert (run_dir / "research_report.html").exists()
    assert (run_dir / "quality.json").exists()
    assert (run_dir / "research_report.pdf").exists()
    assert (run_dir / "research_workbook.xlsx").exists()
    assert (run_dir / "delivery_bundle.zip").exists()
    assert (run_dir / "source_scores.svg").exists()
    assert (run_dir / "event_timeline.svg").exists()
    report = (run_dir / "research_report.md").read_text(encoding="utf-8")
    assert "## Executive Summary" in report
    assert "## Key Evidence" in report
    assert payload["sources"]


def test_acceptance_monitoring_deliverable(tmp_path):
    watch_file = tmp_path / "watch.txt"
    watch_file.write_text("版本一", encoding="utf-8")
    created = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Acceptance Watch",
            "--task",
            "监控研究源变化",
            "--interval-minutes",
            "30",
            "--file",
            str(watch_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert created.exit_code == 0
    watch_id = json.loads(created.stdout)["watch_id"]

    run_result = runner.invoke(
        app,
        [
            "watch",
            "run",
            watch_id,
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )
    assert run_result.exit_code == 0
    watch_dir = tmp_path / "watches" / watch_id
    assert (watch_dir / "last_digest.md").exists()
    assert (watch_dir / "notification.txt").exists()
    notification = json.loads((watch_dir / "notification.json").read_text(encoding="utf-8"))
    assert notification["deliverables"]["summary"].endswith("run_summary.json")
    assert notification["deliverables"]["quality"].endswith("quality.json")
    assert notification["deliverables"]["pdf_report"].endswith("research_report.pdf")
    assert notification["deliverables"]["delivery_bundle"].endswith("delivery_bundle.zip")
    assert notification["deliverables"]["event_timeline_chart"].endswith("event_timeline.svg")
