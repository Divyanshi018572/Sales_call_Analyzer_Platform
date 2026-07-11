"""
Authentication utilities for JWT token generation, verification, and role authorization.

Why this approach:
We implement a custom authentication layer using python-jose and passlib (bcrypt). 
This allows us to maintain direct control over password verification, JWT token validation, 
and scoped role-based access checks. We define a dependency get_current_user and 
a helper class RoleChecker to enforce granular user-level and role-level permission guards.
"""

import datetime
from typing import List, Optional
import bcrypt
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from src.config import settings
from src.storage import db, models

# Setup Bearer security scheme
security = HTTPBearer()

def hash_password(password: str) -> str:
    """
    Hashes a plain-text password using bcrypt directly.
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain-text password against a stored bcrypt hash.
    """
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    Generates a short-lived JWT access token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: dict, expires_delta: Optional[datetime.timedelta] = None) -> str:
    """
    Generates a long-lived JWT refresh token.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.utcnow() + expires_delta
    else:
        expire = datetime.datetime.utcnow() + datetime.timedelta(days=7) # 7 days default
    to_encode.update({"exp": expire, "refresh": True})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security), 
    db_session: Session = Depends(db.get_db)
) -> models.User:
    """
    FastAPI dependency that extracts and decodes a JWT token to return the current authenticated user.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None or payload.get("refresh") is True: # Refresh tokens cannot be used to authenticate API requests
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db_session.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

class RoleChecker:
    """
    Dependency helper that enforces role membership requirements.
    """
    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: models.User = Depends(get_current_user)) -> models.User:
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )
        return current_user
