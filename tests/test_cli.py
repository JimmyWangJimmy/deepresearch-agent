from __future__ import annotations

import json

from typer.testing import CliRunner

from research_operator.cli import app


runner = CliRunner()


def test_run_creates_artifacts(tmp_path):
    source_file = tmp_path / "input.txt"
    source_file.write_text("机器人行业融资升温，自动化和具身智能成为焦点。", encoding="utf-8")
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
    assert (tmp_path / run_id / "research_report.md").exists()
    assert (tmp_path / run_id / "research_report.html").exists()
    assert (tmp_path / run_id / "findings.json").exists()
    assert (tmp_path / run_id / "source_ledger.json").exists()
    assert payload["sources"][0]["label"] == "input.txt"


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
    assert len(second_payload["changed_sources"]) == 0
    assert second_payload["new_run_id"] is None

    watch_file.write_text("版本二，新增融资披露", encoding="utf-8")
    third_run = runner.invoke(
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
    assert third_run.exit_code == 0
    third_payload = json.loads(third_run.stdout)
    assert len(third_payload["changed_sources"]) == 1
    assert third_payload["new_run_id"] is not None
    digest_path = tmp_path / "watches" / created["watch_id"] / "last_digest.md"
    assert digest_path.exists()
    assert "Changed Sources" in digest_path.read_text(encoding="utf-8")


def test_providers_lists_available_backends():
    result = runner.invoke(app, ["providers", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "attached" in payload
    assert "web_fetch" in payload
