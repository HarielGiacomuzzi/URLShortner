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
