from datetime import datetime, date
from typing import Optional, List, Dict, Any
from app.providers.base import WeatherProvider
from app.schemas.schemas import CurrentWeather, WeatherForecast, ForecastDay, WeatherHistoryRecord
from app.config import settings


WEATHER_DESC_MAP = {
    "Clear": "晴", "Clouds": "多云", "Rain": "雨", "Drizzle": "小雨",
    "Thunderstorm": "雷阵雨", "Snow": "雪", "Mist": "雾", "Fog": "雾",
    "Haze": "霾", "Smoke": "烟", "Dust": "沙尘", "Ash": "火山灰",
    "Squall": "暴风", "Tornado": "龙卷风",
}

AQI_LEVEL_MAP = {1: "优", 2: "良", 3: "轻度污染", 4: "中度污染", 5: "重度污染", 6: "严重污染"}
AQI_TO_CN = {1: 25, 2: 75, 3: 125, 4: 175, 5: 250}


class OpenWeatherMapProvider(WeatherProvider):
    name = "openweathermap"

    def __init__(self):
        super().__init__(
            api_key=settings.OPENWEATHERMAP_API_KEY,
            base_url=settings.OPENWEATHERMAP_BASE_URL,
        )

    def _get_base_params(self) -> Dict[str, Any]:
        return {"appid": self.api_key, "units": "metric", "lang": "zh_cn"}

    def _condition_map(self, main: str) -> str:
        return WEATHER_DESC_MAP.get(main, main)

    def _parse_aqi_response(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not data.get("list"):
            return None
        item = data["list"][0]
        components = item.get("components", {})
        owm_aqi = item.get("main", {}).get("aqi", 1)
        return {
            "aqi": AQI_TO_CN.get(owm_aqi, 300),
            "aqi_level": AQI_LEVEL_MAP.get(owm_aqi, "严重污染"),
            "pm2_5": components.get("pm2_5"),
            "pm10": components.get("pm10"),
            "so2": components.get("so2"),
            "no2": components.get("no2"),
            "co": components.get("co"),
            "o3": components.get("o3"),
        }

    def _parse_current_response(self, data: Dict[str, Any], location: str,
                                 lat: float, lon: float) -> CurrentWeather:
        return CurrentWeather(
            location=location,
            latitude=lat,
            longitude=lon,
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

    async def get_aqi_by_coords(self, latitude: float, longitude: float) -> Optional[dict]:
        data = await self._api_get("/air_pollution", {"lat": latitude, "lon": longitude})
        return self._parse_aqi_response(data) if data else None

    async def get_aqi_by_city(self, city: str, country: str = "CN") -> Optional[dict]:
        coords = await self._resolve_city(city, country)
        if not coords:
            return None
        return await self.get_aqi_by_coords(coords[0], coords[1])

    async def _resolve_city(self, city: str, country: str) -> Optional[tuple]:
        data = await self._api_get("/weather", {"q": f"{city},{country}"})
        if not data:
            return None
        return data["coord"]["lat"], data["coord"]["lon"]

    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        data = await self._api_get("/weather", {"q": f"{city},{country}"})
        if not data:
            return None
        return self._parse_current_response(data, city, data["coord"]["lat"], data["coord"]["lon"])

    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        data = await self._api_get("/weather", {"lat": latitude, "lon": longitude})
        if not data:
            return None
        location = data.get("name", f"({latitude:.2f}, {longitude:.2f})")
        return self._parse_current_response(data, location, latitude, longitude)

    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        coords = await self._resolve_city(city, country)
        if not coords:
            return None
        return await self.get_forecast_by_coords(coords[0], coords[1], days)

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        cnt = min(days * 8, 40)
        data = await self._api_get("/forecast", {"lat": latitude, "lon": longitude, "cnt": cnt})
        if not data:
            return None
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
                latitude=latitude,
                longitude=longitude,
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

    async def get_history_by_city(self, city: str, start_date: date, end_date: date,
                                  country: str = "CN") -> List[WeatherHistoryRecord]:
        return []

    async def get_history_by_coords(self, latitude: float, longitude: float,
                                    start_date: date, end_date: date) -> List[WeatherHistoryRecord]:
        return []

    async def is_available(self) -> bool:
        if not self.api_key:
            return False
        data = await self._api_get("/weather", {"q": "Beijing"}, timeout=5.0, max_retries=1)
        return data is not None
