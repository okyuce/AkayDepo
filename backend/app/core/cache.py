"""
Redis Cache Helper
Sık çağrılan endpoint'ler için basit cache katmanı.
Hata durumunda sessizce DB'ye düşer (graceful degradation).
"""
import json
import logging
from typing import Optional, Any
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=2,
    )
    redis_client.ping()
    REDIS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Redis kullanılamıyor, cache devre dışı: {e}")
    redis_client = None
    REDIS_AVAILABLE = False


def cache_get(key: str) -> Optional[Any]:
    """Cache'den değer oku, yoksa None döndür"""
    if not REDIS_AVAILABLE:
        return None
    try:
        raw = redis_client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.warning(f"Cache GET hatası ({key}): {e}")
        return None


def cache_set(key: str, value: Any, ttl: int = 10) -> None:
    """Cache'e değer yaz, ttl saniye sonra otomatik silinir"""
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.warning(f"Cache SET hatası ({key}): {e}")


def cache_delete(key: str) -> None:
    """Cache'den sil"""
    if not REDIS_AVAILABLE:
        return
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.warning(f"Cache DELETE hatası ({key}): {e}")


def cache_delete_pattern(pattern: str) -> None:
    """Pattern'e uyan tüm key'leri sil (örn: 'active_cycle:*')"""
    if not REDIS_AVAILABLE:
        return
    try:
        keys = list(redis_client.scan_iter(match=pattern, count=100))
        if keys:
            redis_client.delete(*keys)
    except Exception as e:
        logger.warning(f"Cache DELETE pattern hatası ({pattern}): {e}")
