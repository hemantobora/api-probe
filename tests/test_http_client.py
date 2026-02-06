from types import SimpleNamespace

import requests

from api_probe.http.client import HTTPClient


class DummyResponse(SimpleNamespace):
    """Minimal Response-like object for testing."""


def test_http_client_single_success(monkeypatch):
    client = HTTPClient()

    dummy = DummyResponse(
        status_code=200,
        headers={"X-Test": "1"},
        text="ok",
        elapsed=SimpleNamespace(total_seconds=lambda: 0.123),
    )

    def fake_request(self, **kwargs):  # noqa: ARG001
        return dummy

    monkeypatch.setattr(requests.Session, "request", fake_request)

    resp = client.execute({"method": "GET", "url": "https://example.com"})

    assert resp.status_code == 200
    assert hasattr(resp, "elapsed_ms")
    assert resp.elapsed_ms == int(0.123 * 1000)


def test_http_client_retry_then_success(monkeypatch):
    client = HTTPClient()

    dummy = DummyResponse(
        status_code=200,
        headers={},
        text="ok",
        elapsed=SimpleNamespace(total_seconds=lambda: 0.0),
    )

    calls = {"count": 0}

    def flaky_request(self, **kwargs):  # noqa: ARG001
        calls["count"] += 1
        if calls["count"] == 1:
            raise requests.RequestException("boom")
        return dummy

    monkeypatch.setattr(requests.Session, "request", flaky_request)

    resp = client.execute(
        {"method": "GET", "url": "https://example.com"},
        retry={"max_attempts": 2, "delay": 0},
    )

    assert resp.status_code == 200
    assert calls["count"] == 2


def test_http_client_retry_exhausted(monkeypatch):
    client = HTTPClient()

    def always_fail(self, **kwargs):  # noqa: ARG001
        raise requests.RequestException("boom")

    monkeypatch.setattr(requests.Session, "request", always_fail)

    try:
        client.execute(
            {"method": "GET", "url": "https://example.com"},
            retry={"max_attempts": 2, "delay": 0},
        )
        assert False, "Expected RequestException"
    except requests.RequestException:
        pass
