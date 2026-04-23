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
