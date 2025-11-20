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


# Basit kullanıcı listesi (production'da DB'den gelir)
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "tablet1": {"password": "tablet123", "role": "tablet"},
    "tablet2": {"password": "tablet123", "role": "tablet"},
    "tablet3": {"password": "tablet123", "role": "tablet"},
    "tablet4": {"password": "tablet123", "role": "tablet"},
    "tablet5": {"password": "tablet123", "role": "tablet"},
}


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


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Mevcut kullanıcıyı al (dependency)"""
    token = credentials.credentials
    payload = verify_token(token)
    username = payload.get("sub")
    
    if username not in USERS:
        raise HTTPException(401, "Kullanıcı bulunamadı")
    
    return {"username": username, "role": payload.get("role")}


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """
    Kullanıcı girişi
    
    Args:
        username: Kullanıcı adı
        password: Şifre
        
    Returns:
        JWT access token
    """
    # Kullanıcı kontrolü
    user = USERS.get(request.username)
    if not user or user["password"] != request.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kullanıcı adı veya şifre hatalı",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Token oluştur
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username, "role": user["role"]},
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
