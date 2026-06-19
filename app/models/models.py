from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class City(Base):
    __tablename__ = "cities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    province = Column(String(100))
    country = Column(String(100), default="中国")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class RouteSegment(Base):
    __tablename__ = "route_segments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    start_city = Column(String(100), nullable=False)
    end_city = Column(String(100), nullable=False)
    start_latitude = Column(Float, nullable=False)
    start_longitude = Column(Float, nullable=False)
    end_latitude = Column(Float, nullable=False)
    end_longitude = Column(Float, nullable=False)
    waypoints = Column(JSON)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Fleet(Base):
    __tablename__ = "fleets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    contact_name = Column(String(100))
    contact_phone = Column(String(50))
    contact_email = Column(String(200))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    routes = relationship("FleetRoute", back_populates="fleet", cascade="all, delete-orphan")


class FleetRoute(Base):
    __tablename__ = "fleet_routes"
    id = Column(Integer, primary_key=True, index=True)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False)
    route_segment_id = Column(Integer, ForeignKey("route_segments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    fleet = relationship("Fleet", back_populates="routes")
    route_segment = relationship("RouteSegment")


class AlertRule(Base):
    __tablename__ = "alert_rules"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=False)
    comparison = Column(String(20), default="gt")
    enabled = Column(Boolean, default=True)
    scope_type = Column(String(50), default="global")
    scope_id = Column(Integer)
    notify_channels = Column(JSON, default=["log"])
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlertRecord(Base):
    __tablename__ = "alert_records"
    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("alert_rules.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    location = Column(String(200), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    trigger_value = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    message = Column(Text, nullable=False)
    data_source = Column(String(100))
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class WeatherSubscription(Base):
    __tablename__ = "weather_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    subscriber_type = Column(String(50), nullable=False)
    subscriber_id = Column(Integer)
    scope_type = Column(String(50), nullable=False)
    scope_id = Column(Integer)
    push_interval_minutes = Column(Integer, default=30)
    enabled = Column(Boolean, default=True)
    last_push_at = Column(DateTime)
    push_channels = Column(JSON, default=["log"])
    created_at = Column(DateTime, default=datetime.utcnow)


class WeatherHistory(Base):
    __tablename__ = "weather_history"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String(200), index=True, nullable=False)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    record_date = Column(DateTime, index=True, nullable=False)
    temperature = Column(Float)
    humidity = Column(Float)
    wind_speed = Column(Float)
    wind_direction = Column(String(50))
    precipitation = Column(Float)
    pressure = Column(Float)
    weather_condition = Column(String(100))
    data_source = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


class WeatherBriefing(Base):
    __tablename__ = "weather_briefings"
    id = Column(Integer, primary_key=True, index=True)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow, index=True)
    briefing_date = Column(DateTime, nullable=False)
    summary = Column(Text, nullable=False)
    details = Column(JSON, nullable=False)
    alerts_count = Column(Integer, default=0)
