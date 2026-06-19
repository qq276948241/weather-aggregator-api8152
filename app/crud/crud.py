from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from app import models, schemas


def get_city(db: Session, city_id: int) -> Optional[models.City]:
    return db.query(models.City).filter(models.City.id == city_id).first()


def get_city_by_name(db: Session, name: str) -> Optional[models.City]:
    return db.query(models.City).filter(models.City.name == name).first()


def get_cities(db: Session, skip: int = 0, limit: int = 100) -> List[models.City]:
    return db.query(models.City).offset(skip).limit(limit).all()


def create_city(db: Session, city: schemas.CityCreate) -> models.City:
    db_city = models.City(**city.model_dump())
    db.add(db_city)
    db.commit()
    db.refresh(db_city)
    return db_city


def get_route_segment(db: Session, route_id: int) -> Optional[models.RouteSegment]:
    return db.query(models.RouteSegment).filter(models.RouteSegment.id == route_id).first()


def get_route_segments(db: Session, skip: int = 0, limit: int = 100) -> List[models.RouteSegment]:
    return db.query(models.RouteSegment).offset(skip).limit(limit).all()


def create_route_segment(db: Session, route: schemas.RouteSegmentCreate) -> models.RouteSegment:
    db_route = models.RouteSegment(**route.model_dump())
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route


def get_fleet(db: Session, fleet_id: int) -> Optional[models.Fleet]:
    return db.query(models.Fleet).filter(models.Fleet.id == fleet_id).first()


def get_fleets(db: Session, skip: int = 0, limit: int = 100) -> List[models.Fleet]:
    return db.query(models.Fleet).offset(skip).limit(limit).all()


def create_fleet(db: Session, fleet: schemas.FleetCreate) -> models.Fleet:
    fleet_data = fleet.model_dump()
    route_ids = fleet_data.pop("route_ids", [])
    db_fleet = models.Fleet(**fleet_data)
    db.add(db_fleet)
    db.commit()
    db.refresh(db_fleet)
    for rid in route_ids:
        db_fr = models.FleetRoute(fleet_id=db_fleet.id, route_segment_id=rid)
        db.add(db_fr)
    db.commit()
    db.refresh(db_fleet)
    return db_fleet


def add_fleet_route(db: Session, fleet_id: int, route_segment_id: int) -> Optional[models.FleetRoute]:
    fleet = get_fleet(db, fleet_id)
    if not fleet:
        return None
    db_fr = models.FleetRoute(fleet_id=fleet_id, route_segment_id=route_segment_id)
    db.add(db_fr)
    db.commit()
    db.refresh(db_fr)
    return db_fr


def get_fleet_routes(db: Session, fleet_id: int) -> List[models.RouteSegment]:
    fleet = get_fleet(db, fleet_id)
    if not fleet:
        return []
    return [fr.route_segment for fr in fleet.routes]


def get_alert_rule(db: Session, rule_id: int) -> Optional[models.AlertRule]:
    return db.query(models.AlertRule).filter(models.AlertRule.id == rule_id).first()


def get_alert_rules(db: Session, skip: int = 0, limit: int = 100,
                    alert_type: Optional[str] = None,
                    enabled: Optional[bool] = None) -> List[models.AlertRule]:
    query = db.query(models.AlertRule)
    if alert_type:
        query = query.filter(models.AlertRule.alert_type == alert_type)
    if enabled is not None:
        query = query.filter(models.AlertRule.enabled == enabled)
    return query.offset(skip).limit(limit).all()


def create_alert_rule(db: Session, rule: schemas.AlertRuleCreate) -> models.AlertRule:
    db_rule = models.AlertRule(**rule.model_dump())
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


def update_alert_rule(db: Session, rule_id: int, rule_update: schemas.AlertRuleUpdate) -> Optional[models.AlertRule]:
    db_rule = get_alert_rule(db, rule_id)
    if not db_rule:
        return None
    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rule, key, value)
    db_rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_rule)
    return db_rule


def delete_alert_rule(db: Session, rule_id: int) -> bool:
    db_rule = get_alert_rule(db, rule_id)
    if not db_rule:
        return False
    db.delete(db_rule)
    db.commit()
    return True


def create_alert_record(db: Session, record: schemas.AlertRecordBase) -> models.AlertRecord:
    db_record = models.AlertRecord(**record.model_dump())
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_alert_records(db: Session, skip: int = 0, limit: int = 100,
                      alert_type: Optional[str] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None) -> List[models.AlertRecord]:
    query = db.query(models.AlertRecord)
    if alert_type:
        query = query.filter(models.AlertRecord.alert_type == alert_type)
    if start_time:
        query = query.filter(models.AlertRecord.created_at >= start_time)
    if end_time:
        query = query.filter(models.AlertRecord.created_at <= end_time)
    return query.order_by(models.AlertRecord.created_at.desc()).offset(skip).limit(limit).all()


