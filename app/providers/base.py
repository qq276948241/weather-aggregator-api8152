import abc
import httpx
import asyncio
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import date
from app.schemas.schemas import CurrentWeather, WeatherForecast, WeatherHistoryRecord

logger = logging.getLogger(__name__)


class HTTPProviderError(Exception):
    pass


class WeatherProvider(abc.ABC):
    name: str = "base"

    _shared_client: Optional[httpx.AsyncClient] = None
    _default_timeout: float = 15.0
    _default_max_retries: int = 3
    _default_retry_backoff: float = 1.0

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url

    @classmethod
    def _get_client(cls) -> httpx.AsyncClient:
        if cls._shared_client is None or cls._shared_client.is_closed:
            cls._shared_client = httpx.AsyncClient(timeout=cls._default_timeout)
        return cls._shared_client

    @classmethod
    async def close_client(cls):
        if cls._shared_client and not cls._shared_client.is_closed:
            await cls._shared_client.aclose()
            cls._shared_client = None

    async def _http_get(self, url: str, params: Optional[Dict[str, Any]] = None,
                        timeout: Optional[float] = None,
                        max_retries: Optional[int] = None,
                        retry_backoff: Optional[float] = None,
                        expected_status: int = 200) -> Optional[Dict[str, Any]]:
        max_retries = max_retries or self._default_max_retries
        retry_backoff = retry_backoff or self._default_retry_backoff
        timeout = timeout or self._default_timeout

        client = self._get_client()
        last_exception: Optional[Exception] = None

        for attempt in range(max_retries):
            try:
                resp = await client.get(url, params=params, timeout=timeout)
                if resp.status_code == expected_status:
                    return resp.json()
                if resp.status_code >= 500 and attempt < max_retries - 1:
                    logger.warning(f"{self.name} HTTP {resp.status_code}, retrying ({attempt + 1}/{max_retries}): {url}")
                    await asyncio.sleep(retry_backoff * (2 ** attempt))
                    continue
                logger.warning(f"{self.name} HTTP {resp.status_code}: {url}")
                return None
            except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError) as e:
                last_exception = e
                if attempt < max_retries - 1:
                    wait_time = retry_backoff * (2 ** attempt)
                    logger.warning(f"{self.name} {type(e).__name__}, retrying in {wait_time:.1f}s ({attempt + 1}/{max_retries}): {url}")
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"{self.name} {type(e).__name__} after {max_retries} attempts: {url}")
                return None
            except Exception as e:
                logger.error(f"{self.name} unexpected error: {type(e).__name__}: {e}")
                return None

        if last_exception:
            logger.error(f"{self.name} failed after {max_retries} retries: {type(last_exception).__name__}")
        return None

    def _build_url(self, path: str) -> str:
        if not self.base_url:
            raise HTTPProviderError(f"{self.name} base_url not configured")
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _get_base_params(self) -> Dict[str, Any]:
        if not self.api_key:
            raise HTTPProviderError(f"{self.name} api_key not configured")
        return {}

    async def _api_get(self, path: str, params: Optional[Dict[str, Any]] = None,
                       **kwargs) -> Optional[Dict[str, Any]]:
        if not self.api_key:
            return None
        try:
            url = self._build_url(path)
            full_params = self._get_base_params()
            if params:
                full_params.update(params)
            return await self._http_get(url, full_params, **kwargs)
        except HTTPProviderError as e:
            logger.debug(str(e))
            return None

    @abc.abstractmethod
    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        ...

    @abc.abstractmethod
    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        ...

    @abc.abstractmethod
    async def get_aqi_by_coords(self, latitude: float, longitude: float) -> Optional[Dict[str, Any]]:
        ...

    async def get_aqi_by_city(self, city: str, country: str = "CN") -> Optional[Dict[str, Any]]:
        return None

    @abc.abstractmethod
    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        ...

    @abc.abstractmethod
    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        ...

    @abc.abstractmethod
    async def get_history_by_city(self, city: str, start_date: date, end_date: date,
                                  country: str = "CN") -> List[WeatherHistoryRecord]:
        ...

    @abc.abstractmethod
    async def get_history_by_coords(self, latitude: float, longitude: float,
                                    start_date: date, end_date: date) -> List[WeatherHistoryRecord]:
        ...

    @abc.abstractmethod
    async def is_available(self) -> bool:
        ...
