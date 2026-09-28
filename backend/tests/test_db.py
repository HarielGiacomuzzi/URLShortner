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
