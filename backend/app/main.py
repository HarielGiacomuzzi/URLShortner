import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl

from app import db

app = FastAPI(title="URL Shortener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
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
