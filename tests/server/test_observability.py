from fastapi.testclient import TestClient

from opencontext.cli import app


class _StubProcMgr:
    def get_all_processors(self):
        return {}


class _StubConsumption:
    def get_scheduled_tasks_status(self):
        return {"enabled": False, "active_timers": []}


class _StubOC:
    def __init__(self):
        self.processor_manager = _StubProcMgr()
        self.consumption_manager = _StubConsumption()


def _prepare_app_state():
    # Prevent heavy initialization in tests
    app.state.context_lab_instance = _StubOC()


def test_healthz_endpoint_available():
    _prepare_app_state()
    client = TestClient(app)
    resp = client.get("/healthz")
    assert resp.status_code in (200, 503)
    data = resp.json()
    assert "data" in data
    assert "components" in data["data"]
    assert "database" in data["data"]["components"]


def test_metrics_endpoint_exposes_prometheus():
    _prepare_app_state()
    client = TestClient(app)

    # Trigger a request to increment counters
    client.get("/healthz")

    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus text format content type
    assert "text/plain" in resp.headers.get("content-type", "")

    body = resp.text
    assert "http_requests_total" in body
    assert "pipeline_stage_duration_seconds" in body  # exported even if zero
