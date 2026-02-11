from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
from src.services.rate_limiter import get_rate_limiter

router = APIRouter()
security = HTTPBearer()


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LogoutResponse(BaseModel):
    detail: str


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def get_db(request: Request):
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(status_code=500, detail="Database not initialized")
    return db


def get_auth_config(request: Request):
    auth_conf = request.app.state.config.get("auth", {})
    secret = auth_conf.get("SECRET_KEY")
    algo = auth_conf.get("ALGORITHM", "HS256")
    expire = int(auth_conf.get("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
    return secret, algo, expire


def check_auth_rate_limit(request: Request) -> None:
    """
    Check rate limit for auth endpoints based on IP address.
    Prevents brute force attacks.
    """
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter = get_rate_limiter()
    
    ip_hash = abs(hash(client_ip)) % 1000000
    pseudo_user_id = -ip_hash - 1
    
    is_allowed, message = rate_limiter.is_allowed(pseudo_user_id, client_ip)
    if not is_allowed:
        raise HTTPException(status_code=429, detail=message)


def create_access_token(data: dict, request: Request, expires_delta: timedelta | None = None):
    secret, algo, default_exp = get_auth_config(request)
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=default_exp))
    to_encode = data.copy()
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=algo)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None) -> int:
    """Decode JWT token and return user_id. Raises HTTPException if invalid."""
    token = credentials.credentials
    secret, algo, _ = get_auth_config(request)
    try:
        payload = jwt.decode(token, secret, algorithms=[algo])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# -- routes --

@router.post("/register", response_model=AuthResponse)
def register(req: AuthRequest, request: Request):
    # Check rate limit to prevent brute force
    check_auth_rate_limit(request)
    
    db = get_db(request)
    if db.get_user_by_username(req.username):
        raise HTTPException(status_code=401, detail="User already exists")

    hashed = hash_password(req.password)
    user_id = db.create_user(req.username, hashed)

    token = create_access_token({"sub": req.username, "user_id": user_id}, request)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=AuthResponse)
def login(req: AuthRequest, request: Request):
    # Check rate limit to prevent brute force
    check_auth_rate_limit(request)
    
    db = get_db(request)
    
    user = db.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": req.username, "user_id": user["id"]}, request)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", response_model=LogoutResponse)
def logout(user_id: int = Depends(get_current_user)):
    # JWT logout is client-side (token deletion). Server validates the token is still valid.
    # For server-side logout, would need token blacklist/revocation.
    return {"detail": "Logged out"}
