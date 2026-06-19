import logging
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app import crud, models
from app.services.weather_service import WeatherService
from app.schemas.schemas import CurrentWeather, WeatherForecast

logger = logging.getLogger(__name__)


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.weather_service = WeatherService(db)

    async def run_global_alert_check(self) -> List[models.AlertRecord]:
        cities = crud.get_cities(self.db, limit=500)
        all_triggered = []
        for city in cities:
            try:
                result = await self.weather_service.check_alerts(
                    city.name, city.latitude, city.longitude
                )
                all_triggered.extend(result.alerts)
            except Exception as e:
                logger.error(f"Alert check failed for {city.name}: {e}")
        routes = crud.get_route_segments(self.db, limit=500)
        for route in routes:
            try:
                start_result = await self.weather_service.check_alerts(
                    f"{route.start_city}", route.start_latitude, route.start_longitude
                )
                all_triggered.extend(start_result.alerts)
                end_result = await self.weather_service.check_alerts(
                    f"{route.end_city}", route.end_latitude, route.end_longitude
                )
                all_triggered.extend(end_result.alerts)
            except Exception as e:
                logger.error(f"Alert check failed for route {route.id}: {e}")
        return all_triggered

    async def check_route_alerts(self, route_id: int) -> List[Dict[str, Any]]:
        route = crud.get_route_segment(self.db, route_id)
        if not route:
            return []
        results = []
        try:
            start_check = await self.weather_service.check_alerts(
                route.start_city, route.start_latitude, route.start_longitude
            )
            if start_check.triggered:
                results.append({"point": "start", "city": route.start_city, "alerts": start_check.alerts})
            end_check = await self.weather_service.check_alerts(
                route.end_city, route.end_latitude, route.end_longitude
            )
            if end_check.triggered:
                results.append({"point": "end", "city": route.end_city, "alerts": end_check.alerts})
            mid_lat = (route.start_latitude + route.end_latitude) / 2
            mid_lon = (route.start_longitude + route.end_longitude) / 2
            mid_check = await self.weather_service.check_alerts(
                f"{route.start_city}-{route.end_city}中点", mid_lat, mid_lon
            )
            if mid_check.triggered:
                results.append({"point": "mid", "city": "路线中点", "alerts": mid_check.alerts})
        except Exception as e:
            logger.error(f"Route alert check failed for route {route_id}: {e}")
        return results

    async def check_fleet_alerts(self, fleet_id: int) -> List[Dict[str, Any]]:
        fleet = crud.get_fleet(self.db, fleet_id)
        if not fleet:
            return []
        results = []
        routes = crud.get_fleet_routes(self.db, fleet_id)
        for route in routes:
            route_alerts = await self.check_route_alerts(route.id)
            if route_alerts:
                results.append({"route_id": route.id, "route_name": route.name, "alerts": route_alerts})
        return results

    def ensure_default_rules(self) -> None:
        from app.config import settings
        existing = {(r.alert_type, r.scope_type, r.scope_id) for r in crud.get_alert_rules(self.db)}
        defaults = [
            ("高温预警", "high_temperature", settings.ALERT_HIGH_TEMP_THRESHOLD, "gt",
             ["log", "console"], "当气温超过阈值时触发，可能影响冷链货物品质"),
            ("低温预警", "low_temperature", settings.ALERT_LOW_TEMP_THRESHOLD, "lt",
             ["log", "console"], "当气温低于阈值时触发，防止冻损"),
            ("暴雨预警", "heavy_rain", settings.ALERT_HEAVY_RAIN_THRESHOLD, "gt",
             ["log", "console"], "当降水量超过阈值时触发，注意运输安全"),
        ]
        for name, atype, threshold, comp, channels, desc in defaults:
            key = (atype, "global", None)
            if key in existing:
                continue
            from app.schemas.schemas import AlertRuleCreate
            crud.create_alert_rule(self.db, AlertRuleCreate(
                name=name, alert_type=atype, threshold_value=threshold,
                comparison=comp, notify_channels=channels, description=desc,
            ))
            logger.info(f"Created default alert rule: {name}")