def mark_alert_notified(db: Session, record_id: int) -> bool:
    record = db.query(models.AlertRecord).filter(models.AlertRecord.id == record_id).first()
    if not record:
        return False
    record.notified = True
    db.commit()
    return True


def get_subscription(db: Session, sub_id: int) -> Optional[models.WeatherSubscription]:
    return db.query(models.WeatherSubscription).filter(models.WeatherSubscription.id == sub_id).first()


def get_subscriptions(db: Session, skip: int = 0, limit: int = 100,
                      enabled: Optional[bool] = None,
                      subscriber_type: Optional[str] = None) -> List[models.WeatherSubscription]:
    query = db.query(models.WeatherSubscription)
    if enabled is not None:
        query = query.filter(models.WeatherSubscription.enabled == enabled)
    if subscriber_type:
        query = query.filter(models.WeatherSubscription.subscriber_type == subscriber_type)
    return query.offset(skip).limit(limit).all()


def create_subscription(db: Session, sub: schemas.WeatherSubscriptionCreate) -> models.WeatherSubscription:
    db_sub = models.WeatherSubscription(**sub.model_dump())
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub


def update_subscription(db: Session, sub_id: int, sub_update: schemas.WeatherSubscriptionUpdate) -> Optional[models.WeatherSubscription]:
    db_sub = get_subscription(db, sub_id)
    if not db_sub:
        return None
    update_data = sub_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_sub, key, value)
    db.commit()
    db.refresh(db_sub)
    return db_sub


def delete_subscription(db: Session, sub_id: int) -> bool:
    db_sub = get_subscription(db, sub_id)
    if not db_sub:
        return False
    db.delete(db_sub)
    db.commit()
    return True


def update_subscription_last_push(db: Session, sub_id: int) -> None:
    db_sub = get_subscription(db, sub_id)
    if db_sub:
        db_sub.last_push_at = datetime.utcnow()
        db.commit()


def save_weather_history(db: Session, record: schemas.WeatherHistoryRecord) -> models.WeatherHistory:
    db_record = models.WeatherHistory(**record.model_dump(exclude={"id"}))
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record


def get_weather_history(db: Session, location: Optional[str] = None,
                        latitude: Optional[float] = None,
                        longitude: Optional[float] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        data_source: Optional[str] = None,
                        skip: int = 0, limit: int = 500) -> List[models.WeatherHistory]:
    query = db.query(models.WeatherHistory)
    if location:
        query = query.filter(models.WeatherHistory.location == location)
    if latitude is not None and longitude is not None:
        query = query.filter(models.WeatherHistory.latitude == latitude,
                             models.WeatherHistory.longitude == longitude)
    if start_date:
        query = query.filter(models.WeatherHistory.record_date >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(models.WeatherHistory.record_date <= datetime.combine(end_date, datetime.max.time()))
    if data_source:
        query = query.filter(models.WeatherHistory.data_source == data_source)
    return query.order_by(models.WeatherHistory.record_date.desc()).offset(skip).limit(limit).all()


def create_weather_briefing(db: Session, fleet_id: int, briefing_date: datetime,
                            summary: str, details: Dict[str, Any],
                            alerts_count: int = 0) -> models.WeatherBriefing:
    db_briefing = models.WeatherBriefing(
        fleet_id=fleet_id,
        briefing_date=briefing_date,
        summary=summary,
        details=details,
        alerts_count=alerts_count
    )
    db.add(db_briefing)
    db.commit()
    db.refresh(db_briefing)
    return db_briefing


def get_weather_briefings(db: Session, fleet_id: int,
                          skip: int = 0, limit: int = 30) -> List[models.WeatherBriefing]:
    return (db.query(models.WeatherBriefing)
            .filter(models.WeatherBriefing.fleet_id == fleet_id)
            .order_by(models.WeatherBriefing.generated_at.desc())
            .offset(skip).limit(limit).all())


def get_latest_briefing(db: Session, fleet_id: int) -> Optional[models.WeatherBriefing]:
    return (db.query(models.WeatherBriefing)
            .filter(models.WeatherBriefing.fleet_id == fleet_id)
            .order_by(models.WeatherBriefing.generated_at.desc())
            .first())
