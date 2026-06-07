from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import smtplib
import time
from email.message import EmailMessage

from app.core.config import get_settings
from app.services.database import PasswordReset, SessionLocal, User, UserProfile


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PRIME_ACTIVE_STATUSES = {"active", "authenticated", "completed"}
MAX_AVATAR_DATA_URL_LENGTH = 900_000
RESET_CODE_LENGTH = 6


def login_user(payload: dict) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

    _validate_credentials(email, password)
    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("Account not found. Please sign up first.")
        if not _password_matches(saved_user.password_hash, password):
            raise ValueError("Invalid email or password.")

        profile = session.query(UserProfile).filter(UserProfile.email == email).one_or_none()
        user = _user_payload(saved_user, profile)
    return _auth_response(user)


def signup_user(payload: dict) -> dict:
    name = str(payload.get("name", "")).strip()
    email = str(payload.get("email", "")).strip().lower()
    password = str(payload.get("password", "")).strip()

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
        profile = _ensure_profile(session, email)
        session.add(saved_user)
        session.commit()
        session.refresh(saved_user)
        session.refresh(profile)
        user = _user_payload(saved_user, profile)
    return _auth_response(user)


def request_password_reset(payload: dict) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address.")

    settings = get_settings()
    now = int(time.time())
    reset_code = f"{secrets.randbelow(1_000_000):06d}"

    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("No account found for this email. Please sign up first.")

        reset = PasswordReset(
            email=email,
            code_hash=_reset_code_hash(email, reset_code),
            expires_at=now + settings.password_reset_code_ttl_seconds,
        )
        session.add(reset)
        session.commit()

    delivery = _send_password_reset_email(email, reset_code)
    response = {
        "status": "reset_code_created",
        "delivery": delivery,
        "expires_in": settings.password_reset_code_ttl_seconds,
        "message": "Reset code sent to your email." if delivery == "email" else "Demo reset code created.",
    }
    if delivery == "demo":
        response["reset_code"] = reset_code
    return response


def reset_password_user(payload: dict) -> dict:
    email = str(payload.get("email", "")).strip().lower()
    code = str(payload.get("code", "")).strip()
    password = str(payload.get("password") or payload.get("new_password") or "").strip()

    _validate_credentials(email, password)
    if not re.fullmatch(r"\d{6}", code):
        raise ValueError("Enter the 6 digit reset code.")

    now = int(time.time())
    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("No account found for this email. Please sign up first.")

        reset = (
            session.query(PasswordReset)
            .filter(PasswordReset.email == email)
            .order_by(PasswordReset.created_at.desc(), PasswordReset.id.desc())
            .first()
        )
        if not reset:
            raise ValueError("Request a reset code first.")
        if reset.used_at:
            raise ValueError("This reset code was already used. Request a new code.")
        if reset.expires_at < now:
            raise ValueError("Reset code expired. Request a new code.")
        if not hmac.compare_digest(reset.code_hash, _reset_code_hash(email, code)):
            raise ValueError("Invalid reset code.")

        saved_user.password_hash = _password_hash(password)
        saved_user.updated_at = now
        reset.used_at = now
        profile = _ensure_profile(session, email)
        session.commit()
        session.refresh(saved_user)
        session.refresh(profile)
        return _auth_response(_user_payload(saved_user, profile))


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
        profile = _ensure_profile(session, email)
        session.commit()
        session.refresh(saved_user)
        session.refresh(profile)
        return _auth_response(_user_payload(saved_user, profile))


def update_prime_subscription_user(authorization: str | None, subscription: dict | None = None) -> dict:
    user = user_from_authorization(authorization)
    email = str(user.get("email", "")).strip().lower()
    if not email:
        raise ValueError("Login required to update Prime subscription.")

    subscription = subscription or {}
    payment_status = str(
        subscription.get("payment_status") or subscription.get("status") or "created",
    ).strip().lower()
    subscription_id = str(subscription.get("subscription_id") or user.get("subscription_id") or "").strip()
    subscription_mode = str(subscription.get("mode") or user.get("subscription_mode") or "live").strip()
    now = int(time.time())

    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("Account not found. Please login again.")

        saved_user.subscription_status = payment_status or "created"
        saved_user.subscription_mode = subscription_mode
        if subscription_id:
            saved_user.subscription_id = subscription_id

        if saved_user.subscription_status in PRIME_ACTIVE_STATUSES:
            saved_user.plan = "prime"
            saved_user.prime_activated_at = saved_user.prime_activated_at or now

        saved_user.updated_at = now
        profile = _ensure_profile(session, email)
        session.commit()
        session.refresh(saved_user)
        session.refresh(profile)
        return _auth_response(_user_payload(saved_user, profile))


