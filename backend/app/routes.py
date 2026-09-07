import os
import secrets
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request, session
from flask_wtf.csrf import generate_csrf
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import or_

from .extensions import csrf, db, limiter
from .models import Journal, Profile, User

api = Blueprint("api", __name__)


def serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="zendout-email-verification")


def send_verification_email(email, token):
    server = os.environ.get("MAIL_SERVER")
    if not server:
        current_app.logger.warning("MAIL_SERVER is not configured; verification email not sent")
        return
    link = f"{request.host_url.rstrip('/')}/api/auth/verify-email?token={token}"
    msg = EmailMessage()
    msg["Subject"] = "Verify your Zen'd Out email"
    msg["From"] = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@example.com")
    msg["To"] = email
    msg.set_content(f"Verify your email by opening: {link}\nThis link expires in 24 hours.")
    with smtplib.SMTP(server, int(os.environ.get("MAIL_PORT", "587")), timeout=10) as smtp:
        smtp.starttls()
        username = os.environ.get("MAIL_USERNAME")
        if username:
            smtp.login(username, os.environ.get("MAIL_PASSWORD", ""))
        smtp.send_message(msg)


def current_user():
    user_id = session.get("user_id")
    return User.query.get(user_id) if user_id else None


@api.get("/health")
def health():
    return jsonify(status="ok")


@api.get("/csrf-token")
def csrf_token():
    return jsonify(csrf_token=generate_csrf())


@api.post("/auth/register")
@limiter.limit("5 per hour")
def register():
    data = request.get_json(silent=True) or {}
    username, email, password = str(data.get("username", "")).strip(), str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
    if not (3 <= len(username) <= 32) or not username.replace("_", "").isalnum():
        return jsonify(error="invalid_username"), 400
    try:
        email = validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError:
        return jsonify(error="invalid_email"), 400
    if len(password) < 12:
        return jsonify(error="password_must_be_at_least_12_characters"), 400
    if User.query.filter(or_(User.username == username, User.email == email)).first():
        return jsonify(error="username_or_email_already_exists"), 409
    user = User(username=username, email=email, account_status="pending", is_verified=False)
    user.set_password(password)
    db.session.add(user)
    db.session.flush()
    db.session.add(Profile(user_id=user.user_id, display_name=username))
    db.session.commit()
    token = serializer().dumps({"user_id": user.user_id, "nonce": secrets.token_urlsafe(16)})
    try:
        send_verification_email(email, token)
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Verification email delivery failed")
    return jsonify(message="account_created_check_email"), 201


@api.get("/auth/verify-email")
def verify_email():
    try:
        payload = serializer().loads(request.args.get("token", ""), max_age=86400)
    except (BadSignature, SignatureExpired):
        return jsonify(error="invalid_or_expired_verification_token"), 400
    user = User.query.get(payload.get("user_id"))
    if not user:
        return jsonify(error="invalid_verification_token"), 400
    user.is_verified, user.account_status = True, "active"
    db.session.commit()
    return jsonify(message="email_verified")


@api.post("/auth/login")
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}
    identifier, password = str(data.get("identifier", "")).strip().lower(), str(data.get("password", ""))
    user = User.query.filter(or_(User.email == identifier, User.username == identifier)).first()
    if not user or not user.check_password(password):
        return jsonify(error="invalid_credentials"), 401
    if os.environ.get("EMAIL_VERIFICATION_REQUIRED", "true").lower() == "true" and not user.is_verified:
        return jsonify(error="email_not_verified"), 403
    session.clear()
    session.permanent, session["user_id"] = True, user.user_id
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(username=user.username, email=user.email)


@api.post("/auth/logout")
@csrf.exempt
def logout():
    session.clear()
    return jsonify(message="logged_out")


@api.get("/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    return jsonify(user_id=user.user_id, username=user.username, email=user.email, verified=user.is_verified)


@api.get("/journals")
def journals():
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    rows = Journal.query.filter_by(user_id=user.user_id).order_by(Journal.updated_at.desc()).all()
    return jsonify([{"id": j.journal_id, "title": j.title, "content": j.content, "visibility": j.visibility} for j in rows])


@api.post("/journals")
def create_journal():
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    data = request.get_json(silent=True) or {}
    title, content = str(data.get("title", "")).strip(), str(data.get("content", ""))
    if not title or len(title) > 200 or len(content) > 100000:
        return jsonify(error="invalid_journal"), 400
    journal = Journal(user_id=user.user_id, title=title, content=content, visibility=data.get("visibility", "private"))
    db.session.add(journal)
    db.session.commit()
    return jsonify(id=journal.journal_id), 201
