from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy.orm import Session
from .config import settings
from .database import db_session
from .models import Team, User, UserRole

hasher = PasswordHash.recommended()
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_password(value: str) -> str: return hasher.hash(value)
def verify_password(value: str, hashed: str) -> bool: return hasher.verify(value, hashed)
def create_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings().access_token_expire_minutes)
    return jwt.encode({"sub": user.id, "exp": expires}, settings().secret_key, algorithm="HS256")
def load_user_for_token(token: str, db: Session) -> User:
    try:
        claims = jwt.decode(token, settings().secret_key, algorithms=["HS256"])
        user_id = claims["sub"]
    except (jwt.PyJWTError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = db.get(User, user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Inactive account")
    view_only = claims.get('scope') == 'team:view'
    if view_only:
        team = db.get(Team, user.team_id) if user.team_id else None
        if (user.role != UserRole.TEAM_LEADER or not team or
                team.id != claims.get('team_id') or team.game_id != claims.get('game_id')):
            raise HTTPException(status_code=401, detail="Deze teamlink is niet meer geldig")
    # Request-local flag; never stored on the user or used to change their role.
    user.view_only = view_only
    return user


VIEWER_READ_PATHS = frozenset(('/api/auth/me', '/api/game', '/api/game-objects',
                               '/api/locations', '/api/scores', '/api/news'))


def current_user(token: str = Depends(oauth2), db: Session = Depends(db_session), request: Request = None) -> User:
    user = load_user_for_token(token, db)
    if user.view_only:
        path = request.url.path if request else ''
        allowed = path in VIEWER_READ_PATHS or path.startswith('/api/game-objects/') or path.startswith('/api/photos/')
        if not request or request.method != 'GET' or not allowed:
            raise HTTPException(status_code=403, detail="Deze teamlink geeft alleen kijkrechten")
    return user


def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != UserRole.ADMIN: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user
