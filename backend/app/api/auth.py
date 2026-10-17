import hashlib
import hmac
import json
import secrets
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.config import settings

router = APIRouter()

PASSWORD_HASH_ITERATIONS = 600_000
PASSWORD_HASH_PREFIX = "pbkdf2_sha256"


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class RegisterPayload(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt, PASSWORD_HASH_ITERATIONS
    )
    return f"{PASSWORD_HASH_PREFIX}${PASSWORD_HASH_ITERATIONS}${salt.hex()}${password_hash.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith(f"{PASSWORD_HASH_PREFIX}$"):
        try:
            prefix, iterations_text, salt_hex, hash_hex = stored_hash.split("$")
            iterations = int(iterations_text)
            salt = bytes.fromhex(salt_hex)
            expected_hash = bytes.fromhex(hash_hex)
        except (ValueError, TypeError):
            return False

        if prefix != PASSWORD_HASH_PREFIX or iterations <= 0:
            return False
        actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual_hash, expected_hash)

    if not settings.LEGACY_PASSWORD_SALT:
        return False

    legacy_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), settings.LEGACY_PASSWORD_SALT.encode(), 200_000
    ).hex()
    return hmac.compare_digest(legacy_hash, stored_hash)


def session_key(token: str) -> str:
    return f"session:{token}"


async def get_current_user(request: Request) -> dict:
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization token")

    token = authorization.split(" ", 1)[1].strip()
    redis = request.app.state.redis
    data = await redis.get(session_key(token))
    if not data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")

    try:
        user = json.loads(data)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    return user


@router.post("/login")
async def login(request: Request, payload: LoginPayload):
    pool = request.app.state.db
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id::text AS id, email, name, password_hash, is_admin FROM users WHERE email = $1",
            payload.email,
        )

    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    stored_hash = row["password_hash"]
    if not verify_password(payload.password, stored_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not stored_hash.startswith(f"{PASSWORD_HASH_PREFIX}$"):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET password_hash = $1 WHERE id = $2",
                hash_password(payload.password),
                row["id"],
            )

    token = secrets.token_urlsafe(32)
    user_data = {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "is_admin": row["is_admin"],
    }
    await request.app.state.redis.set(session_key(token), json.dumps(user_data), ex=settings.SESSION_TTL_HOURS * 3600)

    return {"token": token, "user": user_data}


@router.post("/register")
async def register(request: Request, payload: RegisterPayload):
    if len(payload.password) < 6:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password must be at least 6 characters")

    pool = request.app.state.db
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", payload.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

        row = await conn.fetchrow(
            "INSERT INTO users (email, name, password_hash) VALUES ($1, $2, $3) RETURNING id::text AS id, email, name, is_admin",
            payload.email,
            payload.name,
            hash_password(payload.password),
        )

    token = secrets.token_urlsafe(32)
    user_data = {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "is_admin": row["is_admin"],
    }
    await request.app.state.redis.set(session_key(token), json.dumps(user_data), ex=settings.SESSION_TTL_HOURS * 3600)

    return {"token": token, "user": user_data}


@router.post("/logout")
async def logout(request: Request):
    authorization = request.headers.get("Authorization")
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await request.app.state.redis.delete(session_key(token))

    return {"status": "ok"}


@router.get("/me")
async def me(request: Request):
    user = await get_current_user(request)
    return user
