import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.providers.factory import get_all_providers, get_provider, get_available_providers
from app.providers.base import WeatherProvider
from app.cache.cache import get_cache, make_cache_key
from app.schemas.schemas import (
    CurrentWeather, WeatherForecast, WeatherHistoryRecord, WeatherComparison,
    WeatherAlertCheck, AlertRecordBase, ProviderStatus
)
from app import crud
from app.config import settings

logger = logging.getLogger(__name__)


class WeatherService:
    def __init__(self, db: Session):
        self.db = db
        self.cache = get_cache()

    async def get_current_by_city(self, city: str, provider_name: Optional[str] = None,
                                  use_cache: bool = True) -> Optional[CurrentWeather]:
        cache_key = make_cache_key("weather", "current", "city", city, provider=provider_name or "all")
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        providers = self._get_providers(provider_name)
        last_error = None
        for p in providers:
            try:
                result = await p.get_current_by_city(city)
                if result:
                    if use_cache:
                        self.cache.set(cache_key, result)
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {p.name} failed for city {city}: {e}")
        if last_error:
            logger.error(f"All providers failed for city {city}: {last_error}")
        return None

    async def get_current_by_coords(self, latitude: float, longitude: float,
                                    provider_name: Optional[str] = None,
                                    use_cache: bool = True) -> Optional[CurrentWeather]:
        cache_key = make_cache_key("weather", "current", "coords", f"{latitude:.4f}", f"{longitude:.4f}",
                                    provider=provider_name or "all")
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        providers = self._get_providers(provider_name)
        last_error = None
        for p in providers:
            try:
                result = await p.get_current_by_coords(latitude, longitude)
                if result:
                    if use_cache:
                        self.cache.set(cache_key, result)
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {p.name} failed for coords {latitude},{longitude}: {e}")
        if last_error:
            logger.error(f"All providers failed for coords {latitude},{longitude}: {last_error}")
        return None

    async def get_forecast_by_city(self, city: str, days: int = 7,
                                   provider_name: Optional[str] = None,
                                   use_cache: bool = True) -> Optional[WeatherForecast]:
        cache_key = make_cache_key("weather", "forecast", "city", city, days=str(days),
                                    provider=provider_name or "all")
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        providers = self._get_providers(provider_name)
        last_error = None
        for p in providers:
            try:
                result = await p.get_forecast_by_city(city, days=days)
                if result:
                    if use_cache:
                        self.cache.set(cache_key, result)
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {p.name} forecast failed for city {city}: {e}")
        if last_error:
            logger.error(f"All providers forecast failed for city {city}: {last_error}")
        return None

    async def get_forecast_by_coords(self, latitude: float, longitude: float, days: int = 7,
                                     provider_name: Optional[str] = None,
                                     use_cache: bool = True) -> Optional[WeatherForecast]:
        cache_key = make_cache_key("weather", "forecast", "coords", f"{latitude:.4f}", f"{longitude:.4f}",
                                    days=str(days), provider=provider_name or "all")
        if use_cache:
            cached = self.cache.get(cache_key)
            if cached:
                return cached
        providers = self._get_providers(provider_name)
        last_error = None
        for p in providers:
            try:
                result = await p.get_forecast_by_coords(latitude, longitude, days=days)
                if result:
                    if use_cache:
                        self.cache.set(cache_key, result)
                    return result
            except Exception as e:
                last_error = e
                logger.warning(f"Provider {p.name} forecast failed: {e}")
        if last_error:
            logger.error(f"All providers forecast failed: {last_error}")
        return None

    async def get_history(self, location: Optional[str] = None,
                          latitude: Optional[float] = None,
                          longitude: Optional[float] = None,
                          start_date: Optional[date] = None,
                          end_date: Optional[date] = None,
                          provider_name: Optional[str] = None,
                          fetch_from_provider: bool = True,
                          use_cache: bool = True) -> List[WeatherHistoryRecord]:
        db_records = crud.get_weather_history(
            self.db, location=location, latitude=latitude, longitude=longitude,
            start_date=start_date, end_date=end_date, data_source=provider_name
        )
        results = [WeatherHistoryRecord.model_validate(r) for r in db_records]
        if fetch_from_provider and latitude is not None and longitude is not None \
                and start_date and end_date:
            cache_key = make_cache_key("weather", "history", f"{latitude:.4f}", f"{longitude:.4f}",
                                        start=start_date.isoformat(), end=end_date.isoformat(),
                                        provider=provider_name or "all")
            cached = self.cache.get(cache_key) if use_cache else None
            if cached:
                return cached
            providers = self._get_providers(provider_name)
            for p in providers:
                try:
                    provider_records = await p.get_history_by_coords(
                        latitude, longitude, start_date, end_date
                    )
                    if provider_records:
                        for rec in provider_records:
                            crud.save_weather_history(self.db, rec)
                        results.extend(provider_records)
                        if use_cache:
                            self.cache.set(cache_key, results)
                        break
                except Exception as e:
                    logger.warning(f"Provider {p.name} history failed: {e}")
        return results

    async def compare_providers(self, location: Optional[str] = None,
                                latitude: Optional[float] = None,
                                longitude: Optional[float] = None) -> WeatherComparison:
        if location and (latitude is None or longitude is None):
            city = crud.get_city_by_name(self.db, location)
            if city:
                latitude, longitude = city.latitude, city.longitude
        if latitude is None or longitude is None:
            latitude, longitude = 30.0, 110.0
        results: Dict[str, CurrentWeather] = {}
        providers = get_all_providers()
        for p in providers:
            try:
                w = await p.get_current_by_coords(latitude, longitude)
                if w:
                    results[p.name] = w
            except Exception as e:
                logger.warning(f"Compare provider {p.name} failed: {e}")
        temp_diff: Dict[str, float] = {}
        hum_diff: Dict[str, float] = {}
        if len(results) >= 2:
            items = list(results.values())
            base_temp = items[0].temperature
            base_hum = items[0].humidity
            for name, w in results.items():
                if base_temp is not None and w.temperature is not None:
                    temp_diff[name] = round(w.temperature - base_temp, 1)
                if base_hum is not None and w.humidity is not None:
                    hum_diff[name] = round(w.humidity - base_hum, 1)
        return WeatherComparison(
            location=location or f"({latitude:.2f}, {longitude:.2f})",
            latitude=latitude,
            longitude=longitude,
            query_time=datetime.now(),
            results=results,
            temperature_diff=temp_diff or None,
            humidity_diff=hum_diff or None,
        )

    async def check_alerts(self, location: str, latitude: Optional[float] = None,
                           longitude: Optional[float] = None) -> WeatherAlertCheck:
        weather = await self.get_current_by_city(location)
        if not weather and latitude is not None and longitude is not None:
            weather = await self.get_current_by_coords(latitude, longitude)
        if latitude is None and weather:
            latitude, longitude = weather.latitude, weather.longitude
        triggered_alerts: List[AlertRecordBase] = []
        rules = crud.get_alert_rules(self.db, enabled=True)
        if weather:
            for rule in rules:
                if not self._rule_applies(rule, location, latitude, longitude):
                    continue
                if self._check_rule(rule, weather):
                    alert = AlertRecordBase(
                        rule_id=rule.id,
                        alert_type=rule.alert_type,
                        location=location,
                        latitude=latitude,
                        longitude=longitude,
                        trigger_value=self._get_alert_value(rule.alert_type, weather),
                        threshold_value=rule.threshold_value,
                        message=self._build_alert_message(rule, weather, location),
                        data_source=weather.data_source,
                    )
                    triggered_alerts.append(alert)
                    db_record = crud.create_alert_record(self.db, alert)
                    from app.services.notification import NotificationService
                    NotificationService.send_alert(self.db, db_record, rule.notify_channels)
        return WeatherAlertCheck(
            location=location,
            latitude=latitude,
            longitude=longitude,
            triggered=len(triggered_alerts) > 0,
            alerts=triggered_alerts,
        )

    async def check_provider_status(self) -> List[ProviderStatus]:
        statuses = []
        for name in get_available_providers():
            try:
                p = get_provider(name)
                available = await p.is_available()
                statuses.append(ProviderStatus(name=name, available=available, last_check=datetime.now()))
            except Exception as e:
                logger.warning(f"Status check failed for {name}: {e}")
                statuses.append(ProviderStatus(name=name, available=False, last_check=datetime.now()))
        return statuses

    def _get_providers(self, provider_name: Optional[str]) -> List[WeatherProvider]:
        if provider_name:
            return [get_provider(provider_name)]
        return get_all_providers()

    def _rule_applies(self, rule, location: str, latitude: Optional[float], longitude: Optional[float]) -> bool:
        if rule.scope_type == "global":
            return True
        if rule.scope_type == "city":
            city = crud.get_city(self.db, rule.scope_id)
            if city and city.name == location:
                return True
        return False

    def _check_rule(self, rule, weather: CurrentWeather) -> bool:
        value = self._get_alert_value(rule.alert_type, weather)
        if value is None:
            return False
        if rule.comparison == "gt":
            return value > rule.threshold_value
        if rule.comparison == "lt":
            return value < rule.threshold_value
        if rule.comparison == "gte":
            return value >= rule.threshold_value
        if rule.comparison == "lte":
            return value <= rule.threshold_value
        if rule.comparison == "eq":
            return value == rule.threshold_value
        return False

    def _get_alert_value(self, alert_type: str, weather: CurrentWeather) -> Optional[float]:
        mapping = {
            "high_temperature": weather.temperature,
            "low_temperature": weather.temperature,
            "heavy_rain": weather.precipitation,
            "high_humidity": weather.humidity,
            "low_humidity": weather.humidity,
            "high_wind": weather.wind_speed,
        }
        return mapping.get(alert_type)

    def _build_alert_message(self, rule, weather: CurrentWeather, location: str) -> str:
        type_names = {
            "high_temperature": "高温",
            "low_temperature": "低温",
            "heavy_rain": "暴雨",
            "high_humidity": "高湿",
            "low_humidity": "低湿",
            "high_wind": "大风",
        }
        tname = type_names.get(rule.alert_type, rule.alert_type)
        val = self._get_alert_value(rule.alert_type, weather)
        return f"【{tname}预警】{location} 当前{self._metric_name(rule.alert_type)}{val}，" \
               f"超过阈值{rule.threshold_value}，请注意冷链运输安全！"

    def _metric_name(self, alert_type: str) -> str:
        mapping = {
            "high_temperature": "温度",
            "low_temperature": "温度",
            "heavy_rain": "降水量",
            "high_humidity": "湿度",
            "low_humidity": "湿度",
            "high_wind": "风速",
        }
        return mapping.get(alert_type, "指标")
