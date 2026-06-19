from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/rules", response_model=List[schemas.AlertRule])
def list_alert_rules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    alert_type: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.get_alert_rules(db, skip=skip, limit=limit, alert_type=alert_type, enabled=enabled)


@router.post("/rules", response_model=schemas.AlertRule, status_code=201)
def create_alert_rule(rule: schemas.AlertRuleCreate, db: Session = Depends(get_db)):
    return crud.create_alert_rule(db, rule)


@router.get("/rules/{rule_id}", response_model=schemas.AlertRule)
def get_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = crud.get_alert_rule(db, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="预警规则不存在")
    return rule


@router.put("/rules/{rule_id}", response_model=schemas.AlertRule)
def update_alert_rule(rule_id: int, update: schemas.AlertRuleUpdate, db: Session = Depends(get_db)):
    rule = crud.update_alert_rule(db, rule_id, update)
    if not rule:
        raise HTTPException(status_code=404, detail="预警规则不存在")
    return rule


@router.delete("/rules/{rule_id}")
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    if not crud.delete_alert_rule(db, rule_id):
        raise HTTPException(status_code=404, detail="预警规则不存在")
    return {"status": "ok"}


@router.get("/records", response_model=List[schemas.AlertRecord])
def list_alert_records(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    alert_type: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.get_alert_records(
        db, skip=skip, limit=limit, alert_type=alert_type,
        start_time=start_time, end_time=end_time,
    )


@router.post("/records/{record_id}/notify")
def mark_alert_notified(record_id: int, db: Session = Depends(get_db)):
    if not crud.mark_alert_notified(db, record_id):
        raise HTTPException(status_code=404, detail="预警记录不存在")
    return {"status": "ok"}


router_subs = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router_subs.get("", response_model=List[schemas.WeatherSubscription])
def list_subscriptions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    enabled: Optional[bool] = Query(None),
    subscriber_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return crud.get_subscriptions(db, skip=skip, limit=limit, enabled=enabled, subscriber_type=subscriber_type)


@router_subs.post("", response_model=schemas.WeatherSubscription, status_code=201)
def create_subscription(sub: schemas.WeatherSubscriptionCreate, db: Session = Depends(get_db)):
    return crud.create_subscription(db, sub)


@router_subs.get("/{sub_id}", response_model=schemas.WeatherSubscription)
def get_subscription(sub_id: int, db: Session = Depends(get_db)):
    sub = crud.get_subscription(db, sub_id)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@router_subs.put("/{sub_id}", response_model=schemas.WeatherSubscription)
def update_subscription(sub_id: int, update: schemas.WeatherSubscriptionUpdate, db: Session = Depends(get_db)):
    sub = crud.update_subscription(db, sub_id, update)
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    return sub


@router_subs.delete("/{sub_id}")
def delete_subscription(sub_id: int, db: Session = Depends(get_db)):
    if not crud.delete_subscription(db, sub_id):
        raise HTTPException(status_code=404, detail="订阅不存在")
    return {"status": "ok"}
