import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from hashlib import sha256

from email_validator import EmailNotValidError, validate_email
from flask import Blueprint, current_app, jsonify, request, session
from flask_wtf.csrf import generate_csrf
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import func, or_

from .extensions import csrf, db, limiter
from .models import Comment, Follow, Journal, Like, PasswordResetToken, Post, Profile, User

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


def send_password_reset_email(email, raw_token):
    server = os.environ.get("MAIL_SERVER")
    if not server:
        current_app.logger.warning("MAIL_SERVER is not configured; password reset email not sent")
        return
    base_url = os.environ.get("FRONTEND_BASE_URL", request.host_url.rstrip("/"))
    link = f"{base_url}/reset-password.html?token={raw_token}"
    msg = EmailMessage()
    msg["Subject"] = "Reset your Zen'd Out password"
    msg["From"] = os.environ.get("MAIL_DEFAULT_SENDER", "no-reply@example.com")
    msg["To"] = email
    msg.set_content(f"Reset your password by opening: {link}\nThis link expires in 30 minutes and can only be used once.")
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
    username, email, password = str(data.get("username", "")).strip().lower(), str(data.get("email", "")).strip().lower(), str(data.get("password", ""))
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
    user = User.query.filter(or_(User.email == identifier, func.lower(User.username) == identifier)).first()
    if not user or not user.check_password(password):
        return jsonify(error="invalid_credentials"), 401
    if os.environ.get("EMAIL_VERIFICATION_REQUIRED", "true").lower() == "true" and not user.is_verified:
        return jsonify(error="email_not_verified"), 403
    session.clear()
    session.permanent, session["user_id"] = True, user.user_id
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()
    return jsonify(username=user.username, email=user.email)


@api.post("/auth/forgot-password")
@limiter.limit("5 per hour")
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    generic = {"message": "If an account exists for that email, a reset link has been sent."}
    try:
        email = validate_email(email, check_deliverability=False).normalized
    except EmailNotValidError:
        return jsonify(generic)
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify(generic)
    raw_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    db.session.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.user_id,
        PasswordResetToken.used_at.is_(None),
    ).update({"used_at": now})
    db.session.add(PasswordResetToken(
        user_id=user.user_id,
        token_hash=sha256(raw_token.encode()).hexdigest(),
        expires_at=now + timedelta(minutes=30),
    ))
    db.session.commit()
    try:
        send_password_reset_email(user.email, raw_token)
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Password reset email delivery failed")
    return jsonify(generic)


@api.post("/auth/reset-password")
@limiter.limit("10 per hour")
def reset_password():
    data = request.get_json(silent=True) or {}
    raw_token, password = str(data.get("token", "")), str(data.get("password", ""))
    if len(password) < 12 or not raw_token:
        return jsonify(error="invalid_reset_request"), 400
    token = PasswordResetToken.query.filter_by(token_hash=sha256(raw_token.encode()).hexdigest()).first()
    now = datetime.now(timezone.utc)
    expires_at = token.expires_at.replace(tzinfo=timezone.utc) if token and token.expires_at.tzinfo is None else (token.expires_at if token else None)
    if not token or token.used_at is not None or expires_at <= now:
        return jsonify(error="invalid_or_expired_reset_token"), 400
    user = User.query.get(token.user_id)
    if not user:
        return jsonify(error="invalid_or_expired_reset_token"), 400
    user.set_password(password)
    token.used_at = now
    db.session.commit()
    return jsonify(message="password_reset")


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
    return jsonify([{"id": j.journal_id, "title": j.title, "content": j.content, "visibility": j.visibility, "isPublic": j.visibility == "public", "date": j.created_at.strftime("%b %d, %Y"), "mood": j.mood_summary or "default"} for j in rows])


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


@api.patch("/journals/<journal_id>")
def update_journal(journal_id):
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    journal = Journal.query.filter_by(journal_id=journal_id, user_id=user.user_id).first()
    if not journal:
        return jsonify(error="not_found"), 404
    data = request.get_json(silent=True) or {}
    title, content = str(data.get("title", "")).strip(), str(data.get("content", ""))
    if not title or len(title) > 200 or len(content) > 100000:
        return jsonify(error="invalid_journal"), 400
    journal.title, journal.content = title, content
    journal.visibility = data.get("visibility", journal.visibility)
    db.session.commit()
    return jsonify(id=journal.journal_id)


