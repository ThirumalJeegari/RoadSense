from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import time

from app.core.config import get_settings
from app.services.database import SessionLocal, User


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_user(payload: dict) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    _validate_credentials(email, password)
    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("Account not found. Please sign up first.")
        if not hmac.compare_digest(saved_user.password_hash, _password_hash(password)):
            raise ValueError("Invalid email or password.")

        user = _user_payload(saved_user)
    return _auth_response(user)


def signup_user(payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", ""))

    if len(name) < 2:
        raise ValueError("Enter your name.")
    _validate_credentials(email, password)

    with SessionLocal() as session:
        existing_user = session.query(User).filter(User.email == email).one_or_none()
        if existing_user:
            raise ValueError("Account already exists. Please login.")

        saved_user = User(
            name=name[:80],
            email=email,
            password_hash=_password_hash(password),
            role="operator",
            plan="free",
            subscription_status="inactive",
            subscription_mode="",
            subscription_id="",
            updated_at=int(time.time()),
        )
        session.add(saved_user)
        session.commit()
        session.refresh(saved_user)
        user = _user_payload(saved_user)
    return _auth_response(user)


def activate_prime_user(authorization: str | None, subscription: dict | None = None) -> dict:
    user = user_from_authorization(authorization)
    email = str(user.get("email", "")).strip().lower()
    if not email:
        raise ValueError("Login required to activate Prime.")

    subscription = subscription or {}
    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            saved_user = User(
                name=user.get("name") or _name_from_email(email),
                email=email,
                password_hash="",
                role=user.get("role", "operator"),
            )
            session.add(saved_user)

        saved_user.plan = "prime"
        saved_user.subscription_status = "active"
        saved_user.subscription_mode = subscription.get("mode", "demo")
        saved_user.subscription_id = subscription.get("subscription_id", "")
        saved_user.prime_activated_at = int(time.time())
        saved_user.updated_at = int(time.time())
        session.commit()
        session.refresh(saved_user)
        return _auth_response(_user_payload(saved_user))


def _validate_credentials(email: str, password: str) -> None:
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")


def _user_payload(record: dict) -> dict:
    if isinstance(record, User):
        return {
            "name": (record.name or _name_from_email(record.email))[:80],
            "email": record.email,
            "role": record.role or "operator",
            "plan": record.plan or "free",
            "subscription_status": record.subscription_status or "inactive",
            "subscription_mode": record.subscription_mode or "",
            "subscription_id": record.subscription_id or "",
            "prime_activated_at": record.prime_activated_at,
        }

    email = str(record.get("email", "")).strip().lower()
    return {
        "name": (record.get("name") or _name_from_email(email))[:80],
        "email": email,
        "role": record.get("role", "operator"),
        "plan": record.get("plan", "free"),
        "subscription_status": record.get("subscription_status", "inactive"),
        "subscription_mode": record.get("subscription_mode", ""),
        "subscription_id": record.get("subscription_id", ""),
        "prime_activated_at": record.get("prime_activated_at"),
    }


def _auth_response(user: dict) -> dict:
    return {
        "token": create_token(user),
        "user": user,
        "expires_in": get_settings().auth_token_ttl_seconds,
    }


def create_token(user: dict) -> str:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "name": user["name"],
        "email": user["email"],
        "role": user.get("role", "operator"),
        "plan": user.get("plan", "free"),
        "subscription_status": user.get("subscription_status", "inactive"),
        "subscription_mode": user.get("subscription_mode", ""),
        "subscription_id": user.get("subscription_id", ""),
        "prime_activated_at": user.get("prime_activated_at"),
        "iat": now,
        "exp": now + settings.auth_token_ttl_seconds,
    }
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _signature(encoded_payload)
    return f"{encoded_payload}.{signature}"


def user_from_authorization(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ValueError("Missing login token.")
    user = verify_token(authorization.split(" ", 1)[1].strip())
    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == str(user.get("email", "")).strip().lower()).one_or_none()
        return _user_payload(saved_user) if saved_user else user


def verify_token(token: str) -> dict:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid login token.") from exc

    expected_signature = _signature(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        raise ValueError("Invalid login token.")

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError("Invalid login token.") from exc

    if int(payload.get("exp", 0)) < int(time.time()):
        raise ValueError("Login session expired.")

    return {
        "name": payload.get("name", ""),
        "email": payload.get("email", ""),
        "role": payload.get("role", "operator"),
        "plan": payload.get("plan", "free"),
        "subscription_status": payload.get("subscription_status", "inactive"),
        "subscription_mode": payload.get("subscription_mode", ""),
        "subscription_id": payload.get("subscription_id", ""),
        "prime_activated_at": payload.get("prime_activated_at"),
    }


def _signature(encoded_payload: str) -> str:
    secret = get_settings().auth_token_secret.encode("utf-8")
    return _b64encode(hmac.new(secret, encoded_payload.encode("utf-8"), hashlib.sha256).digest())


def _password_hash(password: str) -> str:
    secret = get_settings().auth_token_secret.encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")


def _name_from_email(email: str) -> str:
    prefix = email.split("@", 1)[0] if email else "Operator"
    return prefix.replace(".", " ").replace("_", " ").title()
