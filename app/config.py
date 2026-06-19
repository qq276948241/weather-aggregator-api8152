from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ColdChainWeatherAggregation"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./weather.db"

    CACHE_BACKEND: str = "memory"
    CACHE_TTL_SECONDS: int = 300
    REDIS_URL: Optional[str] = None

    WEATHER_PROVIDERS: str = "mock"
    OPENWEATHERMAP_API_KEY: Optional[str] = None
    OPENWEATHERMAP_BASE_URL: str = "https://api.openweathermap.org/data/2.5"
    QWEATHER_API_KEY: Optional[str] = None
    QWEATHER_BASE_URL: str = "https://devapi.qweather.com/v7"

    ALERT_HIGH_TEMP_THRESHOLD: float = 35.0
    ALERT_HEAVY_RAIN_THRESHOLD: float = 50.0
    ALERT_LOW_TEMP_THRESHOLD: float = -10.0
    ALERT_CHECK_INTERVAL_MINUTES: int = 10

    BRIEFING_GENERATION_HOUR: int = 6
    SUBSCRIPTION_PUSH_INTERVAL_MINUTES: int = 30

    @property
    def provider_list(self) -> List[str]:
        return [p.strip() for p in self.WEATHER_PROVIDERS.split(",") if p.strip()]


settings = Settings()
