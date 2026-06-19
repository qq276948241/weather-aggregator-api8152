import logging
import asyncio
from datetime import datetime, date
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app import crud, models
from app.schemas.schemas import CurrentWeather, WeatherForecast, WeatherAlertCheck
from app.services.weather_service import WeatherService
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


@dataclass
class RouteRawData:
    start_weather: Optional[CurrentWeather]
    end_weather: Optional[CurrentWeather]
    start_forecast: Optional[WeatherForecast]
    end_forecast: Optional[WeatherForecast]
    start_alerts: WeatherAlertCheck
    end_alerts: WeatherAlertCheck


@dataclass
class RiskAssessment:
    risk_level: str
    alerts_count: int
    air_quality_warning: bool
    aqi_warning_detail: str
    recommendations: List[str]


@dataclass
class AirQualityInfo:
    aqi: Optional[int]
    aqi_level: Optional[str]
    pm2_5: Optional[float]
    pm10: Optional[float]
    has_warning: bool
    warning_msg: str


class BriefingService:
    def __init__(self, db: Session):
        self.db = db
        self.weather_service = WeatherService(db)

    async def generate_fleet_briefing(self, fleet_id: int,
                                       briefing_date: Optional[date] = None) -> Optional[models.WeatherBriefing]:
        fleet = crud.get_fleet(self.db, fleet_id)
        if not fleet:
            return None
        briefing_date = briefing_date or datetime.now().date()
        routes = crud.get_fleet_routes(self.db, fleet_id)
        details = await self._build_briefing_details(fleet, routes, briefing_date)
        alerts_count = sum(r.get("alerts_count", 0) for r in details["routes"])
        summary = self._build_summary(fleet.name, briefing_date, details, alerts_count)
        details["summary_points"] = self._build_summary_points(details, alerts_count)
        briefing = self._save_briefing(fleet_id, briefing_date, summary, details, alerts_count)
        logger.info(f"Generated briefing for fleet {fleet.name}: {alerts_count} alerts")
        return briefing

    async def _build_briefing_details(self, fleet: models.Fleet,
                                      routes: List[models.RouteSegment],
                                      briefing_date: date) -> Dict[str, Any]:
        details: Dict[str, Any] = {
            "fleet_name": fleet.name,
            "date": briefing_date.isoformat(),
            "routes": [],
            "summary_points": [],
        }
        for route in routes:
            try:
                route_info = await self._analyze_route(route)
                details["routes"].append(route_info)
            except Exception as e:
                logger.error(f"Failed to analyze route {route.id}: {e}")
                details["routes"].append(self._empty_route_result(route))
        return details

    def _save_briefing(self, fleet_id: int, briefing_date: date, summary: str,
                       details: Dict[str, Any], alerts_count: int) -> models.WeatherBriefing:
        return crud.create_weather_briefing(
            self.db, fleet_id=fleet_id,
            briefing_date=datetime.combine(briefing_date, datetime.min.time()),
            summary=summary, details=details, alerts_count=alerts_count,
        )

    def _empty_route_result(self, route: models.RouteSegment) -> Dict[str, Any]:
        return {
            "route_id": route.id,
            "route_name": route.name,
            "start_city": route.start_city,
            "end_city": route.end_city,
            "start_weather": None,
            "end_weather": None,
            "start_air_quality": None,
            "end_air_quality": None,
            "air_quality_warning": False,
            "forecast": [],
            "alerts_count": 0,
            "risk_level": "low",
            "recommendation": "路线数据分析失败，请稍后重试",
        }

    async def _analyze_route(self, route: models.RouteSegment) -> Dict[str, Any]:
        raw_data = await self._fetch_route_data(route)
        risk = self._assess_risk(route, raw_data)
        return self._format_route_result(route, raw_data, risk)

    async def _fetch_route_data(self, route: models.RouteSegment) -> RouteRawData:
        start_w, end_w = await asyncio.gather(
            self._safe_get_current(route.start_city),
            self._safe_get_current(route.end_city),
        )
        start_fc, end_fc = await asyncio.gather(
            self._safe_get_forecast(route.start_city),
            self._safe_get_forecast(route.end_city),
        )
        start_alerts, end_alerts = await asyncio.gather(
            self._safe_check_alerts(route.start_city, route.start_latitude, route.start_longitude),
            self._safe_check_alerts(route.end_city, route.end_latitude, route.end_longitude),
        )
        return RouteRawData(
            start_weather=start_w,
            end_weather=end_w,
            start_forecast=start_fc,
            end_forecast=end_fc,
            start_alerts=start_alerts,
            end_alerts=end_alerts,
        )

    async def _safe_get_current(self, city: str) -> Optional[CurrentWeather]:
        try:
            return await self.weather_service.get_current_by_city(city, include_aqi=True)
        except Exception as e:
            logger.error(f"Failed to get current weather for {city}: {e}")
            return None

    async def _safe_get_forecast(self, city: str) -> Optional[WeatherForecast]:
        try:
            return await self.weather_service.get_forecast_by_city(city, days=3)
        except Exception as e:
            logger.error(f"Failed to get forecast for {city}: {e}")
            return None

    async def _safe_check_alerts(self, city: str, lat: Optional[float],
                                  lon: Optional[float]) -> WeatherAlertCheck:
        try:
            return await self.weather_service.check_alerts(city, lat, lon)
        except Exception as e:
            logger.error(f"Failed to check alerts for {city}: {e}")
            return WeatherAlertCheck(
                location=city, latitude=lat, longitude=lon,
                triggered=False, alerts=[],
            )

    def _assess_risk(self, route: models.RouteSegment, data: RouteRawData) -> RiskAssessment:
        start_alerts = data.start_alerts.alerts if data.start_alerts else []
        end_alerts = data.end_alerts.alerts if data.end_alerts else []
        alerts_count = len(start_alerts) + len(end_alerts)
        start_aqi = self._extract_air_quality(data.start_weather, route.start_city)
        end_aqi = self._extract_air_quality(data.end_weather, route.end_city)
        air_quality_warning = start_aqi.has_warning or end_aqi.has_warning
        aqi_warning_parts = [w.warning_msg for w in [start_aqi, end_aqi] if w.warning_msg]
        aqi_warning_detail = " | ".join(aqi_warning_parts) if aqi_warning_parts else ""

        recommendations: List[str] = []
        risk_level = "low"

        if alerts_count > 0:
            risk_level = "high"
            recommendations.append("建议调整运输计划或加强温湿度监控，必要时改道行驶")
        elif self._forecast_has_risk(data.start_forecast) or self._forecast_has_risk(data.end_forecast):
            risk_level = "medium"
            recommendations.append("未来三天有天气变化风险，请保持关注并准备应急方案")

        if air_quality_warning:
            if risk_level != "high":
                risk_level = "medium"
            if start_aqi.has_warning:
                recommendations.append(f"【{route.start_city} AQI={start_aqi.aqi} 红色预警】请关闭车窗减少通风")
            if end_aqi.has_warning:
                recommendations.append(f"【{route.end_city} AQI={end_aqi.aqi} 红色预警】请关闭车窗减少通风")
            recommendations.append("加强冷链货箱密封，防止外部污染空气进入影响生鲜品质")

        if not recommendations:
            recommendations.append("沿途天气及空气质量良好，适合冷链运输，按原计划执行即可")

        return RiskAssessment(
            risk_level=risk_level,
            alerts_count=alerts_count,
            air_quality_warning=air_quality_warning,
            aqi_warning_detail=aqi_warning_detail,
            recommendations=recommendations,
        )

    def _extract_air_quality(self, weather: Optional[CurrentWeather], city: str) -> AirQualityInfo:
        if not weather or weather.aqi is None:
            return AirQualityInfo(None, None, None, None, False, "")
        has_warning = weather.aqi > 150
        warning_msg = f"{city} AQI={weather.aqi}({weather.aqi_level})，已达中度污染及以上" if has_warning else ""
        return AirQualityInfo(
            aqi=weather.aqi,
            aqi_level=weather.aqi_level,
            pm2_5=weather.pm2_5,
            pm10=weather.pm10,
            has_warning=has_warning,
            warning_msg=warning_msg,
        )

    def _format_route_result(self, route: models.RouteSegment,
                              data: RouteRawData, risk: RiskAssessment) -> Dict[str, Any]:
        start_aqi = self._extract_air_quality(data.start_weather, route.start_city)
        end_aqi = self._extract_air_quality(data.end_weather, route.end_city)

        forecast = []
        if data.start_forecast:
            forecast.append({"city": route.start_city,
                             "days": [d.model_dump() for d in data.start_forecast.days]})
        if data.end_forecast:
            forecast.append({"city": route.end_city,
                             "days": [d.model_dump() for d in data.end_forecast.days]})

        return {
            "route_id": route.id,
            "route_name": route.name,
            "start_city": route.start_city,
            "end_city": route.end_city,
            "start_weather": data.start_weather.model_dump() if data.start_weather else None,
            "end_weather": data.end_weather.model_dump() if data.end_weather else None,
            "start_air_quality": {
                "aqi": start_aqi.aqi, "aqi_level": start_aqi.aqi_level,
                "pm2_5": start_aqi.pm2_5, "pm10": start_aqi.pm10,
            } if start_aqi.aqi is not None else None,
            "end_air_quality": {
                "aqi": end_aqi.aqi, "aqi_level": end_aqi.aqi_level,
                "pm2_5": end_aqi.pm2_5, "pm10": end_aqi.pm10,
            } if end_aqi.aqi is not None else None,
            "air_quality_warning": risk.air_quality_warning,
            "aqi_warning_detail": risk.aqi_warning_detail,
            "forecast": forecast,
            "alerts_count": risk.alerts_count,
            "risk_level": risk.risk_level,
            "recommendation": " | ".join(risk.recommendations),
        }

    def _forecast_has_risk(self, forecast: Optional[WeatherForecast]) -> bool:
        if not forecast:
            return False
        for d in forecast.days:
            if d.temp_max and d.temp_max > 35:
                return True
            if d.temp_min and d.temp_min < -10:
                return True
            if d.precipitation and d.precipitation > 30:
                return True
        return False

    def _build_summary(self, fleet_name: str, b_date: date, details: Dict[str, Any], alerts_count: int) -> str:
        route_count = len(details.get("routes", []))
        high_risk = sum(1 for r in details.get("routes", []) if r.get("risk_level") == "high")
        medium_risk = sum(1 for r in details.get("routes", []) if r.get("risk_level") == "medium")
        aqi_warning_routes = sum(1 for r in details.get("routes", []) if r.get("air_quality_warning"))
        parts = [
            f"【{fleet_name}】{b_date.isoformat()} 冷链运输天气简报",
            f"共覆盖 {route_count} 条运输路线。",
        ]
        if alerts_count > 0:
            parts.append(f"当前触发 {alerts_count} 条气象预警，")
        if aqi_warning_routes > 0:
            parts.append(f"{aqi_warning_routes} 条路线沿途 AQI 超标需注意，")
        if high_risk > 0:
            parts.append(f"其中 {high_risk} 条路线为高风险，")
        if medium_risk > 0:
            parts.append(f"{medium_risk} 条路线为中风险。")
        if high_risk == 0 and medium_risk == 0 and alerts_count == 0 and aqi_warning_routes == 0:
            parts.append("所有路线天气及空气质量良好，适合冷链运输。")
        else:
            parts.append("请重点关注高风险路段，合理安排运输时间和应急预案。")
        return "".join(parts)

    def _build_summary_points(self, details: Dict[str, Any], alerts_count: int) -> List[str]:
        points = []
        aqi_points = []
        for r in details.get("routes", []):
            if r.get("air_quality_warning") and r.get("aqi_warning_detail"):
                aqi_points.append(
                    f"{r['route_name']}: 【空气质量预警】{r['aqi_warning_detail']}。请关闭车窗减少通风，加强货箱密封。"
                )
            if r.get("risk_level") != "low" and not r.get("air_quality_warning"):
                points.append(f"{r['route_name']}: {r.get('recommendation', '')}")
        points.extend(aqi_points)
        if not points and alerts_count == 0:
            points.append("所有路线天气及空气质量良好，冷链运输可正常进行。")
        return points

    async def generate_all_fleet_briefings(self) -> List[models.WeatherBriefing]:
        fleets = crud.get_fleets(self.db, limit=500)
        results = []
        for fleet in fleets:
            try:
                briefing = await self.generate_fleet_briefing(fleet.id)
                if briefing:
                    results.append(briefing)
            except Exception as e:
                logger.error(f"Failed to generate briefing for fleet {fleet.id}: {e}")
        return results


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.weather_service = WeatherService(db)

    async def process_due_subscriptions(self) -> int:
        now = datetime.now()
        subs = crud.get_subscriptions(self.db, enabled=True)
        processed = 0
        for sub in subs:
            try:
                if sub.last_push_at:
                    elapsed = (now - sub.last_push_at).total_seconds() / 60
                    if elapsed < sub.push_interval_minutes:
                        continue
                content = await self._build_push_content(sub)
                if content:
                    NotificationService.send_subscription_push(self.db, sub, content)
                    processed += 1
            except Exception as e:
                logger.error(f"Failed to process subscription {sub.id}: {e}")
        return processed

    async def _build_push_content(self, sub: models.WeatherSubscription) -> Optional[Dict[str, Any]]:
        content = {
            "subscription_name": sub.name,
            "generated_at": datetime.now().isoformat(),
            "data": {},
        }
        if sub.scope_type == "city":
            content["data"] = await self._build_city_content(sub)
        elif sub.scope_type == "route":
            content["data"] = await self._build_route_content(sub)
        elif sub.scope_type == "fleet":
            content["data"] = await self._build_fleet_content(sub)
        else:
            return None
        return content

    async def _build_city_content(self, sub: models.WeatherSubscription) -> Dict[str, Any]:
        city = crud.get_city(self.db, sub.scope_id)
        if not city:
            return {}
        current = await self.weather_service.get_current_by_city(city.name)
        forecast = await self.weather_service.get_forecast_by_city(city.name, days=3)
        alert_check = await self.weather_service.check_alerts(city.name, city.latitude, city.longitude)
        return {
            "city": city.name,
            "current": current.model_dump() if current else None,
            "forecast_3d": [d.model_dump() for d in forecast.days] if forecast else [],
            "alerts": [a.model_dump() for a in alert_check.alerts],
        }

    async def _build_route_content(self, sub: models.WeatherSubscription) -> Dict[str, Any]:
        route = crud.get_route_segment(self.db, sub.scope_id)
        if not route:
            return {}
        start_w, end_w = await asyncio.gather(
            self.weather_service.get_current_by_city(route.start_city),
            self.weather_service.get_current_by_city(route.end_city),
        )
        start_alerts, end_alerts = await asyncio.gather(
            self.weather_service.check_alerts(route.start_city, route.start_latitude, route.start_longitude),
            self.weather_service.check_alerts(route.end_city, route.end_latitude, route.end_longitude),
        )
        return {
            "route_name": route.name,
            "start_city": route.start_city,
            "end_city": route.end_city,
            "start_weather": start_w.model_dump() if start_w else None,
            "end_weather": end_w.model_dump() if end_w else None,
            "alerts": [a.model_dump() for a in start_alerts.alerts + end_alerts.alerts],
        }

    async def _build_fleet_content(self, sub: models.WeatherSubscription) -> Dict[str, Any]:
        briefing_svc = BriefingService(self.db)
        briefing = await briefing_svc.generate_fleet_briefing(sub.scope_id)
        if not briefing:
            return {}
        return {
            "briefing_id": briefing.id,
            "summary": briefing.summary,
            "alerts_count": briefing.alerts_count,
            "details": briefing.details,
        }
