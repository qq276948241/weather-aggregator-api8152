from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date
from app.database import get_db
from app.schemas.schemas import (
    CurrentWeather, WeatherForecast, WeatherHistoryRecord, WeatherComparison,
    WeatherAlertCheck, ProviderStatus
)
from app.services.weather_service import WeatherService

router = APIRouter(prefix="/weather", tags=["weather"])


@router.get("/current/city", response_model=Optional[CurrentWeather])
async def get_current_by_city(
    city: str = Query(..., description="城市名称"),
    country: str = Query("CN", description="国家代码"),
    provider: Optional[str] = Query(None, description="指定数据源，如mock/openweathermap/qweather"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    include_aqi: bool = Query(True, description="是否包含空气质量数据"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_current_by_city(city, provider_name=provider,
                                            use_cache=use_cache, include_aqi=include_aqi)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取当前天气数据，请检查城市名或数据源配置")
    return result


@router.get("/current/coords", response_model=Optional[CurrentWeather])
async def get_current_by_coords(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    include_aqi: bool = Query(True, description="是否包含空气质量数据"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_current_by_coords(latitude, longitude, provider_name=provider,
                                              use_cache=use_cache, include_aqi=include_aqi)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取当前天气数据")
    return result


@router.get("/aqi/city")
async def get_aqi_by_city(
    city: str = Query(..., description="城市名称"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_aqi_by_city(city, provider_name=provider, use_cache=use_cache)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取空气质量数据")
    return result


@router.get("/aqi/coords")
async def get_aqi_by_coords(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_aqi_by_coords(latitude, longitude, provider_name=provider, use_cache=use_cache)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取空气质量数据")
    return result


@router.get("/forecast/city", response_model=Optional[WeatherForecast])
async def get_forecast_by_city(
    city: str = Query(..., description="城市名称"),
    days: int = Query(7, ge=1, le=15, description="预报天数"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    include_aqi: bool = Query(True, description="是否包含空气质量数据"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_forecast_by_city(city, days=days, provider_name=provider,
                                            use_cache=use_cache, include_aqi=include_aqi)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取天气预报数据")
    return result


@router.get("/forecast/coords", response_model=Optional[WeatherForecast])
async def get_forecast_by_coords(
    latitude: float = Query(..., description="纬度"),
    longitude: float = Query(..., description="经度"),
    days: int = Query(7, ge=1, le=15, description="预报天数"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    use_cache: bool = Query(True, description="是否使用缓存"),
    include_aqi: bool = Query(True, description="是否包含空气质量数据"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    result = await svc.get_forecast_by_coords(latitude, longitude, days=days, provider_name=provider,
                                              use_cache=use_cache, include_aqi=include_aqi)
    if result is None:
        raise HTTPException(status_code=404, detail="无法获取天气预报数据")
    return result


@router.get("/history", response_model=List[WeatherHistoryRecord])
async def get_weather_history(
    location: Optional[str] = Query(None, description="地点名称"),
    latitude: Optional[float] = Query(None, description="纬度"),
    longitude: Optional[float] = Query(None, description="经度"),
    start_date: Optional[date] = Query(None, description="开始日期"),
    end_date: Optional[date] = Query(None, description="结束日期"),
    provider: Optional[str] = Query(None, description="指定数据源"),
    fetch_online: bool = Query(True, description="是否从数据源在线获取"),
    db: Session = Depends(get_db),
):
    if not location and (latitude is None or longitude is None):
        raise HTTPException(status_code=400, detail="请提供地点名称或经纬度")
    svc = WeatherService(db)
    return await svc.get_history(
        location=location, latitude=latitude, longitude=longitude,
        start_date=start_date, end_date=end_date, provider_name=provider,
        fetch_from_provider=fetch_online,
    )


@router.get("/compare", response_model=WeatherComparison)
async def compare_providers(
    location: Optional[str] = Query(None, description="地点名称"),
    city: Optional[str] = Query(None, description="城市名称（location的别名）"),
    latitude: Optional[float] = Query(None, description="纬度"),
    longitude: Optional[float] = Query(None, description="经度"),
    db: Session = Depends(get_db),
):
    loc = location or city
    if not loc and (latitude is None or longitude is None):
        raise HTTPException(status_code=400, detail="请提供地点或经纬度")
    svc = WeatherService(db)
    return await svc.compare_providers(loc, latitude, longitude)


@router.get("/alerts/check", response_model=WeatherAlertCheck)
async def check_weather_alerts(
    location: str = Query(..., description="地点名称"),
    latitude: Optional[float] = Query(None, description="纬度"),
    longitude: Optional[float] = Query(None, description="经度"),
    db: Session = Depends(get_db),
):
    svc = WeatherService(db)
    return await svc.check_alerts(location, latitude, longitude)


@router.get("/providers/status", response_model=List[ProviderStatus])
async def get_provider_status(db: Session = Depends(get_db)):
    svc = WeatherService(db)
    return await svc.check_provider_status()
