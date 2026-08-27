from __future__ import annotations

import time

from app.core import security


def test_correct_credentials_accepted(monkeypatch):
    monkeypatch.setattr(security.settings, "admin_username", "admin")
    monkeypatch.setattr(security.settings, "admin_password", "supersecret")
    assert security.verify_credentials("admin", "supersecret") is True


def test_wrong_password_rejected(monkeypatch):
    monkeypatch.setattr(security.settings, "admin_username", "admin")
    monkeypatch.setattr(security.settings, "admin_password", "supersecret")
    assert security.verify_credentials("admin", "wrong") is False


def test_wrong_username_rejected(monkeypatch):
    monkeypatch.setattr(security.settings, "admin_username", "admin")
    monkeypatch.setattr(security.settings, "admin_password", "supersecret")
    assert security.verify_credentials("someone_else", "supersecret") is False


def test_session_token_round_trip():
    token = security.create_session_token("admin")
    username = security.read_session_token(token)
    assert username == "admin"


def test_tampered_session_token_rejected():
    token = security.create_session_token("admin")
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    assert security.read_session_token(tampered) is None


def test_expired_session_token_rejected(monkeypatch):
    monkeypatch.setattr(security, "SESSION_MAX_AGE_SECONDS", 0)
    token = security.create_session_token("admin")
    time.sleep(1)
    assert security.read_session_token(token) is None
