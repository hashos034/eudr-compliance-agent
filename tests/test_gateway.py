"""The HTTP API, with the agent run replaced by a fake. No LLM calls."""

import pytest
from fastapi.testclient import TestClient

from eudr.gateway import app as gateway
from eudr.review.store import CheckStore
from tests.test_review import FakeSummarizer, awaiting_review

KEY = {"X-API-Key": "test-key"}
SHIPMENT = {"shipment_id": "SHP-T", "supplier_ids": ["SUP-001"], "plot_ids": ["P01"]}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("EUDR_API_KEY", "test-key")
    store = CheckStore(tmp_path)
    gateway.app.dependency_overrides[gateway.get_store] = lambda: store
    yield TestClient(gateway.app), store
    gateway.app.dependency_overrides.clear()


def test_requests_without_the_right_key_are_refused(client):
    http, _ = client
    assert http.get("/checks").status_code == 401
    assert http.get("/checks", headers={"X-API-Key": "wrong"}).status_code == 401


def test_start_check_returns_at_once_and_runs_in_the_background(client, monkeypatch):
    http, store = client
    ran = []

    async def fake_run(store, record):
        ran.append(record.check_id)

    monkeypatch.setattr(gateway.service, "run", fake_run)
    response = http.post("/checks", json=SHIPMENT, headers=KEY)
    assert response.status_code == 202
    assert response.json()["status"] == "running"
    assert ran == [response.json()["check_id"]]


def test_unknown_ids_are_rejected_before_any_agent_runs(client):
    http, store = client
    response = http.post("/checks", json={**SHIPMENT, "plot_ids": ["P99"]}, headers=KEY)
    assert response.status_code == 422
    assert store.list() == []


def test_review_flow_over_http(client, monkeypatch):
    http, store = client
    _, check_id = awaiting_review(store.root)
    monkeypatch.setattr(gateway.service.dds, "write_summary", FakeSummarizer())

    assert http.get(f"/checks/{check_id}/dds", headers=KEY).status_code == 404
    view = http.get(f"/checks/{check_id}", headers=KEY).json()
    assert "Rogério" in view["result"]["suppliers"][1]["explanation"]

    response = http.post(f"/checks/{check_id}/approve", json={"reviewer": "A. Reviewer"}, headers=KEY)
    assert response.json()["status"] == "approved"
    assert "SHP-2026-003" in http.get(f"/checks/{check_id}/dds", headers=KEY).text

    again = http.post(f"/checks/{check_id}/reject", json={"reviewer": "B", "reason": "x"}, headers=KEY)
    assert again.status_code == 409


def test_missing_check_is_404(client):
    http, _ = client
    assert http.get("/checks/chk-nope", headers=KEY).status_code == 404
