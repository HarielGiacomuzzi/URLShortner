# URL Shortener Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** FastAPI service that shortens URLs into 6-char alphanumeric codes stored in SQLite and redirects short codes to originals, deployed to Railway.

**Architecture:** Two modules. `app/db.py` owns SQLite (stdlib `sqlite3`, one table, connection per request). `app/main.py` owns HTTP: Pydantic `HttpUrl` validation, `POST /shorten`, `GET /{short_code}` redirect, CORS for the Vercel frontend. `short_url` is built from the incoming request's base URL, so no base-URL config is needed.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, stdlib `sqlite3`, pytest + httpx (`TestClient`), Railway.

**Spec:** `Exercise_requirements.md` (repo root)

## Global Constraints

- `POST /shorten` accepts `{"url": "https://..."}` and returns `{"short_code": "abc123", "short_url": "..."}`
- `GET /{short_code}` redirects to the original URL
- Storage: SQLite
- Short codes: exactly 6 characters, ASCII alphanumeric (`[A-Za-z0-9]{6}`)
- URL input validated: only `http`/`https` accepted (also blocks `javascript:` open-redirect abuse)
- Duplicate URL returns the existing short code
- Deploy target: Railway
- All backend code lives under `backend/`; run every command below from `backend/` unless stated
- Extension challenges (analytics, custom codes, expiration, QR) are OUT of scope

## File Structure

```
backend/
  app/__init__.py        # empty, makes `app` a package
  app/db.py              # SQLite: connect, generate_code, get_or_create_code, get_url
  app/main.py            # FastAPI app, routes, CORS
  tests/test_db.py       # storage unit tests
  tests/test_api.py      # HTTP tests via TestClient
  requirements.txt       # runtime deps (Railway installs this)
  requirements-dev.txt   # test deps
  pytest.ini             # puts backend/ on sys.path
  Procfile               # Railway start command
  .python-version        # pins Python for Railway
  .gitignore
```

---

### Task 1: Project scaffold + SQLite storage

**Files:**
- Create: `backend/app/__init__.py`, `backend/app/db.py`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pytest.ini`, `backend/.gitignore`, `backend/.python-version`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Consumes: nothing
- Produces (used by Task 2):
  - `db.connect() -> sqlite3.Connection` — opens `os.environ.get("DB_PATH", "urls.db")`, creates table if missing
  - `db.generate_code() -> str` — random 6-char `[A-Za-z0-9]`
  - `db.get_or_create_code(conn: sqlite3.Connection, url: str) -> str`
  - `db.get_url(conn: sqlite3.Connection, code: str) -> str | None`

- [ ] **Step 1: Scaffold project and install deps**

`backend/requirements.txt`:
```
fastapi>=0.115
uvicorn[standard]>=0.30
```

`backend/requirements-dev.txt`:
```
pytest>=8
httpx>=0.27
```

`backend/pytest.ini`:
```ini
[pytest]
pythonpath = .
testpaths = tests
```

`backend/.python-version`:
```
3.12
```

`backend/.gitignore`:
```
.venv/
__pycache__/
.pytest_cache/
*.db
```

`backend/app/__init__.py`: empty file.

Run:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```
Expected: installs without errors.

- [ ] **Step 2: Write the failing tests**

`backend/tests/test_db.py`:
```python
import pytest

from app import db


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    c = db.connect()
    yield c
    c.close()


def test_generate_code_is_six_ascii_alphanumeric():
    code = db.generate_code()
    assert len(code) == 6
    assert code.isascii() and code.isalnum()


def test_same_url_returns_same_code(conn):
    first = db.get_or_create_code(conn, "https://example.com/")
    second = db.get_or_create_code(conn, "https://example.com/")
    assert first == second


def test_different_urls_get_different_codes(conn):
    a = db.get_or_create_code(conn, "https://a.com/")
    b = db.get_or_create_code(conn, "https://b.com/")
    assert a != b


def test_get_url_round_trip(conn):
    code = db.get_or_create_code(conn, "https://example.com/page")
    assert db.get_url(conn, code) == "https://example.com/page"


def test_get_url_unknown_code_returns_none(conn):
    assert db.get_url(conn, "nope00") is None


def test_retries_on_code_collision(conn, monkeypatch):
    codes = iter(["AAAAAA", "AAAAAA", "BBBBBB"])
    monkeypatch.setattr(db, "generate_code", lambda: next(codes))
    assert db.get_or_create_code(conn, "https://a.com/") == "AAAAAA"
    # second URL collides on AAAAAA first, must retry and get BBBBBB
    assert db.get_or_create_code(conn, "https://b.com/") == "BBBBBB"
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL / collection error — `ImportError: cannot import name 'db' from 'app'`.

- [ ] **Step 4: Write minimal implementation**

`backend/app/db.py`:
```python
import os
import secrets
import sqlite3
import string

ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 6
MAX_ATTEMPTS = 10


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(os.environ.get("DB_PATH", "urls.db"))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS urls ("
        "code TEXT PRIMARY KEY, "
        "url TEXT NOT NULL UNIQUE)"
    )
    return conn


def generate_code() -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(CODE_LENGTH))


