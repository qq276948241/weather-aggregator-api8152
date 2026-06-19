from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from app.providers.base import WeatherProvider
from app.schemas.schemas import CurrentWeather, WeatherForecast, ForecastDay, WeatherHistoryRecord
from app.config import settings


class QWeatherProvider(WeatherProvider):
    name = "qweather"

    def __init__(self):
        super().__init__(
            api_key=settings.QWEATHER_API_KEY,
            base_url=settings.QWEATHER_BASE_URL,
        )

    def _get_base_params(self) -> Dict[str, Any]:
        return {"key": self.api_key}

    def _check_response(self, data: Optional[Dict[str, Any]]) -> bool:
        return data is not None and data.get("code") == "200"

    def _parse_aqi_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self._check_response(data):
            return None
        now = data["now"]
        return {
            "aqi": int(now.get("aqi", 0)),
            "aqi_level": now.get("category"),
            "pm2_5": float(now.get("pm2p5")) if now.get("pm2p5") else None,
            "pm10": float(now.get("pm10")) if now.get("pm10") else None,
            "so2": float(now.get("so2")) if now.get("so2") else None,
            "no2": float(now.get("no2")) if now.get("no2") else None,
            "co": float(now.get("co")) if now.get("co") else None,
            "o3": float(now.get("o3")) if now.get("o3") else None,
        }

    def _parse_current_response(self, data: Dict[str, Any], location: str,
                                 lat: float, lon: float) -> CurrentWeather:
        now = data["now"]
        return CurrentWeather(
            location=location,
            latitude=lat,
            longitude=lon,
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

    def _parse_forecast_response(self, data: Dict[str, Any], location: str,
                                  lat: float, lon: float, days: int) -> WeatherForecast:
        forecast_days: List[ForecastDay] = []
        for item in data.get("daily", [])[:days]:
            forecast_days.append(ForecastDay(
                date=date.fromisoformat(item["fxDate"]),
                latitude=lat,
                longitude=lon,
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
            location=location,
            latitude=lat,
            longitude=lon,
            data_source=self.name,
            days=forecast_days,
        )

    async def _lookup_location(self, location: str) -> Optional[Tuple[str, float, float]]:
        data = await self._api_get("/city/lookup", {"location": location})
        if not self._check_response(data) or not data.get("location"):
            return None
        loc = data["location"][0]
        loc_id = loc.get("id")
        if not loc_id:
            return None
        lat = float(loc.get("lat", 0)) if loc.get("lat") else 0.0
        lon = float(loc.get("lon", 0)) if loc.get("lon") else 0.0
        return loc_id, lat, lon

    async def get_aqi_by_coords(self, latitude: float, longitude: float) -> Optional[dict]:
        data = await self._api_get("/air/now", {"location": f"{longitude:.2f},{latitude:.2f}"})
        return self._parse_aqi_response(data)

    async def get_aqi_by_city(self, city: str, country: str = "CN") -> Optional[dict]:
        lookup = await self._lookup_location(city)
        if not lookup:
            return None
        loc_id = lookup[0]
        data = await self._api_get("/air/now", {"location": loc_id})
        return self._parse_aqi_response(data)

    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        lookup = await self._lookup_location(city)
        if not lookup:
            return None
        loc_id, lat, lon = lookup
        data = await self._api_get("/weather/now", {"location": loc_id})
        if not self._check_response(data):
            return None
        return self._parse_current_response(data, city, lat, lon)

    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        data = await self._api_get("/weather/now", {"location": f"{longitude:.2f},{latitude:.2f}"})
        if not self._check_response(data):
            return None
        return self._parse_current_response(data, f"({latitude:.2f}, {longitude:.2f})", latitude, longitude)

    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        lookup = await self._lookup_location(city)
        if not lookup:
            return None
        loc_id, lat, lon = lookup
        endpoint = "/weather/3d" if days <= 3 else "/weather/7d"
        data = await self._api_get(endpoint, {"location": loc_id})
        if not self._check_response(data):
            return None
        return self._parse_forecast_response(data, city, lat, lon, days)

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        endpoint = "/weather/3d" if days <= 3 else "/weather/7d"
        data = await self._api_get(endpoint, {"location": f"{longitude:.2f},{latitude:.2f}"})
        if not self._check_response(data):
            return None
        return self._parse_forecast_response(data, f"({latitude:.2f}, {longitude:.2f})", latitude, longitude, days)

    async def get_history_by_city(self, city: str, start_date: date, end_date: date,
                                  country: str = "CN") -> List[WeatherHistoryRecord]:
        return []

    async def get_history_by_coords(self, latitude: float, longitude: float,
                                    start_date: date, end_date: date) -> List[WeatherHistoryRecord]:
        return []

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        data = await self._api_get("/weather/now", {"location": "101010100"}, timeout=5.0, max_retries=1)
        return self._check_response(data)
