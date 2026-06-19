import abc
from typing import Optional, List
from datetime import date
from app.schemas.schemas import CurrentWeather, WeatherForecast, WeatherHistoryRecord


class WeatherProvider(abc.ABC):
    name: str = "base"

    @abc.abstractmethod
    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        ...

    @abc.abstractmethod
    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        ...

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
