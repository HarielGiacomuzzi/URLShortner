# URL Shortener

A small full-stack URL shortener: paste a long URL, get a 6-character short link back, and the link redirects to the original.

- **Backend:** Python + FastAPI, SQLite storage — deployed to [Railway](https://railway.com)
- **Frontend:** TypeScript + Next.js + Tailwind CSS — deployed to [Vercel](https://vercel.com)

Built as the "Vibe Coding Introduction" lab exercise (see [`Exercise_requirements.md`](Exercise_requirements.md)).

```
User ──▶ Next.js frontend ──POST /shorten──▶ FastAPI backend ──▶ SQLite
                                                   │
User ──── visits short URL ──── GET /{code} ───────┘──▶ 307 redirect to original URL
```

## Features

- `POST /shorten` turns a URL into a 6-character alphanumeric code (`[A-Za-z0-9]{6}`)
- `GET /{code}` redirects (307) to the original URL, or returns 404 for unknown codes
- The same URL always gets the same code back (duplicates are detected)
- Input validation: only `http://` and `https://` URLs are accepted (max 2083 chars), which also blocks `javascript:` redirect abuse
- Codes come from a cryptographically secure random source; collisions are retried automatically
- Single-page UI with a loading state, copy-to-clipboard button, friendly error messages, and a responsive layout (works down to phone width)

## Repository layout

```
backend/                 FastAPI service
  app/db.py              SQLite storage: code generation, lookup, dedupe
  app/main.py            HTTP routes + CORS
  tests/                 pytest suite (storage + API)
  Procfile               Railway start command
frontend/                Next.js app
  app/page.tsx           The shortener page
  lib/api.ts             API client (fetch + error mapping)
  lib/api.test.ts        Vitest suite for the API client
docs/superpowers/plans/  Implementation plans used to build the project
```

## Running locally

Prerequisites: Python 3.12+ and Node.js 20+.

### 1. Backend (http://localhost:8000)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

### 2. Frontend (http://localhost:3000)

In a second terminal:

```bash
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
npm run dev
```

Open http://localhost:3000, paste a URL, and click **Shorten**.

## Testing

```bash
# Backend — 17 tests (storage, endpoints, validation, redirects, CORS)
cd backend && source .venv/bin/activate && python -m pytest -v

# Frontend — API client tests, plus lint and a production build
cd frontend && npm test && npm run lint && npm run build
```

## API reference

### `POST /shorten`

Request:

```json
{ "url": "https://example.com/some/very/long/path" }
```

Response `200`:

```json
{ "short_code": "AbUTnA", "short_url": "https://<backend-host>/AbUTnA" }
```

Errors: `422` if `url` is missing or isn't a valid `http`/`https` URL.

```bash
curl -X POST http://localhost:8000/shorten \
  -H 'content-type: application/json' \
  -d '{"url":"https://example.com"}'
```

### `GET /{short_code}`

- `307 Temporary Redirect` with `Location: <original URL>`
- `404 {"detail": "Short URL not found"}` for unknown codes

### `GET /health`

Returns `{"status": "ok"}`. Useful for deploy health checks.

## Configuration

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `DB_PATH` | backend | `urls.db` | SQLite database file path |
| `ALLOWED_ORIGINS` | backend | `*` | Comma-separated list of origins allowed by CORS |
| `PORT` | backend | set by Railway | Port uvicorn listens on (used in `Procfile`) |
| `NEXT_PUBLIC_API_URL` | frontend | `http://localhost:8000` | Backend base URL (a trailing slash is fine) |

`short_url` is built from the host the request came in on, so the backend doesn't need a "base URL" setting.

## Deployment

### Backend on Railway

1. **New Project → Deploy from GitHub repo**, and pick this repository.
2. Service **Settings → Root Directory**: `backend`.
3. **Volumes → Add volume** mounted at `/data`. Without it, SQLite is wiped on every redeploy.
4. **Variables**:
   - `DB_PATH=/data/urls.db`
   - `ALLOWED_ORIGINS=*` for now (you'll lock this down after the frontend is live)
5. **Settings → Networking → Generate Domain**.
6. Verify:
   ```bash
   API=https://<your-service>.up.railway.app
   curl -s $API/health                      # {"status":"ok"}
   curl -s -X POST $API/shorten -H 'content-type: application/json' \
     -d '{"url":"https://example.com"}'     # short_url must start with https://
   ```

The `Procfile` runs uvicorn with `--proxy-headers`. Without it, short URLs behind Railway's proxy would start with `http://`.

### Frontend on Vercel

1. **Add New → Project**, and import this repository.
2. **Root Directory**: `frontend`. Vercel detects the Next.js framework on its own.
3. **Environment Variables**: `NEXT_PUBLIC_API_URL=https://<your-service>.up.railway.app`
4. Deploy.

> `NEXT_PUBLIC_API_URL` is baked in at **build time**. Set it before the first build, and redeploy after changing it. If it's missing, the app falls back to `http://localhost:8000` and shows "Could not reach the server".

### Lock down CORS

Back in Railway, set `ALLOWED_ORIGINS=https://<your-project>.vercel.app` (scheme included, no trailing slash). Railway redeploys automatically. Then open the Vercel URL, shorten a link, and follow it.

## Design notes and known limitations

- **SQLite with a connection per request.** Simple and fine for this scale. For many instances or heavy traffic, switch to Postgres.
- **Codes are random, not sequential.** There are 62⁶ ≈ 56.8 billion possible codes, so a collision is retried and practically never happens.
- **`/health` is a reserved path.** In the roughly 1-in-57-billion case that a generated code is `health`, that code wouldn't redirect.
- **Out of scope** (the exercise's extension challenges): click analytics, custom codes, expiring links, and QR codes.

## License

[Apache 2.0](LICENSE)
