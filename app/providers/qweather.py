import httpx
from datetime import datetime, date
from typing import Optional, List
from app.providers.base import WeatherProvider
from app.schemas.schemas import CurrentWeather, WeatherForecast, ForecastDay, WeatherHistoryRecord
from app.config import settings


class QWeatherProvider(WeatherProvider):
    name = "qweather"

    def __init__(self):
        self.api_key = settings.QWEATHER_API_KEY
        self.base_url = settings.QWEATHER_BASE_URL
        self._client = httpx.AsyncClient(timeout=15.0)

    async def _lookup_location(self, location: str) -> Optional[str]:
        if not self.api_key:
            return None
        try:
            params = {"location": location, "key": self.api_key}
            resp = await self._client.get(f"{self.base_url}/city/lookup", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("code") == "200" and data.get("location"):
                return data["location"][0]["id"]
        except Exception:
            pass
        return None

    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        if not self.api_key:
            return None
        try:
            loc_id = await self._lookup_location(city)
            if not loc_id:
                return None
            params = {"location": loc_id, "key": self.api_key}
            resp = await self._client.get(f"{self.base_url}/weather/now", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("code") != "200":
                return None
            now = data["now"]
            refer = data.get("location", {})
            return CurrentWeather(
                location=city,
                latitude=float(refer.get("lat", 0)) if isinstance(refer, dict) else 0,
                longitude=float(refer.get("lon", 0)) if isinstance(refer, dict) else 0,
                data_source=self.name,
                observed_at=datetime.fromisoformat(data["updateTime"].replace("Z", "+00:00")),
                temperature=float(now.get("temp")) if now.get("temp") else None,
                humidity=int(now.get("humidity")) if now.get("humidity") else None,
                wind_speed=float(now.get("windSpeed")) if now.get("windSpeed") else None,
                wind_direction=now.get("windDir"),
                precipitation=float(now.get("precip")) if now.get("precip") else 0,
                pressure=float(now.get("pressure")) if now.get("pressure") else None,
                weather_condition=now.get("text"),
                feels_like=float(now.get("feelsLike")) if now.get("feelsLike") else None,
                visibility=float(now.get("vis")) if now.get("vis") else None,
            )
        except Exception:
            return None

    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        if not self.api_key:
            return None
        try:
            params = {"location": f"{longitude:.2f},{latitude:.2f}", "key": self.api_key}
            resp = await self._client.get(f"{self.base_url}/weather/now", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("code") != "200":
                return None
            now = data["now"]
            return CurrentWeather(
                location=f"({latitude:.2f}, {longitude:.2f})",
                latitude=latitude,
                longitude=longitude,
                data_source=self.name,
                observed_at=datetime.fromisoformat(data["updateTime"].replace("Z", "+00:00")),
                temperature=float(now.get("temp")) if now.get("temp") else None,
                humidity=int(now.get("humidity")) if now.get("humidity") else None,
                wind_speed=float(now.get("windSpeed")) if now.get("windSpeed") else None,
                wind_direction=now.get("windDir"),
                precipitation=float(now.get("precip")) if now.get("precip") else 0,
                pressure=float(now.get("pressure")) if now.get("pressure") else None,
                weather_condition=now.get("text"),
                feels_like=float(now.get("feelsLike")) if now.get("feelsLike") else None,
                visibility=float(now.get("vis")) if now.get("vis") else None,
            )
        except Exception:
            return None

    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        if not self.api_key:
            return None
        try:
            loc_id = await self._lookup_location(city)
            if not loc_id:
                return None
            endpoint = f"{self.base_url}/weather/3d" if days <= 3 else f"{self.base_url}/weather/7d"
            params = {"location": loc_id, "key": self.api_key}
            resp = await self._client.get(endpoint, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("code") != "200":
                return None
            forecast_days: List[ForecastDay] = []
            for item in data.get("daily", [])[:days]:
                forecast_days.append(ForecastDay(
                    date=date.fromisoformat(item["fxDate"]),
                    temp_max=float(item.get("tempMax")) if item.get("tempMax") else None,
                    temp_min=float(item.get("tempMin")) if item.get("tempMin") else None,
                    weather_condition=item.get("textDay"),
                    wind_direction=item.get("windDirDay"),
                    wind_speed=float(item.get("windSpeedDay")) if item.get("windSpeedDay") else None,
                    humidity=int(item.get("humidity")) if item.get("humidity") else None,
                    precipitation=float(item.get("precip")) if item.get("precip") else 0,
                    precipitation_probability=int(item.get("pop")) if item.get("pop") else None,
                    pressure=float(item.get("pressure")) if item.get("pressure") else None,
                    sunrise=datetime.fromisoformat(item["sunrise"]) if item.get("sunrise") else None,
                    sunset=datetime.fromisoformat(item["sunset"]) if item.get("sunset") else None,
                ))
            return WeatherForecast(
                location=city,
                latitude=0,
                longitude=0,
                data_source=self.name,
                days=forecast_days,
            )
        except Exception:
            return None

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        if not self.api_key:
            return None
        try:
            endpoint = f"{self.base_url}/weather/3d" if days <= 3 else f"{self.base_url}/weather/7d"
            params = {"location": f"{longitude:.2f},{latitude:.2f}", "key": self.api_key}
            resp = await self._client.get(endpoint, params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if data.get("code") != "200":
                return None
            forecast_days: List[ForecastDay] = []
            for item in data.get("daily", [])[:days]:
                forecast_days.append(ForecastDay(
                    date=date.fromisoformat(item["fxDate"]),
                    temp_max=float(item.get("tempMax")) if item.get("tempMax") else None,
                    temp_min=float(item.get("tempMin")) if item.get("tempMin") else None,
                    weather_condition=item.get("textDay"),
                    wind_direction=item.get("windDirDay"),
                    wind_speed=float(item.get("windSpeedDay")) if item.get("windSpeedDay") else None,
                    humidity=int(item.get("humidity")) if item.get("humidity") else None,
                    precipitation=float(item.get("precip")) if item.get("precip") else 0,
                    precipitation_probability=int(item.get("pop")) if item.get("pop") else None,
                    pressure=float(item.get("pressure")) if item.get("pressure") else None,
                    sunrise=datetime.fromisoformat(item["sunrise"]) if item.get("sunrise") else None,
                    sunset=datetime.fromisoformat(item["sunset"]) if item.get("sunset") else None,
                ))
            return WeatherForecast(
                location=f"({latitude:.2f}, {longitude:.2f})",
                latitude=latitude,
                longitude=longitude,
                data_source=self.name,
                days=forecast_days,
            )
        except Exception:
            return None

    async def get_history_by_city(self, city: str, start_date: date, end_date: date,
                                  country: str = "CN") -> List[WeatherHistoryRecord]:
        return []

    async def get_history_by_coords(self, latitude: float, longitude: float,
                                    start_date: date, end_date: date) -> List[WeatherHistoryRecord]:
        return []

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        try:
            params = {"location": "101010100", "key": self.api_key}
            resp = await self._client.get(f"{self.base_url}/weather/now", params=params, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
