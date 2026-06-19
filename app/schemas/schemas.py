from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date


class CityBase(BaseModel):
    name: str
    province: Optional[str] = None
    country: str = "中国"
    latitude: float
    longitude: float


class CityCreate(CityBase):
    pass


class City(CityBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class RouteSegmentBase(BaseModel):
    name: str
    start_city: str
    end_city: str
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    waypoints: Optional[List[Dict[str, float]]] = None
    description: Optional[str] = None


class RouteSegmentCreate(RouteSegmentBase):
    pass


class RouteSegment(RouteSegmentBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class FleetBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    description: Optional[str] = None


class FleetCreate(FleetBase):
    route_ids: Optional[List[int]] = None


class Fleet(FleetBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class AlertRuleBase(BaseModel):
    name: str
    alert_type: str
    threshold_value: float
    comparison: str = "gt"
    enabled: bool = True
    scope_type: str = "global"
    scope_id: Optional[int] = None
    notify_channels: List[str] = ["log"]
    description: Optional[str] = None


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleUpdate(BaseModel):
    name: Optional[str] = None
    threshold_value: Optional[float] = None
    enabled: Optional[bool] = None
    notify_channels: Optional[List[str]] = None
    description: Optional[str] = None


class AlertRule(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    updated_at: datetime


class AlertRecordBase(BaseModel):
    rule_id: int
    alert_type: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    trigger_value: float
    threshold_value: float
    message: str
    data_source: Optional[str] = None


class AlertRecord(AlertRecordBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    notified: bool
    created_at: datetime


class WeatherSubscriptionBase(BaseModel):
    name: str
    subscriber_type: str
    subscriber_id: Optional[int] = None
    scope_type: str
    scope_id: int
    push_interval_minutes: int = 30
    enabled: bool = True
    push_channels: List[str] = ["log"]


class WeatherSubscriptionCreate(WeatherSubscriptionBase):
    pass


class WeatherSubscriptionUpdate(BaseModel):
    name: Optional[str] = None
    push_interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None
    push_channels: Optional[List[str]] = None


class WeatherSubscription(WeatherSubscriptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    last_push_at: Optional[datetime] = None
    created_at: datetime


class WeatherDataPoint(BaseModel):
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    precipitation: Optional[float] = None
    pressure: Optional[float] = None
    weather_condition: Optional[str] = None
    feels_like: Optional[float] = None
    visibility: Optional[float] = None
    uv_index: Optional[float] = None


class CurrentWeather(WeatherDataPoint):
    location: str
    latitude: float
    longitude: float
    data_source: str
    observed_at: datetime


class ForecastDay(WeatherDataPoint):
    date: date
    temp_min: Optional[float] = None
    temp_max: Optional[float] = None
    precipitation_probability: Optional[float] = None
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None


class WeatherForecast(BaseModel):
    location: str
    latitude: float
    longitude: float
    data_source: str
    days: List[ForecastDay]


class WeatherHistoryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: Optional[int] = None
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    record_date: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    precipitation: Optional[float] = None
    pressure: Optional[float] = None
    weather_condition: Optional[str] = None
    data_source: Optional[str] = None


class WeatherComparison(BaseModel):
    location: str
    latitude: float
    longitude: float
    query_time: datetime
    results: Dict[str, CurrentWeather]
    temperature_diff: Optional[Dict[str, float]] = None
    humidity_diff: Optional[Dict[str, float]] = None


class WeatherBriefingCreate(BaseModel):
    fleet_id: int
    briefing_date: Optional[date] = None


class WeatherBriefingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    fleet_id: int
    generated_at: datetime
    briefing_date: datetime
    summary: str
    details: Dict[str, Any]
    alerts_count: int


class WeatherAlertCheck(BaseModel):
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    triggered: bool
    alerts: List[AlertRecordBase]


class ProviderStatus(BaseModel):
    name: str
    available: bool
    last_check: Optional[datetime] = None
