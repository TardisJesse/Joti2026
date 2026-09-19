from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import settings
from .database import db_session
from .models import User, UserRole

hasher = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(value: str) -> str: return hasher.hash(value)
def verify_password(value: str, hashed: str) -> bool: return hasher.verify(value, hashed)
def create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings().access_token_expire_minutes)
    return jwt.encode({"sub": user.id, "exp": expires}, settings().secret_key, algorithm="HS256")
def current_user(token: str = Depends(oauth2), db: Session = Depends(db_session)) -> User:
    try: user_id = jwt.decode(token, settings().secret_key, algorithms=["HS256"])["sub"]
    except (jwt.PyJWTError, KeyError): raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.get(User, user_id)
    if not user or not user.active: raise HTTPException(status_code=401, detail="Inactive account")
    return user
def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
