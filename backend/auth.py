"""JWT Email/Password Auth + Emergent Google SSO."""
import os
import bcrypt
import jwt
import secrets
import httpx
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import EmailStr, BaseModel

from models import User, RegisterRequest, LoginRequest, _now

JWT_ALGORITHM = "HS256"
ACCESS_TTL_MIN = 60 * 24  # 24 hours
REFRESH_TTL_DAYS = 7


def _secret() -> str:
    return os.environ["JWT_SECRET"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TTL_MIN),
        "type": "access",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TTL_DAYS),
        "type": "refresh",
    }
    return jwt.encode(payload, _secret(), algorithm=JWT_ALGORITHM)


def set_auth_cookies(response: Response, access: str, refresh: str):
    # Cross-site cookies for preview environment (frontend & backend share host via ingress)
    response.set_cookie(
        key="access_token", value=access, httponly=True, secure=True,
        samesite="none", max_age=ACCESS_TTL_MIN * 60, path="/",
    )
    response.set_cookie(
        key="refresh_token", value=refresh, httponly=True, secure=True,
        samesite="none", max_age=REFRESH_TTL_DAYS * 86400, path="/",
    )


def clear_auth_cookies(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    response.delete_cookie("session_token", path="/")


async def _user_from_jwt(token: str, db) -> dict:
    payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _user_from_session(session_token: str, db) -> dict:
    sess = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
    if not sess:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = sess["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    user = await db.users.find_one({"user_id": sess["user_id"]}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_db_dep(request: Request):
    return request.app.state.db


async def get_current_user(request: Request) -> dict:
    db = request.app.state.db
    # Try session_token first (Google SSO)
    session_token = request.cookies.get("session_token")
    if session_token:
        try:
            return await _user_from_session(session_token, db)
        except HTTPException:
            pass
    # Then JWT cookie
    access = request.cookies.get("access_token")
    if not access:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            access = auth_header[7:]
    if not access:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        return await _user_from_jwt(access, db)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user


# ─── Routes ─────────────────────────────────────────────────────
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(req: RegisterRequest, request: Request, response: Response):
    db = request.app.state.db
    email = req.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(email=email, name=req.name.strip(), auth_provider="password")
    doc = user.model_dump()
    doc["password_hash"] = hash_password(req.password)
    doc["created_at"] = doc["created_at"].isoformat()
    await db.users.insert_one(doc)
    access = create_access_token(user.user_id, email)
    refresh = create_refresh_token(user.user_id)
    set_auth_cookies(response, access, refresh)
    return user.model_dump(mode="json")


@router.post("/login")
async def login(req: LoginRequest, request: Request, response: Response):
    db = request.app.state.db
    email = req.email.lower().strip()
    user_doc = await db.users.find_one({"email": email})
    if not user_doc or not user_doc.get("password_hash"):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(req.password, user_doc["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access = create_access_token(user_doc["user_id"], email)
    refresh = create_refresh_token(user_doc["user_id"])
    set_auth_cookies(response, access, refresh)
    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    return user_doc


@router.post("/logout")
async def logout(request: Request, response: Response):
    db = request.app.state.db
    session_token = request.cookies.get("session_token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    clear_auth_cookies(response)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, _secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        db = request.app.state.db
        user = await db.users.find_one({"user_id": payload["sub"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        access = create_access_token(user["user_id"], user["email"])
        response.set_cookie(
            key="access_token", value=access, httponly=True, secure=True,
            samesite="none", max_age=ACCESS_TTL_MIN * 60, path="/",
        )
        return {"ok": True}
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")


# ─── Emergent Google SSO ────────────────────────────────────────
class SessionExchange(BaseModel):
    session_id: str


@router.post("/google/session")
async def google_session(payload: SessionExchange, request: Request, response: Response):
    """Exchange a session_id from Emergent Google Auth for an app session."""
    db = request.app.state.db
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.get(
                "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                headers={"X-Session-ID": payload.session_id},
            )
            r.raise_for_status()
        except httpx.HTTPError:
            raise HTTPException(status_code=400, detail="Invalid Emergent session_id")
        data = r.json()
    email = data["email"].lower().strip()
    name = data.get("name") or email.split("@")[0]
    picture = data.get("picture")
    session_token = data["session_token"]

    # Upsert user
    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        new_user = User(email=email, name=name, picture=picture, auth_provider="google")
        doc = new_user.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.users.insert_one(doc)
        user_doc = await db.users.find_one({"email": email})
    elif picture and user_doc.get("picture") != picture:
        await db.users.update_one({"email": email}, {"$set": {"picture": picture}})
        user_doc["picture"] = picture

    # Save session
    await db.user_sessions.update_one(
        {"session_token": session_token},
        {"$set": {
            "session_token": session_token,
            "user_id": user_doc["user_id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )

    # Set httpOnly session cookie
    response.set_cookie(
        key="session_token", value=session_token, httponly=True, secure=True,
        samesite="none", max_age=7 * 86400, path="/",
    )
    user_doc.pop("_id", None)
    user_doc.pop("password_hash", None)
    return user_doc


# ─── Forgot password (logs token to server) ─────────────────────
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, request: Request):
    db = request.app.state.db
    user = await db.users.find_one({"email": req.email.lower().strip()})
    # Always return ok to avoid email enumeration
    if user and user.get("auth_provider") == "password":
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": user["user_id"],
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "used": False,
        })
        # In production: send via Resend. For MVP, log it.
        print(f"[PASSWORD_RESET_LINK] /reset?token={token}")
    return {"ok": True}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest, request: Request):
    db = request.app.state.db
    rec = await db.password_reset_tokens.find_one({"token": req.token, "used": False}, {"_id": 0})
    if not rec:
        raise HTTPException(status_code=400, detail="Invalid or used token")
    expires_at = rec["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Token expired")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")
    await db.users.update_one(
        {"user_id": rec["user_id"]},
        {"$set": {"password_hash": hash_password(req.new_password)}},
    )
    await db.password_reset_tokens.update_one({"token": req.token}, {"$set": {"used": True}})
    return {"ok": True}
