import random
import hashlib
from datetime import datetime, date, timedelta
from typing import Optional, List
from app.providers.base import WeatherProvider
from app.schemas.schemas import CurrentWeather, WeatherForecast, ForecastDay, WeatherHistoryRecord


class MockWeatherProvider(WeatherProvider):
    name = "mock"

    def __init__(self):
        super().__init__(api_key=None, base_url=None)

    def _seed_from(self, *parts) -> int:
        key = ":".join(str(p) for p in parts)
        return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2**32)

    def _aqi_level(self, aqi: int) -> str:
        if aqi <= 50:
            return "优"
        if aqi <= 100:
            return "良"
        if aqi <= 150:
            return "轻度污染"
        if aqi <= 200:
            return "中度污染"
        if aqi <= 300:
            return "重度污染"
        return "严重污染"

    def _generate_aqi(self, lat: float, lon: float, seed_offset: str = "") -> dict:
        seed = self._seed_from(lat, lon, datetime.now().date().isoformat(), "aqi", seed_offset)
        rng = random.Random(seed)
        aqi = rng.randint(20, 280)
        return {
            "aqi": aqi,
            "aqi_level": self._aqi_level(aqi),
            "pm2_5": round(rng.uniform(5, 200), 1),
            "pm10": round(rng.uniform(10, 250), 1),
            "so2": round(rng.uniform(2, 80), 1),
            "no2": round(rng.uniform(10, 120), 1),
            "co": round(rng.uniform(0.2, 2.5), 2),
            "o3": round(rng.uniform(20, 180), 1),
        }

    def _generate_current(self, location: str, lat: float, lon: float,
                          seed_offset: str = "") -> CurrentWeather:
        seed = self._seed_from(location, lat, lon, datetime.now().date().isoformat(), seed_offset)
        rng = random.Random(seed)
        conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨", "小雪", "雾", "霾"]
        aqi_data = self._generate_aqi(lat, lon, seed_offset)
        return CurrentWeather(
            location=location,
            latitude=lat,
            longitude=lon,
            data_source=self.name,
            observed_at=datetime.now(),
            temperature=round(rng.uniform(-10, 38), 1),
            humidity=rng.randint(20, 98),
            wind_speed=round(rng.uniform(0, 20), 1),
            wind_direction=rng.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
            precipitation=round(rng.uniform(0, 80), 1),
            pressure=round(rng.uniform(980, 1030), 1),
            weather_condition=rng.choice(conditions),
            feels_like=round(rng.uniform(-15, 42), 1),
            visibility=round(rng.uniform(0.5, 30), 1),
            uv_index=round(rng.uniform(0, 12), 1),
            **aqi_data,
        )

    def _generate_forecast(self, location: str, lat: float, lon: float, days: int) -> WeatherForecast:
        seed = self._seed_from(location, lat, lon, "forecast", days)
        rng = random.Random(seed)
        conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨", "小雪", "雾", "霾"]
        today = datetime.now().date()
        forecast_days: List[ForecastDay] = []
        base_temp = rng.uniform(0, 30)
        for i in range(days):
            d = today + timedelta(days=i)
            temp_variation = rng.uniform(-5, 5)
            temp_max = base_temp + temp_variation + rng.uniform(3, 8)
            temp_min = base_temp + temp_variation - rng.uniform(3, 8)
            forecast_days.append(ForecastDay(
                date=d,
                latitude=lat,
                longitude=lon,
                temperature=round((temp_max + temp_min) / 2, 1),
                temp_min=round(temp_min, 1),
                temp_max=round(temp_max, 1),
                humidity=rng.randint(30, 95),
                wind_speed=round(rng.uniform(0, 18), 1),
                wind_direction=rng.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
                precipitation=round(rng.uniform(0, 60), 1),
                precipitation_probability=rng.randint(0, 100),
                pressure=round(rng.uniform(985, 1025), 1),
                weather_condition=rng.choice(conditions),
                sunrise=datetime.combine(d, datetime.min.time().replace(hour=5, minute=rng.randint(0, 59))),
                sunset=datetime.combine(d, datetime.min.time().replace(hour=18, minute=rng.randint(0, 59))),
            ))
        return WeatherForecast(
            location=location,
            latitude=lat,
            longitude=lon,
            data_source=self.name,
            days=forecast_days,
        )

    async def get_current_by_city(self, city: str, country: str = "CN") -> Optional[CurrentWeather]:
        lat_lon_map = {
            "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
            "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
            "成都": (30.5728, 104.0668), "杭州": (30.2741, 120.1551),
            "武汉": (30.5928, 114.3055), "西安": (34.3416, 108.9398),
            "南京": (32.0603, 118.7969), "重庆": (29.4316, 106.9123),
        }
        lat, lon = lat_lon_map.get(city, (30.0, 110.0))
        return self._generate_current(city, lat, lon)

    async def get_current_by_coords(self, latitude: float, longitude: float) -> Optional[CurrentWeather]:
        location = f"({latitude:.2f}, {longitude:.2f})"
        return self._generate_current(location, latitude, longitude)

    async def get_forecast_by_city(self, city: str, days: int = 7, country: str = "CN") -> Optional[WeatherForecast]:
        lat_lon_map = {
            "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
            "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
            "成都": (30.5728, 104.0668), "杭州": (30.2741, 120.1551),
            "武汉": (30.5928, 114.3055), "西安": (34.3416, 108.9398),
            "南京": (32.0603, 118.7969), "重庆": (29.4316, 106.9123),
        }
        lat, lon = lat_lon_map.get(city, (30.0, 110.0))
        return self._generate_forecast(city, lat, lon, days)

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7) -> Optional[WeatherForecast]:
        location = f"({latitude:.2f}, {longitude:.2f})"
        return self._generate_forecast(location, latitude, longitude, days)

    async def get_aqi_by_coords(self, latitude: float, longitude: float) -> Optional[dict]:
        return self._generate_aqi(latitude, longitude)

    async def get_aqi_by_city(self, city: str, country: str = "CN") -> Optional[dict]:
        lat_lon_map = {
            "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
            "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
            "成都": (30.5728, 104.0668), "杭州": (30.2741, 120.1551),
            "武汉": (30.5928, 114.3055), "西安": (34.3416, 108.9398),
            "南京": (32.0603, 118.7969), "重庆": (29.4316, 106.9123),
        }
        lat, lon = lat_lon_map.get(city, (30.0, 110.0))
        return await self.get_aqi_by_coords(lat, lon)

    async def get_history_by_city(self, city: str, start_date: date, end_date: date,
                                  country: str = "CN") -> List[WeatherHistoryRecord]:
        lat_lon_map = {
            "北京": (39.9042, 116.4074), "上海": (31.2304, 121.4737),
            "广州": (23.1291, 113.2644), "深圳": (22.5431, 114.0579),
        }
        lat, lon = lat_lon_map.get(city, (30.0, 110.0))
        return await self.get_history_by_coords(lat, lon, start_date, end_date)

    async def get_history_by_coords(self, latitude: float, longitude: float,
                                    start_date: date, end_date: date) -> List[WeatherHistoryRecord]:
        records: List[WeatherHistoryRecord] = []
        conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨", "小雪", "雾", "霾"]
        delta = (end_date - start_date).days + 1
        for i in range(min(delta, 365)):
            d = start_date + timedelta(days=i)
            seed = self._seed_from(latitude, longitude, d.isoformat(), "history")
            rng = random.Random(seed)
            aqi_data = self._generate_aqi(latitude, longitude, d.isoformat())
            records.append(WeatherHistoryRecord(
                location=f"({latitude:.2f}, {longitude:.2f})",
                latitude=latitude,
                longitude=longitude,
                record_date=datetime.combine(d, datetime.min.time().replace(hour=12)),
                temperature=round(rng.uniform(-15, 40), 1),
                humidity=rng.randint(20, 98),
                wind_speed=round(rng.uniform(0, 20), 1),
                wind_direction=rng.choice(["北", "东北", "东", "东南", "南", "西南", "西", "西北"]),
                precipitation=round(rng.uniform(0, 80), 1),
                pressure=round(rng.uniform(980, 1030), 1),
                weather_condition=rng.choice(conditions),
                data_source=self.name,
                **aqi_data,
            ))
        return records

    async def is_available(self) -> bool:
        return True
