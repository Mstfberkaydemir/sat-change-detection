"""Ortak bağımlılıklar: aktif kullanıcıyı JWT'den çıkarma."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı",
        headers={"WWW-Authenticate": "Bearer"},
    )
    sub = decode_access_token(token, settings.secret_key, settings.algorithm)
    if sub is None or not sub.isdigit():
        raise credentials_error
    user = db.get(User, int(sub))
    if user is None:
        raise credentials_error
    return user
