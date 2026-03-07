"""
User Model
Kullanıcı yönetimi - admin ve tablet kullanıcıları
"""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
import bcrypt


class User(SQLModel, table=True):
    """Kullanıcı modeli - veritabanında saklanır"""
    __tablename__ = "users"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)  # bcrypt hash
    full_name: Optional[str] = Field(default=None)  # İsim soyisim (opsiyonel)
    role: str = Field(nullable=False)  # "admin" veya "tablet"
    station_id: Optional[UUID] = Field(default=None, foreign_key="stations.id")  # Tablet için dolu
    depot_id: Optional[UUID] = Field(default=None, foreign_key="depots.id", index=True)  # Superadmin için None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Şifreyi bcrypt ile hashle"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str) -> bool:
        """Şifreyi doğrula"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def set_password(self, password: str):
        """Şifreyi değiştir"""
        self.password_hash = User.hash_password(password)
        self.updated_at = datetime.now()
