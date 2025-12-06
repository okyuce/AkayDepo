"""
Auth API Router
Basit JWT tabanlı authentication
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import jwt  # PyJWT
import os
from sqlmodel import Session, select
from ..core.database import get_session
from ..models.user import User

router = APIRouter()
security = HTTPBearer()

# JWT config (destek: JWT_SECRET veya SECRET_KEY)
SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 saat


class LoginRequest(BaseModel):
    """Login isteği"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int




def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT token oluştur"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """JWT token'ı doğrula"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token süresi dolmuş")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Geçersiz token")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: Session = Depends(get_session)
):
    """Mevcut kullanıcıyı al (dependency)"""
    token = credentials.credentials
    payload = verify_token(token)
    username = payload.get("sub")
    user_id = payload.get("user_id")
    
    # Kullanıcıyı DB'den al
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Kullanıcı bulunamadı veya aktif değil")
    
    return {
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "station_id": str(user.station_id) if user.station_id else None,
        "full_name": user.full_name
    }


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: Session = Depends(get_session)):
    """
    Kullanıcı girişi
    
    Args:
        username: Kullanıcı adı
        password: Şifre
        
    Returns:
        JWT access token
    """
    # Kullanıcıyı DB'den bul
    statement = select(User).where(User.username == request.username)
    user = session.exec(statement).first()
    
    # Kullanıcı kontrolü ve şifre doğrulama
    if not user or not user.is_active or not user.verify_password(request.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token oluştur
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": str(user.id),
            "role": user.role
        },
        expires_delta=access_token_expires
    )
    
    return TokenResponse(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60  # saniye cinsinden
    )


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Mevcut kullanıcı bilgilerini getir"""
    return current_user


@router.post("/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """Çıkış yap (token client tarafında silinir)"""
    return {"message": "Başarıyla çıkış yapıldı"}
