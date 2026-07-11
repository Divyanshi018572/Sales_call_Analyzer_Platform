"""
API router for authentication and token management.

Why this approach:
We implement REST routes for user login and token refresh, returning Pydantic models.
This encapsulates authentication requests separately from business logic and allows the frontend
to acquire tokens securely and query details about the currently logged-in user profile.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.storage import db, models
from src.api import schemas, auth_utils
from jose import JWTError, jwt
from src.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=schemas.TokenResponse)
def login(request: schemas.LoginRequest, db_session: Session = Depends(db.get_db)):
    """
    Authenticates a user via email and password, returning JWT access and refresh tokens.
    """
    user = db_session.query(models.User).filter(models.User.email == request.email).first()
    if not user or not auth_utils.verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    # Generate tokens
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    refresh_token = auth_utils.create_refresh_token(data={"sub": user.email})
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        role=user.role,
        email=user.email,
        advisor_id=user.advisor_id,
        team_id=user.team_id
    )

@router.get("/me", response_model=schemas.UserProfileResponse)
def get_me(current_user: models.User = Depends(auth_utils.get_current_user)):
    """
    Returns the currently authenticated user's profile.
    """
    return current_user

class RefreshRequest(schemas.BaseModel):
    """
    Request model containing a refresh token to request a new access token.
    """
    refresh_token: str

@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh_token(request: RefreshRequest, db_session: Session = Depends(db.get_db)):
    """
    Refreshes the access token using a valid refresh token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh credentials",
    )
    try:
        payload = jwt.decode(request.refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        is_refresh = payload.get("refresh")
        if email is None or not is_refresh:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db_session.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
        
    access_token = auth_utils.create_access_token(data={"sub": user.email})
    new_refresh_token = auth_utils.create_refresh_token(data={"sub": user.email})
    
    return schemas.TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        role=user.role,
        email=user.email,
        advisor_id=user.advisor_id,
        team_id=user.team_id
    )
