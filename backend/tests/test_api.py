import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_shorten_returns_code_and_short_url(client):
    res = client.post("/shorten", json={"url": "https://example.com/some/long/path"})
    assert res.status_code == 200
    body = res.json()
    assert re.fullmatch(r"[A-Za-z0-9]{6}", body["short_code"])
    assert body["short_url"] == f"http://testserver/{body['short_code']}"


def test_shorten_duplicate_url_returns_same_code(client):
    first = client.post("/shorten", json={"url": "https://example.com/"}).json()
    second = client.post("/shorten", json={"url": "https://example.com/"}).json()
    assert first["short_code"] == second["short_code"]


@pytest.mark.parametrize(
    "payload",
    [
        {"url": "not-a-url"},
        {"url": "ftp://example.com/file"},
        {"url": "javascript:alert(1)"},
        {"url": ""},
        {},
    ],
)
def test_shorten_rejects_invalid_input(client, payload):
    assert client.post("/shorten", json=payload).status_code == 422


def test_redirect_to_original_url(client):
    code = client.post("/shorten", json={"url": "https://example.com/target"}).json()["short_code"]
    res = client.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == "https://example.com/target"


def test_redirect_unknown_code_404(client):
    res = client.get("/zzzzzz", follow_redirects=False)
    assert res.status_code == 404
    assert res.json() == {"detail": "Short URL not found"}


def test_cors_allows_frontend_origin(client):
    res = client.options(
        "/shorten",
        headers={
            "Origin": "https://my-frontend.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert "access-control-allow-origin" in res.headers
