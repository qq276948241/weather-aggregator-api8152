import logging
from datetime import datetime, date
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app import crud, models
from app.services.weather_service import WeatherService
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


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
        details: Dict[str, Any] = {
            "fleet_name": fleet.name,
            "date": briefing_date.isoformat(),
            "routes": [],
            "summary_points": [],
        }
        alerts_count = 0
        for route in routes:
            route_info = await self._analyze_route(route)
            details["routes"].append(route_info)
            alerts_count += route_info.get("alerts_count", 0)
        summary = self._build_summary(fleet.name, briefing_date, details, alerts_count)
        details["summary_points"] = self._build_summary_points(details, alerts_count)
        briefing = crud.create_weather_briefing(
            self.db, fleet_id=fleet_id,
            briefing_date=datetime.combine(briefing_date, datetime.min.time()),
            summary=summary, details=details, alerts_count=alerts_count,
        )
        logger.info(f"Generated briefing for fleet {fleet.name}: {alerts_count} alerts")
        return briefing

    async def _analyze_route(self, route: models.RouteSegment) -> Dict[str, Any]:
        result = {
            "route_id": route.id,
            "route_name": route.name,
            "start_city": route.start_city,
            "end_city": route.end_city,
            "start_weather": None,
            "end_weather": None,
            "forecast": [],
            "alerts_count": 0,
            "risk_level": "low",
            "recommendation": "",
        }
        try:
            start_w = await self.weather_service.get_current_by_city(route.start_city)
            result["start_weather"] = start_w.model_dump() if start_w else None
            end_w = await self.weather_service.get_current_by_city(route.end_city)
            result["end_weather"] = end_w.model_dump() if end_w else None
            start_fc = await self.weather_service.get_forecast_by_city(route.start_city, days=3)
            if start_fc:
                result["forecast"].append({"city": route.start_city,
                                           "days": [d.model_dump() for d in start_fc.days]})
            end_fc = await self.weather_service.get_forecast_by_city(route.end_city, days=3)
            if end_fc:
                result["forecast"].append({"city": route.end_city,
                                           "days": [d.model_dump() for d in end_fc.days]})
            alert_check_start = await self.weather_service.check_alerts(
                route.start_city, route.start_latitude, route.start_longitude
            )
            alert_check_end = await self.weather_service.check_alerts(
                route.end_city, route.end_latitude, route.end_longitude
            )
            result["alerts_count"] = len(alert_check_start.alerts) + len(alert_check_end.alerts)
            if result["alerts_count"] > 0:
                result["risk_level"] = "high"
                result["recommendation"] = "建议调整运输计划或加强温湿度监控，必要时改道行驶"
            elif self._forecast_has_risk(start_fc) or self._forecast_has_risk(end_fc):
                result["risk_level"] = "medium"
                result["recommendation"] = "未来三天有天气变化风险，请保持关注并准备应急方案"
            else:
                result["risk_level"] = "low"
                result["recommendation"] = "沿途天气良好，适合冷链运输，按原计划执行即可"
        except Exception as e:
            logger.error(f"Failed to analyze route {route.id}: {e}")
        return result

    def _forecast_has_risk(self, forecast) -> bool:
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
        parts = [
            f"【{fleet_name}】{b_date.isoformat()} 冷链运输天气简报",
            f"共覆盖 {route_count} 条运输路线。",
        ]
        if alerts_count > 0:
            parts.append(f"当前触发 {alerts_count} 条气象预警，")
        if high_risk > 0:
            parts.append(f"其中 {high_risk} 条路线为高风险，")
        if medium_risk > 0:
            parts.append(f"{medium_risk} 条路线为中风险。")
        if high_risk == 0 and medium_risk == 0 and alerts_count == 0:
            parts.append("所有路线天气良好，适合冷链运输。")
        else:
            parts.append("请重点关注高风险路段，合理安排运输时间和应急预案。")
        return "".join(parts)

    def _build_summary_points(self, details: Dict[str, Any], alerts_count: int) -> List[str]:
        points = []
        for r in details.get("routes", []):
            if r.get("risk_level") != "low":
                points.append(f"{r['route_name']}: {r.get('recommendation', '')}")
        if not points and alerts_count == 0:
            points.append("所有路线天气状况良好，冷链运输可正常进行。")
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
            city = crud.get_city(self.db, sub.scope_id)
            if not city:
                return None
            current = await self.weather_service.get_current_by_city(city.name)
            forecast = await self.weather_service.get_forecast_by_city(city.name, days=3)
            alert_check = await self.weather_service.check_alerts(city.name, city.latitude, city.longitude)
            content["data"] = {
                "city": city.name,
                "current": current.model_dump() if current else None,
                "forecast_3d": [d.model_dump() for d in forecast.days] if forecast else [],
                "alerts": [a.model_dump() for a in alert_check.alerts],
            }
        elif sub.scope_type == "route":
            route = crud.get_route_segment(self.db, sub.scope_id)
            if not route:
                return None
            start_w = await self.weather_service.get_current_by_city(route.start_city)
            end_w = await self.weather_service.get_current_by_city(route.end_city)
            alert_check_start = await self.weather_service.check_alerts(
                route.start_city, route.start_latitude, route.start_longitude
            )
            alert_check_end = await self.weather_service.check_alerts(
                route.end_city, route.end_latitude, route.end_longitude
            )
            content["data"] = {
                "route_name": route.name,
                "start_city": route.start_city,
                "end_city": route.end_city,
                "start_weather": start_w.model_dump() if start_w else None,
                "end_weather": end_w.model_dump() if end_w else None,
                "alerts": [a.model_dump() for a in alert_check_start.alerts + alert_check_end.alerts],
            }
        elif sub.scope_type == "fleet":
            from app.services.briefing import BriefingService
            briefing_svc = BriefingService(self.db)
            briefing = await briefing_svc.generate_fleet_briefing(sub.scope_id)
            if not briefing:
                return None
            content["data"] = {
                "briefing_id": briefing.id,
                "summary": briefing.summary,
                "alerts_count": briefing.alerts_count,
                "details": briefing.details,
            }
        else:
            return None
        return content
