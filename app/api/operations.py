from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.database import get_db
from app import crud, schemas
from app.services.briefing import BriefingService, SubscriptionService
from app.services.alert_service import AlertService

router = APIRouter(tags=["operations"])


@router.post("/briefings/fleet/{fleet_id}", response_model=schemas.WeatherBriefingOut)
async def generate_fleet_briefing(
    fleet_id: int,
    briefing_date: Optional[date] = Query(None, description="简报日期，默认今天"),
    db: Session = Depends(get_db),
):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    svc = BriefingService(db)
    briefing = await svc.generate_fleet_briefing(fleet_id, briefing_date)
    if not briefing:
        raise HTTPException(status_code=500, detail="生成简报失败")
    return briefing


@router.get("/briefings/fleet/{fleet_id}", response_model=List[schemas.WeatherBriefingOut])
def list_fleet_briefings(
    fleet_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    return crud.get_weather_briefings(db, fleet_id, skip=skip, limit=limit)


@router.get("/briefings/fleet/{fleet_id}/latest", response_model=schemas.WeatherBriefingOut)
def get_latest_briefing(fleet_id: int, db: Session = Depends(get_db)):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    briefing = crud.get_latest_briefing(db, fleet_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="尚未生成任何简报")
    return briefing


@router.post("/briefings/_generate_all")
async def generate_all_briefings(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    svc = BriefingService(db)
    background_tasks.add_task(svc.generate_all_fleet_briefings)
    return {"status": "started", "message": "已触发所有车队简报生成任务"}


@router.post("/alerts/_check_all")
async def run_global_alert_check(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    svc = AlertService(db)
    background_tasks.add_task(svc.run_global_alert_check)
    return {"status": "started", "message": "已触发全局预警检查"}


@router.get("/alerts/route/{route_id}")
async def check_route_alerts(route_id: int, db: Session = Depends(get_db)):
    route = crud.get_route_segment(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")
    svc = AlertService(db)
    return await svc.check_route_alerts(route_id)


@router.get("/alerts/fleet/{fleet_id}")
async def check_fleet_alerts(fleet_id: int, db: Session = Depends(get_db)):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    svc = AlertService(db)
    return await svc.check_fleet_alerts(fleet_id)


@router.post("/subscriptions/_push")
async def trigger_subscription_push(background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    svc = SubscriptionService(db)
    count = await svc.process_due_subscriptions()
    return {"status": "ok", "pushed_count": count}
