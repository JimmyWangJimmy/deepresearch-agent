from __future__ import annotations

import json
from zipfile import ZipFile

from typer.testing import CliRunner

from research_operator.cli import app
from research_operator.schemas import CollectedSource, ProviderKind, SourceRecord


runner = CliRunner()


def test_run_creates_artifacts(tmp_path):
    source_file = tmp_path / "input.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资，远望资本领投。", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "分析机器人行业融资",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    run_id = payload["run_id"]
    assert (tmp_path / run_id / "run_manifest.json").exists()
    assert (tmp_path / run_id / "run_summary.json").exists()
    assert (tmp_path / run_id / "research_report.md").exists()
    assert (tmp_path / run_id / "research_report.html").exists()
    assert (tmp_path / run_id / "research_report.pdf").exists()
    assert (tmp_path / run_id / "quality.json").exists()
    assert (tmp_path / run_id / "research_workbook.xlsx").exists()
    assert (tmp_path / run_id / "delivery_bundle.zip").exists()
    assert (tmp_path / run_id / "source_scores.svg").exists()
    assert (tmp_path / run_id / "event_timeline.svg").exists()
    assert (tmp_path / run_id / "findings.json").exists()
    assert (tmp_path / run_id / "source_ledger.json").exists()
    assert (tmp_path / run_id / "entities.json").exists()
    assert (tmp_path / run_id / "entities.csv").exists()
    assert (tmp_path / run_id / "events.json").exists()
    assert (tmp_path / run_id / "events.csv").exists()
    assert payload["sources"][0]["label"] == "input.txt"
    assert "evidence_score" in payload["sources"][0]
    assert payload["entities"]
    assert payload["events"]
    quality = json.loads((tmp_path / run_id / "quality.json").read_text(encoding="utf-8"))
    assert quality["score"] > 0
    assert quality["warnings"]
    summary = json.loads((tmp_path / run_id / "run_summary.json").read_text(encoding="utf-8"))
    assert summary["quality_score"] == quality["score"]
    assert summary["primary_deliverables"]["bundle"].endswith("delivery_bundle.zip")
    assert summary["source_highlights"]
    assert summary["recent_events"]


