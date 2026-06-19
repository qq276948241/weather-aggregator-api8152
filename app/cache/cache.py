import abc
import time
import json
import pickle
from typing import Any, Optional, Dict
from app.config import settings


class CacheBackend(abc.ABC):
    @abc.abstractmethod
    def get(self, key: str) -> Optional[Any]:
        ...

    @abc.abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        ...

    @abc.abstractmethod
    def delete(self, key: str) -> None:
        ...

    @abc.abstractmethod
    def exists(self, key: str) -> bool:
        ...

    @abc.abstractmethod
    def clear(self) -> None:
        ...


class MemoryCache(CacheBackend):
    def __init__(self, default_ttl: int = 300):
        self._store: Dict[str, tuple] = {}
        self._default_ttl = default_ttl

    def _is_expired(self, entry: tuple) -> bool:
        _, expire_at = entry
        if expire_at is None:
            return False
        return time.time() > expire_at

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if not entry:
            return None
        if self._is_expired(entry):
            del self._store[key]
            return None
        return entry[0]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        actual_ttl = ttl if ttl is not None else self._default_ttl
        expire_at = time.time() + actual_ttl if actual_ttl > 0 else None
        self._store[key] = (value, expire_at)

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    def exists(self, key: str) -> bool:
        entry = self._store.get(key)
        if not entry:
            return False
        if self._is_expired(entry):
            del self._store[key]
            return False
        return True

    def clear(self) -> None:
        self._store.clear()


class RedisCache(CacheBackend):
    def __init__(self, redis_url: str, default_ttl: int = 300):
        try:
            import redis
            self._client = redis.Redis.from_url(redis_url)
            self._client.ping()
        except Exception:
            self._client = None
        self._default_ttl = default_ttl

    @property
    def available(self) -> bool:
        return self._client is not None

    def get(self, key: str) -> Optional[Any]:
        if not self.available:
            return None
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            return pickle.loads(raw)
        except Exception:
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        if not self.available:
            return
        actual_ttl = ttl if ttl is not None else self._default_ttl
        try:
            if actual_ttl > 0:
                self._client.setex(key, actual_ttl, pickle.dumps(value))
            else:
                self._client.set(key, pickle.dumps(value))
        except Exception:
            pass

    def delete(self, key: str) -> None:
        if not self.available:
            return
        try:
            self._client.delete(key)
        except Exception:
            pass

    def exists(self, key: str) -> bool:
        if not self.available:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception:
            return False

    def clear(self) -> None:
        if not self.available:
            return
        try:
            self._client.flushdb()
        except Exception:
            pass


_cache_instance: Optional[CacheBackend] = None


def get_cache() -> CacheBackend:
    global _cache_instance
    if _cache_instance is None:
        ttl = settings.CACHE_TTL_SECONDS
        if settings.CACHE_BACKEND == "redis" and settings.REDIS_URL:
            redis_cache = RedisCache(settings.REDIS_URL, default_ttl=ttl)
            if redis_cache.available:
                _cache_instance = redis_cache
            else:
                _cache_instance = MemoryCache(default_ttl=ttl)
        else:
            _cache_instance = MemoryCache(default_ttl=ttl)
    return _cache_instance


def make_cache_key(prefix: str, *parts, **kwargs) -> str:
    key_parts = [prefix] + [str(p) for p in parts]
    if kwargs:
        sorted_kwargs = sorted(kwargs.items())
        key_parts.append("&".join(f"{k}={v}" for k, v in sorted_kwargs))
    return ":".join(key_parts)
