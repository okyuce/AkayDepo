"""
Users Management API
Kullanıcı yönetimi ve şifre işlemleri
"""
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field
from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from ..core.database import get_session
from ..models.user import User
from .auth import get_current_user

router = APIRouter()


class UserResponse(BaseModel):
    """Kullanıcı response modeli"""
    id: str
    username: str
    full_name: Optional[str] = None
    role: str
    station_id: Optional[str] = None
    is_active: bool
    created_at: str
    
    class Config:
        from_attributes = True


class ChangePasswordRequest(BaseModel):
    """Şifre değiştirme isteği (self-service)"""
    current_password: str = Field(..., min_length=6)
    new_password: str = Field(..., min_length=6)


class ResetPasswordRequest(BaseModel):
    """Şifre sıfırlama isteği (admin)"""
    new_password: str = Field(..., min_length=6)


class UpdateUserRequest(BaseModel):
    """Kullanıcı güncelleme isteği"""
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


@router.get("/", response_model=List[UserResponse])
async def list_users(
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Tüm kullanıcıları listele (sadece admin)
    """
    # Sadece admin yetkisi kontrolü
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok"
        )
    
    # Tüm kullanıcıları getir
    statement = select(User).order_by(User.created_at)
    users = session.exec(statement).all()
    
    return [
        UserResponse(
            id=str(user.id),
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            station_id=str(user.station_id) if user.station_id else None,
            is_active=user.is_active,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Kendi şifresini değiştir (self-service)
    """
    # Kullanıcıyı getir
    user = session.get(User, current_user["user_id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )
    
    # Mevcut şifreyi doğrula
    if not user.verify_password(request.current_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mevcut şifre hatalı"
        )
    
    # Yeni şifreyi ayarla
    user.set_password(request.new_password)
    session.add(user)
    session.commit()
    
    return {"message": "Şifre başarıyla değiştirildi"}


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: UUID,
    request: ResetPasswordRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Kullanıcının şifresini sıfırla (sadece admin)
    """
    # Sadece admin yetkisi kontrolü
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok"
        )
    
    # Kullanıcıyı getir
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )
    
    # Yeni şifreyi ayarla
    user.set_password(request.new_password)
    session.add(user)
    session.commit()
    
    return {"message": f"{user.username} kullanıcısının şifresi başarıyla sıfırlandı"}


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Kullanıcı bilgilerini güncelle (sadece admin)
    """
    # Sadece admin yetkisi kontrolü
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için yetkiniz yok"
        )
    
    # Kullanıcıyı getir
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kullanıcı bulunamadı"
        )
    
    # Güncellemeleri uygula
    if request.full_name is not None:
        user.full_name = request.full_name
    if request.is_active is not None:
        user.is_active = request.is_active
    
    session.add(user)
    session.commit()
    session.refresh(user)
    
    return UserResponse(
        id=str(user.id),
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        station_id=str(user.station_id) if user.station_id else None,
        is_active=user.is_active,
        created_at=user.created_at.isoformat()
    )