def test_inspect_reads_manifest(tmp_path):
    run_result = runner.invoke(
        app,
        [
            "run",
            "监控AI新闻",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    inspect_result = runner.invoke(
        app,
        ["inspect", payload["run_id"], "--artifacts-dir", str(tmp_path)],
    )

    assert inspect_result.exit_code == 0
    inspected = json.loads(inspect_result.stdout)
    assert inspected["run_id"] == payload["run_id"]


def test_runs_filters_by_task_type_and_limit(tmp_path):
    first = runner.invoke(
        app,
        ["run", "监控AI新闻", "--artifacts-dir", str(tmp_path), "--json"],
    )
    second_file = tmp_path / "funding.txt"
    second_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    second = runner.invoke(
        app,
        ["run", "分析这个文件并提取要点", "--file", str(second_file), "--artifacts-dir", str(tmp_path), "--json"],
    )
    assert first.exit_code == 0
    assert second.exit_code == 0

    filtered = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--task-type", "file_intelligence", "--limit", "1", "--json"],
    )
    assert filtered.exit_code == 0
    payload = json.loads(filtered.stdout)
    assert len(payload) == 1
    assert payload[0]["plan"]["task_type"] == "file_intelligence"

    searched = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--task-contains", "文件", "--json"],
    )
    assert searched.exit_code == 0
    searched_payload = json.loads(searched.stdout)
    assert len(searched_payload) == 1
    assert "文件" in searched_payload[0]["task"]

    warned = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--has-warnings", "--json"],
    )
    assert warned.exit_code == 0
    warned_payload = json.loads(warned.stdout)
    assert len(warned_payload) == 2

    low_quality = runner.invoke(
        app,
        ["run", "普通任务", "--artifacts-dir", str(tmp_path), "--json"],
    )
    assert low_quality.exit_code == 0

    high_quality = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--min-quality-score", "0.75", "--json"],
    )
    assert high_quality.exit_code == 0
    high_quality_payload = json.loads(high_quality.stdout)
    assert len(high_quality_payload) >= 1
    assert all(
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["score"] >= 0.75
        for item in high_quality_payload
    )

    single_source = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--max-source-count", "1", "--json"],
    )
    assert single_source.exit_code == 0
    single_source_payload = json.loads(single_source.stdout)
    assert len(single_source_payload) >= 1
    assert all(
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["source_count"] <= 1
        for item in single_source_payload
    )

    eventful = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--min-event-count", "1", "--json"],
    )
    assert eventful.exit_code == 0
    eventful_payload = json.loads(eventful.stdout)
    assert len(eventful_payload) >= 1
    assert all(
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["event_count"] >= 1
        for item in eventful_payload
    )

    entityful = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--min-entity-count", "1", "--json"],
    )
    assert entityful.exit_code == 0
    entityful_payload = json.loads(entityful.stdout)
    assert len(entityful_payload) >= 1
    assert all(
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["entity_count"] >= 1
        for item in entityful_payload
    )

    strong_evidence = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--min-average-evidence-score", "0.75", "--json"],
    )
    assert strong_evidence.exit_code == 0
    strong_evidence_payload = json.loads(strong_evidence.stdout)
    assert len(strong_evidence_payload) >= 1
    assert all(
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["average_evidence_score"] >= 0.75
        for item in strong_evidence_payload
    )

    sorted_by_quality = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--sort-by", "quality_desc", "--json"],
    )
    assert sorted_by_quality.exit_code == 0
    sorted_payload = json.loads(sorted_by_quality.stdout)
    scores = [
        json.loads((tmp_path / item["run_id"] / "quality.json").read_text(encoding="utf-8"))["score"]
        for item in sorted_payload
    ]
    assert scores == sorted(scores, reverse=True)

    summary = runner.invoke(
        app,
        ["runs-summary", "--artifacts-dir", str(tmp_path)],
    )
    assert summary.exit_code == 0
    summary_payload = json.loads(summary.stdout)
    assert summary_payload["run_count"] >= 3
    assert "research" in summary_payload["task_types"] or "monitor" in summary_payload["task_types"]


def test_verify_checks_run_integrity(tmp_path):
    source_file = tmp_path / "verify.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "验证研究交付物",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)

    verify_result = runner.invoke(
        app,
        [
            "verify",
            payload["run_id"],
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert verify_result.exit_code == 0
    verification = json.loads(verify_result.stdout)
    assert verification["ready"] is True
    assert {item["name"] for item in verification["checks"]} >= {"core_artifacts", "delivery_bundle", "quality", "summary"}


def test_export_copies_html_artifact(tmp_path):
    source_file = tmp_path / "evidence.md"
    source_file.write_text("# Title\n\nAlternative data signal from filings.", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "生成研究报告",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)

    export_target = tmp_path / "exports" / "report.html"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "html",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )

    assert export_result.exit_code == 0
    assert export_target.exists()
    assert "<!doctype html>" in export_target.read_text(encoding="utf-8").lower()
    assert "Executive Summary" in export_target.read_text(encoding="utf-8")


def test_export_copies_events_csv(tmp_path):
    source_file = tmp_path / "events.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出事件结构化表",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)

    export_target = tmp_path / "exports" / "events.csv"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "events_csv",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert "event_type" in export_target.read_text(encoding="utf-8")


def test_export_copies_xlsx_artifact(tmp_path):
    source_file = tmp_path / "xlsx.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出 Excel 交付物",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "research.xlsx"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "xlsx",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert export_target.exists()


def test_export_copies_chart_artifact(tmp_path):
    source_file = tmp_path / "chart.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出图表交付物",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "chart.svg"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "chart",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert export_target.exists()
    assert "<svg" in export_target.read_text(encoding="utf-8")