def get_or_create_code(conn: sqlite3.Connection, url: str) -> str:
    # Loop covers both races: code collision (retry new code) and a concurrent
    # insert of the same URL (the re-SELECT at the top then finds it).
    for _ in range(MAX_ATTEMPTS):
        row = conn.execute("SELECT code FROM urls WHERE url = ?", (url,)).fetchone()
        if row:
            return row[0]
        code = generate_code()
        try:
            with conn:
                conn.execute("INSERT INTO urls (code, url) VALUES (?, ?)", (code, url))
            return code
        except sqlite3.IntegrityError:
            continue
    raise RuntimeError("Could not allocate a unique short code")


def get_url(conn: sqlite3.Connection, code: str) -> str | None:
    row = conn.execute("SELECT url FROM urls WHERE code = ?", (code,)).fetchone()
    return row[0] if row else None
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat(backend): add SQLite storage for short codes"
```

---

### Task 2: HTTP API (`POST /shorten`, `GET /{short_code}`, CORS)

**Files:**
- Create: `backend/app/main.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `db.connect`, `db.get_or_create_code`, `db.get_url` from Task 1
- Produces (used by frontend plan and Task 3):
  - `app.main:app` — ASGI app
  - `POST /shorten` body `{"url": str}` → 200 `{"short_code": str, "short_url": str}`; invalid URL → 422
  - `GET /{short_code}` → 307 with `Location: <original url>`; unknown → 404 `{"detail": "Short URL not found"}`
  - `GET /health` → 200 `{"status": "ok"}`
  - Env: `DB_PATH` (default `urls.db`), `ALLOWED_ORIGINS` (comma-separated, default `*`)

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_api.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_api.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'`.

- [ ] **Step 3: Write minimal implementation**

`backend/app/main.py`:
```python
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from app import db

app = FastAPI(title="URL Shortener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("ALLOWED_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


class ShortenRequest(BaseModel):
    url: HttpUrl  # http/https only, max 2083 chars


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/shorten", response_model=ShortenResponse)
def shorten(body: ShortenRequest, request: Request):
    conn = db.connect()
    try:
        code = db.get_or_create_code(conn, str(body.url))
    finally:
        conn.close()
    return ShortenResponse(short_code=code, short_url=f"{request.base_url}{code}")


# Must stay the LAST route: it matches any single path segment.
@app.get("/{short_code}")
def redirect(short_code: str):
    conn = db.connect()
    try:
        url = db.get_url(conn, short_code)
    finally:
        conn.close()
    if url is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(url)
```

Note: `str(HttpUrl("https://example.com"))` normalizes to `"https://example.com/"`. That is fine and makes dedupe consistent.

- [ ] **Step 4: Run all tests to verify they pass**

Run: `python -m pytest -v`
Expected: all tests in `test_db.py` and `test_api.py` pass.

- [ ] **Step 5: Smoke-test locally**

Run in one terminal: `uvicorn app.main:app --reload --port 8000`
In another:
```bash
curl -s -X POST localhost:8000/shorten -H 'content-type: application/json' -d '{"url":"https://example.com"}'
# => {"short_code":"XXXXXX","short_url":"http://localhost:8000/XXXXXX"}
curl -si localhost:8000/XXXXXX | head -3
# => HTTP/1.1 307 Temporary Redirect ... location: https://example.com/
```
Also open `http://localhost:8000/docs`: Swagger UI must load. FastAPI registers `/docs` before user routes, so the catch-all does not shadow it.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat(backend): add shorten and redirect endpoints"
```

---

### Task 3: Deploy backend to Railway

**Files:**
- Create: `backend/Procfile`

**Interfaces:**
- Consumes: `app.main:app`, env vars `DB_PATH`, `ALLOWED_ORIGINS` from Task 2
- Produces: public backend URL, e.g. `https://<service>.up.railway.app`. The frontend plan puts it in `NEXT_PUBLIC_API_URL`.

- [ ] **Step 1: Add start command**

`backend/Procfile`:
```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips '*'
```
`--proxy-headers` makes `request.base_url` use `https` behind Railway's proxy. Without it, `short_url` would come out as `http://...`.

- [ ] **Step 2: Commit and push**

```bash
git add backend/Procfile
git commit -m "chore(backend): add Railway start command"
git push
```

- [ ] **Step 3: Create the Railway service (dashboard)**

1. railway.com → New Project → Deploy from GitHub repo → pick this repo.
2. Service → Settings → **Root Directory** = `backend`.
3. Service → **Volumes** → Add volume, mount path `/data`. Without it, SQLite is wiped on every redeploy.
4. Service → **Variables**:
   - `DB_PATH=/data/urls.db`
   - `ALLOWED_ORIGINS=*` (tighten to the Vercel URL in the frontend plan's deploy task)
5. Settings → Networking → **Generate Domain**.
6. Wait for the deploy to show "Active".

- [ ] **Step 4: Verify the deployment**

```bash
API=https://<your-service>.up.railway.app
curl -s $API/health
# => {"status":"ok"}
curl -s -X POST $API/shorten -H 'content-type: application/json' -d '{"url":"https://example.com"}'
# => short_url must start with https://<your-service>.up.railway.app/
curl -si $API/<code> | head -3
# => 307, location: https://example.com/
```
If `short_url` starts with `http://`, the Procfile flags were not applied. Check Settings → Deploy → Custom Start Command is empty so the Procfile is used.

- [ ] **Step 5: Record the URL**

Save the Railway URL. The frontend plan needs it.
