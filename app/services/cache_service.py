import hashlib
import json
import logging
from redis import Redis
from redis.exceptions import RedisError
from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.redis = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )

    @staticmethod
    def make_key(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "rag:answer:" + hashlib.sha256(raw.encode()).hexdigest()

    def get(self, payload: dict):
        try:
            value = self.redis.get(self.make_key(payload))
            return json.loads(value) if value else None
        except (RedisError, ValueError):
            logger.warning("cache_read_failed", exc_info=True)
            return None

    def set(self, payload: dict, value: dict):
        try:
            self.redis.setex(
                self.make_key(payload), settings.cache_ttl_seconds, json.dumps(value)
            )
        except (RedisError, TypeError, ValueError):
            logger.warning("cache_write_failed", exc_info=True)

    def close(self):
        self.redis.close()
