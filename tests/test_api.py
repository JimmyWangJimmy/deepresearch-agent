from __future__ import annotations

from fastapi.testclient import TestClient

from research_operator.api import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_providers_endpoint():
    response = client.get("/providers")
    assert response.status_code == 200
    payload = response.json()
    assert "providers" in payload
    assert "wikipedia_search" in payload["providers"]


def test_doctor_endpoint(tmp_path):
    response = client.get("/doctor", params={"artifacts_dir": str(tmp_path)})
    assert response.status_code == 200
    payload = response.json()
    assert "checks" in payload
    assert any(item["name"] == "artifacts_dir" for item in payload["checks"])


def test_create_and_fetch_run_via_api(tmp_path):
    source_file = tmp_path / "funding.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")

    response = client.post(
        "/runs",
        json={
            "task": "通过 API 生成研究交付物",
            "files": [str(source_file)],
            "artifacts_dir": str(tmp_path),
        },
    )
    assert response.status_code == 200
    payload = response.json()
    run_id = payload["run_id"]

    fetched = client.get("/runs", params={"artifacts_dir": str(tmp_path)})
    assert fetched.status_code == 200
    assert fetched.json()["runs"][0]["run_id"] == run_id

    detail = client.get(f"/runs/{run_id}", params={"artifacts_dir": str(tmp_path)})
    assert detail.status_code == 200
    assert detail.json()["run_id"] == run_id

    deliverables = client.get(f"/runs/{run_id}/deliverables", params={"artifacts_dir": str(tmp_path)})
    assert deliverables.status_code == 200
    delivery_payload = deliverables.json()
    assert delivery_payload["deliverables"]["summary"]["exists"]
    assert delivery_payload["deliverables"]["quality"]["exists"]
    assert delivery_payload["deliverables"]["pdf_report"]["exists"]
    assert delivery_payload["deliverables"]["delivery_bundle"]["exists"]
    assert delivery_payload["deliverables"]["source_score_chart"]["size_bytes"] > 0

    bundle = client.get(
        f"/runs/{run_id}/deliverables/delivery_bundle",
        params={"artifacts_dir": str(tmp_path)},
    )
    assert bundle.status_code == 200
    assert bundle.content.startswith(b"PK")

    quality = client.get(f"/runs/{run_id}/quality", params={"artifacts_dir": str(tmp_path)})
    assert quality.status_code == 200
    assert quality.json()["score"] > 0

    delivery_manifest = client.get(
        f"/runs/{run_id}/delivery-manifest",
        params={"artifacts_dir": str(tmp_path)},
    )
    assert delivery_manifest.status_code == 200
    manifest_payload = delivery_manifest.json()
    assert manifest_payload["primary"]["bundle"].endswith("delivery_bundle.zip")
    assert "summary" in manifest_payload["all"]
    assert manifest_payload["highlights"]["top_sources"]
    assert manifest_payload["highlights"]["recent_events"]

    verification = client.get(
        f"/runs/{run_id}/verify",
        params={"artifacts_dir": str(tmp_path)},
    )
    assert verification.status_code == 200
    verification_payload = verification.json()
    assert verification_payload["ready"] is True
    assert any(item["name"] == "delivery_bundle" for item in verification_payload["checks"])


def test_runs_endpoint_filters_by_task_type_and_limit(tmp_path):
    source_file = tmp_path / "funding.txt"
    source_file.write_text("2026年4月20日，星海机器人公司完成2亿元人民币融资。", encoding="utf-8")

    created_research = client.post(
        "/runs",
        json={"task": "监控AI新闻", "artifacts_dir": str(tmp_path)},
    )
    created_file = client.post(
        "/runs",
        json={"task": "分析这个文件并提取要点", "files": [str(source_file)], "artifacts_dir": str(tmp_path)},
    )
    assert created_research.status_code == 200
    assert created_file.status_code == 200

    filtered = client.get(
        "/runs",
        params={"artifacts_dir": str(tmp_path), "task_type": "file_intelligence", "limit": 1},
    )
    assert filtered.status_code == 200
    payload = filtered.json()["runs"]
    assert len(payload) == 1
    assert payload[0]["plan"]["task_type"] == "file_intelligence"