def test_export_copies_timeline_chart_artifact(tmp_path):
    source_file = tmp_path / "timeline.txt"
    source_file.write_text(
        "2026年4月20日，星海机器人公司完成2亿元人民币融资。2026年4月22日，远航智造发布新型人形机器人平台。",
        encoding="utf-8",
    )
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出时间线图表交付物",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "timeline.svg"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "timeline_chart",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert export_target.exists()
    contents = export_target.read_text(encoding="utf-8")
    assert "<svg" in contents
    assert "Event Timeline" in contents


def test_export_copies_pdf_artifact(tmp_path):
    source_file = tmp_path / "pdf.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出 PDF 交付物",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "report.pdf"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "pdf",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert export_target.exists()
    assert export_target.read_bytes().startswith(b"%PDF")


def test_export_copies_delivery_bundle(tmp_path):
    source_file = tmp_path / "bundle.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出完整交付包",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "delivery_bundle.zip"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "bundle",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    assert export_target.exists()
    with ZipFile(export_target) as archive:
        names = set(archive.namelist())
    assert "research_report.pdf" in names
    assert "run_summary.json" in names
    assert "quality.json" in names
    assert "research_workbook.xlsx" in names
    assert "source_scores.svg" in names
    assert "event_timeline.svg" in names


def test_export_all_copies_full_delivery_set(tmp_path):
    source_file = tmp_path / "all.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "输出完整全量交付集",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    payload = json.loads(run_result.stdout)
    export_target = tmp_path / "exports" / "all"
    export_result = runner.invoke(
        app,
        [
            "export",
            payload["run_id"],
            "--format",
            "all",
            "--artifacts-dir",
            str(tmp_path),
            "--output",
            str(export_target),
        ],
    )
    assert export_result.exit_code == 0
    exported = json.loads(export_result.stdout)["exported"]
    assert "bundle" in exported
    assert (export_target / "delivery_bundle.zip").exists()
    assert (export_target / "research_report.pdf").exists()
    assert (export_target / "run_summary.json").exists()


