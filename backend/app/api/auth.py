"""
Auth API Router
Basit JWT tabanlı authentication + çoklu depo desteği
"""
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, List
import jwt  # PyJWT
import os
from sqlmodel import Session, select
from ..core.database import get_session
from ..models.user import User
from ..models.depot import Depot

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
    depot_code: Optional[str] = None  # Depo kodu (superadmin için opsiyonel)


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DepotPublicResponse(BaseModel):
    """Public depo bilgisi (login sayfası için)"""
    code: str
    name: str
    city: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """JWT token oluştur"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _online_print_enabled(depot_code: Optional[str]) -> bool:
    """Bu deponun Online Print (Zebra bulut) butonunu görüp göremeyeceği.

    `ZEBRA_ENABLED_DEPOT_CODES` (virgülle ayrılmış, ör. "KON") içindeyse True.
    """
    from app.core.config import settings
    if not depot_code:
        return False
    enabled = {
        c.strip().upper()
        for c in (settings.ZEBRA_ENABLED_DEPOT_CODES or "").split(",")
        if c.strip()
    }
    return depot_code.upper() in enabled


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
    user_id = payload.get("user_id")

    # Kullanıcıyı DB'den al
    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(401, "Kullanıcı bulunamadı veya aktif değil")

    # Depo bilgisini al (superadmin için token'daki depot_id kullanılır)
    effective_depot_id = user.depot_id
    if user.role == "superadmin" and not user.depot_id:
        token_depot_id = payload.get("depot_id")
        if token_depot_id:
            from uuid import UUID
            effective_depot_id = UUID(token_depot_id)

    depot_id = str(effective_depot_id) if effective_depot_id else None
    depot_code = None
    depot_name = None
    depot_city = None
    if effective_depot_id:
        depot = session.get(Depot, effective_depot_id)
        if depot:
            depot_code = depot.code
            depot_name = depot.name
            depot_city = depot.city

    return {
        "user_id": str(user.id),
        "username": user.username,
        "role": user.role,
        "station_id": str(user.station_id) if user.station_id else None,
        "full_name": user.full_name,
        "depot_id": depot_id,
        "depot_code": depot_code,
        "depot_name": depot_name,
        "depot_city": depot_city,
        "online_print_enabled": _online_print_enabled(depot_code),
    }


def get_depot_id(current_user: dict = Depends(get_current_user)) -> Optional[str]:
    """JWT'den depot_id çıkar (superadmin için None olabilir)"""
    return current_user.get("depot_id")


def verify_depot_access(entity, depot_id: str, entity_name: str = "Kayıt"):
    """
    Bir entity'nin depot_id'sinin mevcut kullanıcının depot_id'siyle eşleştiğini doğrula.
    depot_id None ise (superadmin) kontrol atlanır.
    """
    if not depot_id:
        return  # Superadmin — tüm depolara erişim
    entity_depot_id = getattr(entity, 'depot_id', None)
    if entity_depot_id and str(entity_depot_id) != str(depot_id):
        raise HTTPException(403, f"{entity_name} başka bir depoya ait")


def require_depot(current_user: dict = Depends(get_current_user)) -> str:
    """Depot_id zorunlu (superadmin hariç tüm işlemler için)"""
    depot_id = current_user.get("depot_id")
    if not depot_id:
        raise HTTPException(403, "Bu işlem için bir depoya atanmış olmanız gerekir")
    return depot_id


def require_superadmin(current_user: dict = Depends(get_current_user)) -> dict:
    """Superadmin rolü zorunlu"""
    if current_user.get("role") != "superadmin":
        raise HTTPException(403, "Bu işlem için superadmin yetkisi gereklidir")
    return current_user


@router.get("/depots/public", response_model=List[DepotPublicResponse])
async def get_public_depots(session: Session = Depends(get_session)):
    """Login sayfası için aktif depo listesi (auth gerektirmez)"""
    statement = select(Depot).where(Depot.is_active == True).order_by(Depot.name)
    depots = session.exec(statement).all()
    return [
        DepotPublicResponse(code=d.code, name=d.name, city=d.city)
        for d in depots
    ]


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, session: Session = Depends(get_session)):
    """
    Kullanıcı girişi

    Args:
        username: Kullanıcı adı
        password: Şifre
        depot_code: Depo kodu (superadmin için opsiyonel)

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

    # Superadmin ve admin — depot_code gerekmez (dashboard erişimi)
    if user.role in ("superadmin", "admin"):
        # depot_code gönderilmişse doğrula, gönderilmemişse kullanıcının kendi deposunu kullan
        if request.depot_code:
            depot = session.exec(
                select(Depot).where(Depot.code == request.depot_code, Depot.is_active == True)
            ).first()
            if not depot:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Geçersiz depo kodu",
                )
            # Admin kullanıcı için depo eşleşmesi kontrol et
            if user.role == "admin" and user.depot_id and user.depot_id != depot.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bu depoya erişim yetkiniz yok",
                )
    else:
        # Normal kullanıcı (operator vb.) — depot_code zorunlu
        if not request.depot_code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Depo seçimi zorunludur",
            )

        # Depo var mı kontrol et
        depot = session.exec(
            select(Depot).where(Depot.code == request.depot_code, Depot.is_active == True)
        ).first()
        if not depot:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Geçersiz depo kodu",
            )

        # Kullanıcı bu depoya atanmış mı kontrol et
        if user.depot_id != depot.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu depoya erişim yetkiniz yok",
            )

    # Superadmin depo seçtiyse, seçilen depo bilgisini token'a yaz
    token_depot_id = str(user.depot_id) if user.depot_id else None
    if user.role == "superadmin" and request.depot_code:
        selected_depot = session.exec(
            select(Depot).where(Depot.code == request.depot_code, Depot.is_active == True)
        ).first()
        if selected_depot:
            token_depot_id = str(selected_depot.id)

    # Token oluştur
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.username,
            "user_id": str(user.id),
            "role": user.role,
            "depot_id": token_depot_id,
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