def test_api_reports_provider_configuration_errors(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = client.post(
        "/runs",
        json={
            "task": "robotics funding",
            "provider": "openai_web_research",
            "artifacts_dir": str(tmp_path),
        },
    )
    assert response.status_code == 400
    assert "OPENAI_API_KEY is required" in response.json()["detail"]


def test_watch_lifecycle_via_api(tmp_path):
    watch_file = tmp_path / "watch.txt"
    watch_file.write_text("版本一，新增融资披露", encoding="utf-8")
    watches_dir = tmp_path / "watches"
    artifacts_dir = tmp_path / "artifacts"

    created = client.post(
        "/watches",
        json={
            "name": "API Watch",
            "task": "监控 API watch",
            "files": [str(watch_file)],
            "interval_minutes": 15,
            "watches_dir": str(watches_dir),
        },
    )
    assert created.status_code == 200
    watch_id = created.json()["watch_id"]

    listed = client.get("/watches", params={"watches_dir": str(watches_dir)})
    assert listed.status_code == 200
    assert listed.json()["watches"][0]["watch_id"] == watch_id

    executed = client.post(
        f"/watches/{watch_id}/run",
        json={
            "artifacts_dir": str(artifacts_dir),
            "watches_dir": str(watches_dir),
            "force": True,
        },
    )
    assert executed.status_code == 200
    assert executed.json()["new_run_id"]

    inspected = client.get(f"/watches/{watch_id}", params={"watches_dir": str(watches_dir)})
    assert inspected.status_code == 200
    payload = inspected.json()
    assert payload["watch"]["watch_id"] == watch_id
    assert payload["last_execution"]["new_run_id"] == executed.json()["new_run_id"]
    assert payload["notification"]["deliverables"]["delivery_bundle"].endswith("delivery_bundle.zip")

    manifest = client.get(f"/watches/{watch_id}/delivery-manifest", params={"watches_dir": str(watches_dir)})
    assert manifest.status_code == 200
    manifest_payload = manifest.json()
    assert manifest_payload["latest"]["run_id"] == executed.json()["new_run_id"]
    assert manifest_payload["primary"]["delivery_bundle"].endswith("delivery_bundle.zip")
    assert manifest_payload["notification"]["title"]

    disabled = client.patch(
        f"/watches/{watch_id}",
        json={
            "enabled": False,
            "watches_dir": str(watches_dir),
        },
    )
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False

    reenabled = client.patch(
        f"/watches/{watch_id}",
        json={
            "enabled": True,
            "watches_dir": str(watches_dir),
        },
    )
    assert reenabled.status_code == 200
    assert reenabled.json()["enabled"] is True
    assert reenabled.json()["next_run_at"] is not None


def test_watch_list_filters_enabled_state_via_api(tmp_path):
    watch_file = tmp_path / "watch-enabled.txt"
    watch_file.write_text("版本一", encoding="utf-8")
    watches_dir = tmp_path / "watches"

    created = client.post(
        "/watches",
        json={
            "name": "Filtered Watch",
            "task": "监控过滤状态",
            "files": [str(watch_file)],
            "watches_dir": str(watches_dir),
        },
    )
    assert created.status_code == 200
    watch_id = created.json()["watch_id"]

    disabled = client.patch(
        f"/watches/{watch_id}",
        json={"enabled": False, "watches_dir": str(watches_dir)},
    )
    assert disabled.status_code == 200

    enabled_list = client.get("/watches", params={"watches_dir": str(watches_dir), "enabled": True})
    assert enabled_list.status_code == 200
    assert enabled_list.json()["watches"] == []

    disabled_list = client.get("/watches", params={"watches_dir": str(watches_dir), "enabled": False})
    assert disabled_list.status_code == 200
    payload = disabled_list.json()["watches"]
    assert len(payload) == 1
    assert payload[0]["watch_id"] == watch_id


def test_watch_delete_via_api(tmp_path):
    watch_file = tmp_path / "delete-api-watch.txt"
    watch_file.write_text("版本一", encoding="utf-8")
    watches_dir = tmp_path / "watches"

    created = client.post(
        "/watches",
        json={
            "name": "Delete API Watch",
            "task": "删除 API watch",
            "files": [str(watch_file)],
            "watches_dir": str(watches_dir),
        },
    )
    assert created.status_code == 200
    watch_id = created.json()["watch_id"]

    deleted = client.delete(f"/watches/{watch_id}", params={"watches_dir": str(watches_dir)})
    assert deleted.status_code == 200
    assert deleted.json()["watch_id"] == watch_id

    listed = client.get("/watches", params={"watches_dir": str(watches_dir)})
    assert listed.status_code == 200
    assert listed.json()["watches"] == []