def update_profile_user(authorization: str | None, payload: dict | None = None) -> dict:
    user = user_from_authorization(authorization)
    email = str(user.get("email", "")).strip().lower()
    if not email:
        raise ValueError("Login required to update profile.")

    payload = payload or {}
    name = str(payload.get("name", user.get("name", ""))).strip()
    phone = str(payload.get("phone", user.get("phone", ""))).strip()
    organization = str(payload.get("organization", user.get("organization", ""))).strip()
    designation = str(payload.get("designation", user.get("designation", ""))).strip()
    city = str(payload.get("city", user.get("city", ""))).strip()
    avatar_data_url = str(payload.get("avatar_data_url", user.get("avatar_data_url", ""))).strip()

    if len(name) < 2:
        raise ValueError("Enter your name.")
    if avatar_data_url and not avatar_data_url.startswith("data:image/"):
        raise ValueError("Profile photo must be an image.")
    if len(avatar_data_url) > MAX_AVATAR_DATA_URL_LENGTH:
        raise ValueError("Profile photo is too large. Upload a smaller image.")

    with SessionLocal() as session:
        saved_user = session.query(User).filter(User.email == email).one_or_none()
        if not saved_user:
            raise ValueError("Account not found. Please login again.")

        profile = _ensure_profile(session, email)
        saved_user.name = name[:80]
        profile.phone = phone[:40]
        profile.organization = organization[:120]
        profile.designation = designation[:120]
        profile.city = city[:120]
        profile.avatar_data_url = avatar_data_url
        now = int(time.time())
        saved_user.updated_at = now
        profile.updated_at = now
        session.commit()
        session.refresh(saved_user)
        session.refresh(profile)
        return _auth_response(_user_payload(saved_user, profile))


def _validate_credentials(email: str, password: str) -> None:
    if not EMAIL_PATTERN.match(email):
        raise ValueError("Enter a valid email address.")
    if len(password) < 4:
        raise ValueError("Password must be at least 4 characters.")


def _user_payload(record: dict, profile: UserProfile | None = None) -> dict:
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
            **_profile_payload(profile),
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
        "phone": record.get("phone", ""),
        "organization": record.get("organization", ""),
        "designation": record.get("designation", ""),
        "city": record.get("city", ""),
        "avatar_data_url": record.get("avatar_data_url", ""),
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
        "phone": user.get("phone", ""),
        "organization": user.get("organization", ""),
        "designation": user.get("designation", ""),
        "city": user.get("city", ""),
        "avatar_data_url": user.get("avatar_data_url", ""),
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
        if not saved_user:
            return user
        profile = session.query(UserProfile).filter(UserProfile.email == saved_user.email).one_or_none()
        return _user_payload(saved_user, profile)


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
        "phone": payload.get("phone", ""),
        "organization": payload.get("organization", ""),
        "designation": payload.get("designation", ""),
        "city": payload.get("city", ""),
        "avatar_data_url": payload.get("avatar_data_url", ""),
    }


def _ensure_profile(session, email: str) -> UserProfile:
    profile = session.query(UserProfile).filter(UserProfile.email == email).one_or_none()
    if profile:
        return profile
    profile = UserProfile(email=email, updated_at=int(time.time()))
    session.add(profile)
    session.flush()
    return profile


def _profile_payload(profile: UserProfile | None) -> dict:
    return {
        "phone": profile.phone if profile else "",
        "organization": profile.organization if profile else "",
        "designation": profile.designation if profile else "",
        "city": profile.city if profile else "",
        "avatar_data_url": profile.avatar_data_url if profile else "",
    }


def _signature(encoded_payload: str) -> str:
    secret = get_settings().auth_token_secret.encode("utf-8")
    return _b64encode(hmac.new(secret, encoded_payload.encode("utf-8"), hashlib.sha256).digest())


def _password_hash(password: str) -> str:
    secret = get_settings().password_hash_secret.encode("utf-8")
    return hmac.new(secret, password.encode("utf-8"), hashlib.sha256).hexdigest()


def _password_matches(saved_hash: str, password: str) -> bool:
    settings = get_settings()
    possible_secrets = {
        settings.password_hash_secret,
        settings.auth_token_secret,
        "roadsense-dev-secret-change-me",
        "change_this_to_a_long_random_secret",
    }
    for secret in possible_secrets:
        candidate = hmac.new(secret.encode("utf-8"), password.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(saved_hash, candidate):
            return True
    return False


def _reset_code_hash(email: str, code: str) -> str:
    secret = get_settings().auth_token_secret.encode("utf-8")
    value = f"{email}:{code}".encode("utf-8")
    return hmac.new(secret, value, hashlib.sha256).hexdigest()


def _send_password_reset_email(email: str, code: str) -> str:
    settings = get_settings()
    if not settings.smtp_host or not settings.smtp_from_email:
        return "demo"

    message = EmailMessage()
    message["Subject"] = "RoadSense password reset code"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        "\n".join(
            [
                "Use this RoadSense password reset code:",
                "",
                code,
                "",
                f"This code expires in {settings.password_reset_code_ttl_seconds // 60} minutes.",
                "If you did not request this, ignore this email.",
            ],
        ),
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_use_tls:
            server.starttls()
        if settings.smtp_username:
            server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return "email"


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}").decode("utf-8")


def _name_from_email(email: str) -> str:
    prefix = email.split("@", 1)[0] if email else "Operator"
    return prefix.replace(".", " ").replace("_", " ").title()