def test_runs_lists_history(tmp_path):
    first = runner.invoke(
        app,
        [
            "run",
            "任务一",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    second = runner.invoke(
        app,
        [
            "run",
            "任务二",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert first.exit_code == 0
    assert second.exit_code == 0

    result = runner.invoke(
        app,
        ["runs", "--artifacts-dir", str(tmp_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 2
    assert {item["task"] for item in payload} == {"任务一", "任务二"}


def test_quality_command_reads_quality_artifact(tmp_path):
    source_file = tmp_path / "quality.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    run_result = runner.invoke(
        app,
        [
            "run",
            "读取质量评分",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert run_result.exit_code == 0
    run_id = json.loads(run_result.stdout)["run_id"]
    quality_result = runner.invoke(app, ["quality", run_id, "--artifacts-dir", str(tmp_path)])
    assert quality_result.exit_code == 0
    payload = json.loads(quality_result.stdout)
    assert payload["score"] > 0
    assert payload["source_count"] == 1


def test_watch_create_and_run_detects_changes(tmp_path):
    watch_file = tmp_path / "watched.txt"
    watch_file.write_text("版本一", encoding="utf-8")
    create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "机器人监控",
            "--task",
            "监控机器人赛道变化并生成摘要",
            "--interval-minutes",
            "30",
            "--file",
            str(watch_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert create.exit_code == 0
    created = json.loads(create.stdout)

    first_run = runner.invoke(
        app,
        [
            "watch",
            "run",
            created["watch_id"],
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )
    assert first_run.exit_code == 0
    first_payload = json.loads(first_run.stdout)
    assert len(first_payload["changed_sources"]) == 1
    assert first_payload["new_run_id"] is not None

    second_run = runner.invoke(
        app,
        [
            "watch",
            "run",
            created["watch_id"],
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )
    assert second_run.exit_code == 0
    second_payload = json.loads(second_run.stdout)
    assert second_payload["skipped_reason"] == "watch_not_due"

    watch_file.write_text("版本二，新增融资披露", encoding="utf-8")
    third_run = runner.invoke(
        app,
        [
            "watch",
            "run",
            created["watch_id"],
            "--force",
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )
    assert third_run.exit_code == 0
    third_payload = json.loads(third_run.stdout)
    assert len(third_payload["changed_sources"]) == 1
    assert third_payload["new_run_id"] is not None
    digest_path = tmp_path / "watches" / created["watch_id"] / "last_digest.md"
    assert digest_path.exists()
    assert "Changed Sources" in digest_path.read_text(encoding="utf-8")
    notification_path = tmp_path / "watches" / created["watch_id"] / "notification.txt"
    assert notification_path.exists()
    assert "new_run_id=" in notification_path.read_text(encoding="utf-8")
    notification_json = tmp_path / "watches" / created["watch_id"] / "notification.json"
    assert notification_json.exists()
    notification_payload = json.loads(notification_json.read_text(encoding="utf-8"))
    assert notification_payload["title"]
    assert notification_payload["deliverables"]["summary"].endswith("run_summary.json")
    assert notification_payload["deliverables"]["quality"].endswith("quality.json")
    assert notification_payload["deliverables"]["pdf_report"].endswith("research_report.pdf")
    assert notification_payload["deliverables"]["workbook"].endswith("research_workbook.xlsx")
    assert notification_payload["deliverables"]["delivery_bundle"].endswith("delivery_bundle.zip")
    assert notification_payload["deliverables"]["source_score_chart"].endswith("source_scores.svg")
    assert notification_payload["deliverables"]["event_timeline_chart"].endswith("event_timeline.svg")

    inspected = runner.invoke(
        app,
        [
            "watch",
            "inspect",
            created["watch_id"],
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert inspected.exit_code == 0
    inspect_payload = json.loads(inspected.stdout)
    assert inspect_payload["watch"]["watch_id"] == created["watch_id"]
    assert inspect_payload["last_execution"]["new_run_id"] == third_payload["new_run_id"]
    assert inspect_payload["notification"]["deliverables"]["delivery_bundle"].endswith("delivery_bundle.zip")
    assert "Changed Sources" in inspect_payload["digest"]

    manifest = runner.invoke(
        app,
        [
            "watch",
            "delivery-manifest",
            created["watch_id"],
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert manifest.exit_code == 0
    manifest_payload = json.loads(manifest.stdout)
    assert manifest_payload["latest"]["run_id"] == third_payload["new_run_id"]
    assert manifest_payload["primary"]["delivery_bundle"].endswith("delivery_bundle.zip")
    assert manifest_payload["notification"]["title"]

    disabled = runner.invoke(
        app,
        [
            "watch",
            "set-enabled",
            created["watch_id"],
            "--disabled",
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert disabled.exit_code == 0
    disabled_payload = json.loads(disabled.stdout)
    assert disabled_payload["enabled"] is False

    reenabled = runner.invoke(
        app,
        [
            "watch",
            "set-enabled",
            created["watch_id"],
            "--enabled",
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert reenabled.exit_code == 0
    reenabled_payload = json.loads(reenabled.stdout)
    assert reenabled_payload["enabled"] is True
    assert reenabled_payload["next_run_at"] is not None


def test_providers_lists_available_backends():
    result = runner.invoke(app, ["providers", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "attached" in payload
    assert "web_fetch" in payload
    assert "openai_web_research" in payload


def test_doctor_reports_environment_status(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(app, ["doctor", "--artifacts-dir", str(tmp_path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ready"] is False
    checks = {item["name"]: item for item in payload["checks"]}
    assert checks["artifacts_dir"]["passed"] is True
    assert checks["providers"]["passed"] is True
    assert checks["openai_web_research"]["passed"] is False


def test_watch_run_all_executes_multiple_specs(tmp_path):
    first_file = tmp_path / "first.txt"
    second_file = tmp_path / "second.txt"
    first_file.write_text("2026年4月，甲公司完成融资。", encoding="utf-8")
    second_file.write_text("2026年4月，乙公司发布新产品。", encoding="utf-8")

    first_create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Watch A",
            "--task",
            "监控甲公司",
            "--interval-minutes",
            "15",
            "--file",
            str(first_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    second_create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Watch B",
            "--task",
            "监控乙公司",
            "--interval-minutes",
            "15",
            "--file",
            str(second_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert first_create.exit_code == 0
    assert second_create.exit_code == 0

    result = runner.invoke(
        app,
        [
            "watch",
            "run-all",
            "--all",
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 2
    assert all(item["new_run_id"] for item in payload)


def test_watch_list_due_only_filters_not_due(tmp_path):
    watch_file = tmp_path / "watch.txt"
    watch_file.write_text("初始版本", encoding="utf-8")
    create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Due Watch",
            "--task",
            "监控变化",
            "--interval-minutes",
            "60",
            "--file",
            str(watch_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    created = json.loads(create.stdout)
    first_run = runner.invoke(
        app,
        [
            "watch",
            "run",
            created["watch_id"],
            "--watches-dir",
            str(tmp_path / "watches"),
            "--artifacts-dir",
            str(tmp_path / "artifacts"),
        ],
    )
    assert first_run.exit_code == 0

    due_list = runner.invoke(
        app,
        [
            "watch",
            "list",
            "--due-only",
            "--watches-dir",
            str(tmp_path / "watches"),
            "--json",
        ],
    )
    assert due_list.exit_code == 0
    assert json.loads(due_list.stdout) == []


def test_watch_list_filters_enabled_state(tmp_path):
    watch_file = tmp_path / "stateful-watch.txt"
    watch_file.write_text("初始版本", encoding="utf-8")
    webhook_file = tmp_path / "webhook-watch.txt"
    webhook_file.write_text("初始版本", encoding="utf-8")
    create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Stateful Watch",
            "--task",
            "监控启停状态",
            "--file",
            str(watch_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert create.exit_code == 0
    watch_id = json.loads(create.stdout)["watch_id"]
    webhook_create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Webhook Filter Watch",
            "--task",
            "监控 webhook 过滤",
            "--webhook-url",
            "https://example.com/hook",
            "--file",
            str(webhook_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert webhook_create.exit_code == 0

    disabled = runner.invoke(
        app,
        [
            "watch",
            "set-enabled",
            watch_id,
            "--disabled",
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert disabled.exit_code == 0

    enabled_list = runner.invoke(
        app,
        ["watch", "list", "--json", "--enabled-only", "--watches-dir", str(tmp_path / "watches")],
    )
    assert enabled_list.exit_code == 0
    enabled_payload = json.loads(enabled_list.stdout)
    assert len(enabled_payload) == 1
    assert enabled_payload[0]["webhook_url"] == "https://example.com/hook"

    disabled_list = runner.invoke(
        app,
        ["watch", "list", "--json", "--disabled-only", "--watches-dir", str(tmp_path / "watches")],
    )
    assert disabled_list.exit_code == 0
    payload = json.loads(disabled_list.stdout)
    assert len(payload) == 1
    assert payload[0]["watch_id"] == watch_id

    webhook_list = runner.invoke(
        app,
        ["watch", "list", "--json", "--has-webhook", "--watches-dir", str(tmp_path / "watches")],
    )
    assert webhook_list.exit_code == 0
    webhook_payload = json.loads(webhook_list.stdout)
    assert len(webhook_payload) == 1
    assert webhook_payload[0]["webhook_url"] == "https://example.com/hook"

    summary = runner.invoke(
        app,
        ["watch", "summary", "--has-webhook", "--watches-dir", str(tmp_path / "watches")],
    )
    assert summary.exit_code == 0
    summary_payload = json.loads(summary.stdout)
    assert summary_payload["watch_count"] == 1
    assert summary_payload["webhook_count"] == 1

    sorted_watches = runner.invoke(
        app,
        ["watch", "list", "--json", "--sort-by", "interval_desc", "--watches-dir", str(tmp_path / "watches")],
    )
    assert sorted_watches.exit_code == 0
    sorted_payload = json.loads(sorted_watches.stdout)
    intervals = [item["interval_minutes"] for item in sorted_payload]
    assert intervals == sorted(intervals, reverse=True)


def test_watch_delete_removes_watch(tmp_path):
    watch_file = tmp_path / "delete-watch.txt"
    watch_file.write_text("初始版本", encoding="utf-8")
    create = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Delete Watch",
            "--task",
            "删除监控",
            "--file",
            str(watch_file),
            "--watches-dir",
            str(tmp_path / "watches"),
        ],
    )
    assert create.exit_code == 0
    watch_id = json.loads(create.stdout)["watch_id"]

    deleted = runner.invoke(
        app,
        ["watch", "delete", watch_id, "--watches-dir", str(tmp_path / "watches")],
    )
    assert deleted.exit_code == 0
    assert json.loads(deleted.stdout)["watch_id"] == watch_id
    assert not (tmp_path / "watches" / watch_id).exists()


def test_watch_posts_webhook_when_configured(tmp_path, monkeypatch):
    posted: dict[str, object] = {}

    def fake_post_webhook(url: str, payload: dict) -> None:
        posted["url"] = url
        posted["payload"] = payload

    monkeypatch.setattr(
        "research_operator.runtime.monitoring.post_webhook",
        fake_post_webhook,
    )

    watch_file = tmp_path / "webhook.txt"
    watch_file.write_text("版本一", encoding="utf-8")
    created = runner.invoke(
        app,
        [
            "watch",
            "create",
            "Webhook Watch",
            "--task",
            "监控 webhook 通知",
            "--interval-minutes",
            "15",
            "--webhook-url",
            "https://example.com/hook",
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
    assert posted["url"] == "https://example.com/hook"
    assert isinstance(posted["payload"], dict)


def test_run_uses_query_provider_when_no_sources(tmp_path, monkeypatch):
    from research_operator.runtime.provider_registry import WikipediaSearchProvider

    def fake_collect_query(self, query: str):
        return [
            CollectedSource(
                record=SourceRecord(
                    label="Robotics",
                    kind="search_result",
                    locator="https://example.com/robotics",
                    excerpt="Robotics is an interdisciplinary branch of engineering.",
                    content_chars=56,
                    provider=ProviderKind.WIKIPEDIA_SEARCH,
                ),
                content="Robotics is an interdisciplinary branch of engineering.",
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
    assert payload["sources"][0]["provider"] == "wikipedia_search"
    assert payload["sources"][0]["label"] == "Robotics"


def test_run_supports_second_query_provider(tmp_path, monkeypatch):
    from research_operator.runtime.provider_registry import ArxivSearchProvider

    def fake_collect_query(self, query: str):
        return [
            CollectedSource(
                record=SourceRecord(
                    label="Vision-Language Models for Robotics",
                    kind="search_result",
                    locator="https://arxiv.org/abs/1234.5678",
                    excerpt="A survey of robotics research.",
                    content_chars=30,
                    provider=ProviderKind.ARXIV_SEARCH,
                ),
                content="A survey of robotics research.",
            )
        ]

    monkeypatch.setattr(ArxivSearchProvider, "collect_query", fake_collect_query)

    result = runner.invoke(
        app,
        [
            "run",
            "robotics research survey",
            "--provider",
            "arxiv_search",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["sources"][0]["provider"] == "arxiv_search"


def test_openai_web_research_provider_uses_responses_api(monkeypatch):
    from research_operator.runtime.provider_registry import OpenAIWebResearchProvider

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "id": "resp_test",
                "output_text": "2026年4月20日，星海机器人公司完成2亿元人民币融资。Source: https://example.com/funding",
            }

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def post(self, url, headers, json):
            assert url == "https://api.openai.com/v1/responses"
            assert headers["Authorization"] == "Bearer test-key"
            assert json["tools"] == [{"type": "web_search"}]
            return FakeResponse()

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("research_operator.runtime.provider_registry.httpx.Client", FakeClient)

    collected = OpenAIWebResearchProvider().collect_query("robotics funding")
    assert collected[0].record.provider == ProviderKind.OPENAI_WEB_RESEARCH
    assert collected[0].record.locator == "openai:responses/resp_test"
    assert "星海机器人公司" in collected[0].content


def test_openai_web_research_provider_reports_missing_key(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    result = runner.invoke(
        app,
        [
            "run",
            "robotics funding",
            "--provider",
            "openai_web_research",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code != 0
    assert "OPENAI_API_KEY is required" in result.output


def test_wikipedia_title_ranking_prefers_reference_results():
    from research_operator.runtime.provider_registry import rank_titles

    ranked = rank_titles(
        ["Robotics;Notes", "Robotics", "Robotics engineering"],
        "robotics industry overview",
    )

    assert ranked[0] == "Robotics"
    assert "Robotics;Notes" not in ranked


def test_gate_reports_blocked_state():
    result = runner.invoke(app, ["gate", "--json"])
    assert result.exit_code in {0, 2}
    payload = json.loads(result.stdout)
    assert "ready" in payload
    assert payload["checks"]


def test_markdown_report_contains_customer_sections(tmp_path):
    source_file = tmp_path / "report.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "run",
            "生成客户级研究报告",
            "--file",
            str(source_file),
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    report = (tmp_path / payload["run_id"] / "research_report.md").read_text(encoding="utf-8")
    assert "## Executive Summary" in report
    assert "## Key Evidence" in report
    assert "## Citations" in report
    assert "## Limitations" in report


def test_source_scores_are_ranked(tmp_path, monkeypatch):
    from research_operator.runtime.provider_registry import WikipediaSearchProvider

    def fake_collect_query(self, query: str):
        return [
            CollectedSource(
                record=SourceRecord(
                    label="Weak Source",
                    kind="search_result",
                    locator="https://example.com/weak",
                    excerpt="Short",
                    content_chars=5,
                    provider=ProviderKind.WIKIPEDIA_SEARCH,
                ),
                content="Short",
            ),
            CollectedSource(
                record=SourceRecord(
                    label="Strong Source",
                    kind="search_result",
                    locator="https://example.com/strong",
                    excerpt="2026年4月20日，星海机器人公司完成2亿元人民币融资。",
                    content_chars=32,
                    provider=ProviderKind.WIKIPEDIA_SEARCH,
                ),
                content="2026年4月20日，星海机器人公司完成2亿元人民币融资。",
            ),
        ]

    monkeypatch.setattr(WikipediaSearchProvider, "collect_query", fake_collect_query)
    result = runner.invoke(
        app,
        [
            "run",
            "robotics financing",
            "--provider",
            "wikipedia_search",
            "--artifacts-dir",
            str(tmp_path),
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["sources"][0]["label"] == "Strong Source"
    assert payload["sources"][0]["evidence_score"] >= payload["sources"][1]["evidence_score"]


def test_fusion_collapses_duplicate_sources_and_records():
    from research_operator.runtime.fusion import fuse_entities, fuse_events, fuse_sources

    source = CollectedSource(
        record=SourceRecord(
            label="Robotics",
            kind="search_result",
            locator="https://example.com/robotics",
            excerpt="Robotics",
            content_chars=8,
            provider=ProviderKind.WIKIPEDIA_SEARCH,
        ),
        content="Robotics overview",
    )
    dup_source = CollectedSource(
        record=SourceRecord(
            label="Robotics duplicate",
            kind="search_result",
            locator="https://example.com/robotics/",
            excerpt="Robotics",
            content_chars=8,
            provider=ProviderKind.WIKIPEDIA_SEARCH,
        ),
        content="Robotics   overview",
    )
    assert len(fuse_sources([source, dup_source])) == 1

    entity = {
        "entity": "星海机器人公司",
        "category": "organization",
        "source_label": "a",
        "source_locator": "x",
    }
    event = {
        "event_type": "financing",
        "subject": "星海机器人公司",
        "amount": "2亿元人民币",
        "event_date": "2026年4月20日",
        "source_label": "a",
        "source_locator": "x",
        "evidence": "sample",
    }
    from research_operator.schemas import ExtractedEntity, ExtractedEvent

    assert len(fuse_entities([ExtractedEntity(**entity), ExtractedEntity(**entity)])) == 1
    assert len(fuse_events([ExtractedEvent(**event), ExtractedEvent(**event)])) == 1
