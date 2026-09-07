from datetime import datetime, timezone
from uuid import uuid4

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(320), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    account_status = db.Column(db.String(20), nullable=False, default="pending")
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_login = db.Column(db.DateTime(timezone=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Profile(db.Model):
    __tablename__ = "profiles"
    profile_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False)
    display_name = db.Column(db.String(80))
    bio = db.Column(db.String(500))
    avatar_url = db.Column(db.String(500))
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(40))
    theme_preference = db.Column(db.String(20), default="light")


class Journal(db.Model):
    __tablename__ = "journals"
    journal_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    visibility = db.Column(db.String(20), nullable=False, default="private")
    mood_summary = db.Column(db.String(120))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow)


class MoodEntry(db.Model):
    __tablename__ = "mood_entries"
    mood_entry_id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    journal_id = db.Column(db.String(36), db.ForeignKey("journals.journal_id", ondelete="CASCADE"), nullable=False, index=True)
    emotion = db.Column(db.String(80), nullable=False)
    stress_level = db.Column(db.Integer)
    energy_level = db.Column(db.Integer)
    sleep_hours = db.Column(db.Float)
    productivity_score = db.Column(db.Integer)
    entry_date = db.Column(db.Date, nullable=False)