@api.delete("/journals/<journal_id>")
def delete_journal(journal_id):
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    journal = Journal.query.filter_by(journal_id=journal_id, user_id=user.user_id).first()
    if not journal:
        return jsonify(error="not_found"), 404
    db.session.delete(journal)
    db.session.commit()
    return jsonify(message="deleted")


def ensure_post_for_journal(journal):
    post = Post.query.filter_by(journal_id=journal.journal_id).first()
    if not post:
        post = Post(post_id=journal.journal_id, user_id=journal.user_id, journal_id=journal.journal_id, caption=journal.content, visibility=journal.visibility)
        db.session.add(post)
        db.session.flush()
    return post


@api.get("/social/feed")
def social_feed():
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    journals = Journal.query.filter_by(visibility="public").order_by(Journal.created_at.desc()).all()
    result = []
    for journal in journals:
        post = ensure_post_for_journal(journal)
        author = User.query.get(journal.user_id)
        result.append({"id": post.post_id, "user": author.username, "title": journal.title, "content": journal.content, "date": journal.created_at.strftime("%b %d, %Y"), "isPublic": True, "like_count": Like.query.filter_by(post_id=post.post_id).count(), "comment_count": Comment.query.filter_by(post_id=post.post_id).count()})
    db.session.commit()
    return jsonify(result)


@api.get("/social/users")
def social_users():
    user = current_user()
    if not user:
        return jsonify(error="unauthorized"), 401
    return jsonify([{"username": other.username, "public_posts": Journal.query.filter_by(user_id=other.user_id, visibility="public").count(), "following": Follow.query.filter_by(follower_id=user.user_id, following_id=other.user_id).first() is not None} for other in User.query.filter(User.user_id != user.user_id).order_by(User.username).all()])


@api.post("/social/follow/<username>")
def toggle_follow(username):
    user = current_user()
    target = User.query.filter_by(username=username).first()
    if not user or not target or target.user_id == user.user_id:
        return jsonify(error="not_found"), 404
    follow = Follow.query.filter_by(follower_id=user.user_id, following_id=target.user_id).first()
    if follow:
        db.session.delete(follow)
        following = False
    else:
        db.session.add(Follow(follower_id=user.user_id, following_id=target.user_id))
        following = True
    db.session.commit()
    return jsonify(following=following)


@api.post("/social/posts/<post_id>/like")
def toggle_like(post_id):
    user = current_user()
    if not user or not Post.query.get(post_id):
        return jsonify(error="not_found"), 404
    like = Like.query.filter_by(post_id=post_id, user_id=user.user_id).first()
    if like:
        db.session.delete(like)
        liked = False
    else:
        db.session.add(Like(post_id=post_id, user_id=user.user_id))
        liked = True
    db.session.commit()
    return jsonify(liked=liked, count=Like.query.filter_by(post_id=post_id).count())


@api.get("/social/posts/<post_id>/comments")
def list_comments(post_id):
    if not current_user() or not Post.query.get(post_id):
        return jsonify(error="not_found"), 404
    return jsonify([{"user": User.query.get(c.user_id).username, "text": c.comment_text, "date": c.created_at.strftime("%b %d, %Y")} for c in Comment.query.filter_by(post_id=post_id).order_by(Comment.created_at).all()])


@api.post("/social/posts/<post_id>/comments")
def create_comment(post_id):
    user = current_user()
    if not user or not Post.query.get(post_id):
        return jsonify(error="not_found"), 404
    text = str((request.get_json(silent=True) or {}).get("text", "")).strip()
    if not text or len(text) > 2000:
        return jsonify(error="invalid_comment"), 400
    db.session.add(Comment(post_id=post_id, user_id=user.user_id, comment_text=text))
    db.session.commit()
    return jsonify(message="comment_created"), 201
