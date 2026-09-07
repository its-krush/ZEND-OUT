import os

import pytest

os.environ["EMAIL_VERIFICATION_REQUIRED"] = "false"

from app import create_app
from app.extensions import db
from app.models import User


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
