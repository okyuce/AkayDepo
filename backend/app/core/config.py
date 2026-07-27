from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator, Field
import json

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        json_loads=json.loads
    )
    
    # Database
    DATABASE_URL: str = "postgresql://depo:depo123@db:5432/akaydepo"
    
    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    
    # Auth
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # CORS - Accept either string or list
    CORS_ORIGINS: Union[str, List[str]] = Field(default="http://localhost:8000,http://localhost:8100")

    # Zebra Data Services (bulut yazdırma — SendFileToPrinter)
    # Yazıcı Weblink ile buluta bağlı; backend ZPL'i Zebra'ya POST eder, Zebra yazıcıya iter.
    ZEBRA_API_URL: str = "https://api.zebra.com/v2/devices/printers/send"
    ZEBRA_API_KEY: str = ""          # developer.zebra.com app Consumer Key
    ZEBRA_TENANT: str = ""           # yazıcının kayıtlı olduğu tenant
    ZEBRA_PRINTER_SERIAL: str = ""   # lokal test için varsayılan yazıcı seri no
    ZEBRA_TIMEOUT_SECONDS: float = 20.0
    # Online Print butonunun görüneceği depo kodları (virgülle) — ör. "KON".
    # Boşsa hiçbir depoda görünmez. Yeni bölgeye yazıcı kurulunca kodu buraya ekle.
    ZEBRA_ENABLED_DEPOT_CODES: str = ""
    
    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # Try JSON parse first
            if v.startswith('['):
                try:
                    return json.loads(v)
                except:
                    pass
            # Otherwise split by comma
            return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v

settings = Settings()
