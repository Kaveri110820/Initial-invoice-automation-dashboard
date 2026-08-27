import datetime
import hashlib
import re
import secrets

import streamlit as st

from database import (
    add_user,
    create_reset_token,
    get_user_by_email,
    get_valid_reset_token,
    mark_reset_token_used,
    update_user_password,
)

_ITERATIONS = 600_000
_SALT_BYTES = 16
_HASH_BYTES = 32

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

ROLES = ("Admin", "Employee")
RESET_TOKEN_TTL_MINUTES = 15


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _ITERATIONS, dklen=_HASH_BYTES
    )
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, iterations, salt_hex, hash_hex = stored_hash.split("$")
        if algo != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, int(iterations), dklen=len(expected)
        )
        return secrets.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email or ""))


def create_user(full_name: str, email: str, password: str) -> tuple[bool, str | None]:
    email = (email or "").strip().lower()
    full_name = (full_name or "").strip()

    if not full_name:
        return False, "Full name is required."
    if not email:
        return False, "Email is required."
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    if not password:
        return False, "Password is required."
    if get_user_by_email(email):
        return False, "An account with this email already exists."

    password_hash = hash_password(password)
    user_id = add_user(full_name, email, password_hash, role="Employee")
    if not user_id:
        return False, "Could not create account. Please try again."
    return True, None


def authenticate_user(email: str, password: str) -> dict | None:
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    user = get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def is_logged_in() -> bool:
    return bool(st.session_state.get("user"))


def get_current_user() -> dict | None:
    return st.session_state.get("user")


def login(email: str, password: str) -> tuple[bool, str | None]:
    user = authenticate_user(email, password)
    if not user:
        return False, "Invalid email or password."
    public = {k: v for k, v in user.items() if k in ("id", "full_name", "email", "role")}
    st.session_state["user"] = public
    return True, None


def logout() -> None:
    st.session_state.pop("user", None)


def get_role() -> str:
    user = get_current_user()
    return (user or {}).get("role", "Employee")


def is_admin() -> bool:
    return get_role() == "Admin"


def request_password_reset(email: str) -> tuple[bool, str | None]:
    email = (email or "").strip().lower()
    if not email:
        return False, "Email is required."
    user = get_user_by_email(email)
    if not user:
        return False, "If that email exists, a reset token will be generated."

    token = secrets.token_urlsafe(24)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    expires_at = (
        datetime.datetime.utcnow() + datetime.timedelta(minutes=RESET_TOKEN_TTL_MINUTES)
    ).strftime("%Y-%m-%d %H:%M:%S")
    create_reset_token(token_hash, email, expires_at)
    return True, token


def reset_password(email: str, token: str, new_password: str) -> tuple[bool, str | None]:
    email = (email or "").strip().lower()
    if not email:
        return False, "Email is required."
    if not token:
        return False, "Reset token is required."
    if not new_password:
        return False, "New password is required."

    token_hash = hashlib.sha256(token.strip().encode("utf-8")).hexdigest()
    record = get_valid_reset_token(token_hash)
    if not record or record["email"].lower() != email:
        return False, "Invalid or already-used reset token."

    expires = datetime.datetime.strptime(record["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.datetime.utcnow() > expires:
        return False, "This reset token has expired. Please request a new one."

    user = get_user_by_email(email)
    if not user:
        return False, "User no longer exists."

    update_user_password(user["id"], hash_password(new_password))
    mark_reset_token_used(record["id"])
    return True, None
