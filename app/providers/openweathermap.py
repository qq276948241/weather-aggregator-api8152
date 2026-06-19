import httpx
from datetime import datetime, date
from typing import Optional, List
from app.providers.base import WeatherProvider
from app.schemas.schemas import CurrentWeather, WeatherForecast, ForecastDay, WeatherHistoryRecord
from app.config import settings


WEATHER_DESC_MAP = {
    "Clear": "晴", "Clouds": "多云", "Rain": "雨", "Drizzle": "小雨",
    "Thunderstorm": "雷阵雨", "Snow": "雪", "Mist": "雾", "Fog": "雾",
    "Haze": "霾", "Smoke": "烟", "Dust": "沙尘", "Ash": "火山灰",
    "Squall": "暴风", "Tornado": "龙卷风",
}


class OpenWeatherMapProvider(WeatherProvider):
    name = "openweathermap"

    def __init__(self):
        self.api_key = settings.OPENWEATHERMAP_API_KEY
        self.base_url = settings.OPENWEATHERMAP_BASE_URL
        self._client = httpx.AsyncClient(timeout=15.0)

    def _condition_map(self, main: str) -> str:
        return WEATHER_DESC_MAP.get(main, main)

    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        if not self.api_key:
            return None
        try:
            params = {"q": f"{city},{country}", "appid": self.api_key, "units": "metric", "lang": "zh_cn"}
            resp = await self._client.get(f"{self.base_url}/weather", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return CurrentWeather(
                location=city,
                latitude=data["coord"]["lat"],
                longitude=data["coord"]["lon"],
                data_source=self.name,
                observed_at=datetime.fromtimestamp(data["dt"]),
                temperature=data["main"].get("temp"),
                humidity=data["main"].get("humidity"),
                wind_speed=data["wind"].get("speed"),
                wind_direction=str(data["wind"].get("deg", "")),
                precipitation=(data.get("rain", {}) or {}).get("1h", 0),
                pressure=data["main"].get("pressure"),
                weather_condition=self._condition_map(data["weather"][0]["main"]) if data.get("weather") else "",
                feels_like=data["main"].get("feels_like"),
                visibility=data.get("visibility"),
            )
        except Exception:
            return None

    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        if not self.api_key:
            return None
        try:
            params = {"lat": latitude, "lon": longitude, "appid": self.api_key, "units": "metric", "lang": "zh_cn"}
            resp = await self._client.get(f"{self.base_url}/weather", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return CurrentWeather(
                location=data.get("name", f"({latitude:.2f}, {longitude:.2f})"),
                latitude=latitude,
                longitude=longitude,
                data_source=self.name,
                observed_at=datetime.fromtimestamp(data["dt"]),
                temperature=data["main"].get("temp"),
                humidity=data["main"].get("humidity"),
                wind_speed=data["wind"].get("speed"),
                wind_direction=str(data["wind"].get("deg", "")),
                precipitation=(data.get("rain", {}) or {}).get("1h", 0),
                pressure=data["main"].get("pressure"),
                weather_condition=self._condition_map(data["weather"][0]["main"]) if data.get("weather") else "",
                feels_like=data["main"].get("feels_like"),
                visibility=data.get("visibility"),
            )
        except Exception:
            return None

    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        if not self.api_key:
            return None
        try:
            lat_lon = await self._resolve_city(city, country)
            if not lat_lon:
                return None
            lat, lon = lat_lon
            return await self.get_forecast_by_coords(lat, lon, days)
        except Exception:
            return None

    async def _resolve_city(self, city: str, country: str) -> Optional[tuple]:
        try:
            params = {"q": f"{city},{country}", "appid": self.api_key, "units": "metric"}
            resp = await self._client.get(f"{self.base_url}/weather", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data["coord"]["lat"], data["coord"]["lon"]
        except Exception:
            return None

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        if not self.api_key:
            return None
        try:
            cnt = min(days * 8, 40)
            params = {"lat": latitude, "lon": longitude, "appid": self.api_key,
                      "units": "metric", "lang": "zh_cn", "cnt": cnt}
            resp = await self._client.get(f"{self.base_url}/forecast", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            daily: dict = {}
            for item in data["list"]:
                d = datetime.fromtimestamp(item["dt"]).date()
                if d not in daily:
                    daily[d] = []
                daily[d].append(item)
            forecast_days: List[ForecastDay] = []
            for d, items in sorted(daily.items())[:days]:
                temps = [i["main"]["temp"] for i in items if "main" in i and "temp" in i["main"]]
                hums = [i["main"]["humidity"] for i in items if "main" in i and "humidity" in i["main"]]
                rains = [((i.get("rain", {}) or {}).get("3h", 0)) for i in items]
                first = items[0]
                forecast_days.append(ForecastDay(
                    date=d,
                    temperature=round(sum(temps) / len(temps), 1) if temps else None,
                    temp_min=round(min(temps), 1) if temps else None,
                    temp_max=round(max(temps), 1) if temps else None,
                    humidity=int(sum(hums) / len(hums)) if hums else None,
                    precipitation=round(sum(rains), 1),
                    weather_condition=self._condition_map(first["weather"][0]["main"]) if first.get("weather") else "",
                ))
            return WeatherForecast(
                location=data.get("city", {}).get("name", f"({latitude:.2f}, {longitude:.2f})"),
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
            params = {"q": "Beijing", "appid": self.api_key, "units": "metric"}
            resp = await self._client.get(f"{self.base_url}/weather", params=params, timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
