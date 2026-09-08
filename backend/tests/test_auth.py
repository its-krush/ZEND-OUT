import os

import pytest

os.environ["EMAIL_VERIFICATION_REQUIRED"] = "false"

from app import create_app
from app.extensions import db
from app.models import PasswordResetToken, User
import app.routes as routes


@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "WTF_CSRF_ENABLED": False, "SQLALCHEMY_DATABASE_URI": f"sqlite:///{tmp_path}/test.db", "SECRET_KEY": "test-secret"})
    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client


def test_health(client):
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_registration_hashes_password_and_login(client):
    response = client.post("/api/auth/register", json={"username": "tester", "email": "tester@example.com", "password": "correct horse battery staple"})
    assert response.status_code == 201
    with client.application.app_context():
        user = User.query.filter_by(username="tester").one()
        assert user.password_hash != "correct horse battery staple"
        assert user.check_password("correct horse battery staple")
    response = client.post("/api/auth/login", json={"identifier": "tester", "password": "correct horse battery staple"})
    assert response.status_code == 200


def test_weak_password_rejected(client):
    response = client.post("/api/auth/register", json={"username": "tester", "email": "tester@example.com", "password": "short"})
    assert response.status_code == 400
    assert response.get_json()["error"] == "password_must_be_at_least_12_characters"


def test_password_reset_is_single_use(client, monkeypatch):
    client.post("/api/auth/register", json={"username": "tester", "email": "tester@example.com", "password": "correct horse battery staple"})
    sent = {}
    monkeypatch.setattr(routes, "send_password_reset_email", lambda email, token: sent.update(token=token))
    response = client.post("/api/auth/forgot-password", json={"email": "tester@example.com"})
    assert response.status_code == 200
    assert "If an account exists" in response.get_json()["message"]
    token = sent["token"]
    response = client.post("/api/auth/reset-password", json={"token": token, "password": "new correct horse battery"})
    assert response.status_code == 200
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "another correct password"}).status_code == 400
    assert client.post("/api/auth/login", json={"identifier": "TESTER", "password": "new correct horse battery"}).status_code == 200


def test_journal_ownership_is_enforced(client):
    client.post("/api/auth/register", json={"username": "owner", "email": "owner@example.com", "password": "correct horse battery staple"})
    client.post("/api/auth/login", json={"identifier": "owner", "password": "correct horse battery staple"})
    journal_id = client.post("/api/journals", json={"title": "Private", "content": "secret"}).get_json()["id"]
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"username": "other", "email": "other@example.com", "password": "correct horse battery staple"})
    client.post("/api/auth/login", json={"identifier": "other", "password": "correct horse battery staple"})
    assert all(item["id"] != journal_id for item in client.get("/api/journals").get_json())
    assert client.delete(f"/api/journals/{journal_id}").status_code == 404
