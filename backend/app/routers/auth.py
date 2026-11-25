"""Kimlik doğrulama: kayıt, giriş (JWT), mevcut kullanıcı."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import Token, UserCreate, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

# Kullanıcı yokken de aynı sürede hash doğrulaması yapılır (kullanıcı adı sızdırmayı zorlaştırır)
_DUMMY_HASH = hash_password("dummy-password")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    username = payload.username.lower()
    exists = db.scalar(select(User).where((User.username == username) | (User.email == payload.email)))
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Kullanıcı adı veya e-posta zaten kayıtlı")

    user = User(username=username, email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError:  # eşzamanlı kayıt yarışı
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Kullanıcı adı veya e-posta zaten kayıtlı")
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.username == form.username.lower()))
    password_ok = verify_password(form.password, user.password_hash if user else _DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(
        str(user.id), settings.secret_key, settings.algorithm, settings.access_token_expire_minutes
    )
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
