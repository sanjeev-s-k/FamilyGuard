import os
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import User, UserRole, ParentProfile, ChildProfile

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "familyguard_super_secure_secret_key_2026_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def get_current_parent(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ParentProfile:
    if current_user.role == UserRole.PARENT or current_user.role == UserRole.ADMIN:
        profile = db.query(ParentProfile).filter(ParentProfile.user_id == current_user.id).first()
        if profile:
            return profile
    # Seamless demo fallback: if child profile is active, resolve to parent
    if current_user.role == UserRole.CHILD and current_user.child_profile and current_user.child_profile.parent:
        return current_user.child_profile.parent

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Parent privileges required",
    )


def get_current_child(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> ChildProfile:
    if current_user.role == UserRole.CHILD:
        profile = db.query(ChildProfile).filter(ChildProfile.user_id == current_user.id).first()
        if profile:
            return profile
    # Seamless demo fallback: if parent profile is active, resolve to first child
    if current_user.role == UserRole.PARENT and current_user.parent_profile and current_user.parent_profile.children:
        return current_user.parent_profile.children[0]

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Child privileges required",
    )
