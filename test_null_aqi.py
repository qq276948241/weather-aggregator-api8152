import asyncio
import sys
import uuid
from datetime import datetime

sys.path.insert(0, ".")

from app.services.briefing import BriefingService, RouteRawData
from app.schemas.schemas import CurrentWeather, WeatherAlertCheck


async def test_null_aqi_briefing():
    print("=" * 60)
    print("测试: AQI 为空时简报不崩溃")
    print("=" * 60)

    from app.database import SessionLocal
    from app import crud, models
    db = SessionLocal()

    fleet_name = f"null_aqi_test_{uuid.uuid4().hex[:6]}"
    fleet = crud.create_fleet(db, models.Fleet(name=fleet_name, description="null aqi test"))
    route = crud.create_route_segment(db, models.RouteSegment(
        name="test-route", start_city="测试城市A", end_city="测试城市B",
        start_latitude=30.0, start_longitude=110.0,
        end_latitude=31.0, end_longitude=111.0, distance_km=100.0,
    ))
    crud.create_fleet_route(db, models.FleetRoute(fleet_id=fleet.id, route_segment_id=route.id))

    svc = BriefingService(db)

    raw = RouteRawData(
        start_weather=CurrentWeather(
            location="测试城市A", latitude=30.0, longitude=110.0,
            data_source="mock", observed_at=datetime.now(),
            temperature=25.0, humidity=60.0, aqi=None, aqi_level=None,
        ),
        end_weather=None,
        start_forecast=None,
        end_forecast=None,
        start_alerts=WeatherAlertCheck(
            location="测试城市A", latitude=30.0, longitude=110.0,
            triggered=False, alerts=[],
        ),
        end_alerts=None,
    )

    risk = svc._assess_risk(route, raw)
    print(f"  risk_level: {risk.risk_level}")
    print(f"  alerts_count: {risk.alerts_count}")
    print(f"  air_quality_warning: {risk.air_quality_warning}")

    result = svc._format_route_result(route, raw, risk)
    print(f"  start_air_quality: {result['start_air_quality']}")
    print(f"  end_air_quality: {result['end_air_quality']}")
    print(f"  air_quality_warning: {result['air_quality_warning']}")

    assert result["start_air_quality"] is None
    assert result["end_air_quality"] is None
    assert result["air_quality_warning"] is False
    assert risk.risk_level == "low"

    print()
    print("  ✅ AQI 为空时简报不崩溃，正确处理空值！")
    db.close()


asyncio.run(test_null_aqi_briefing())
