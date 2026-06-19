from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/cities", tags=["cities"])


@router.get("", response_model=List[schemas.City])
def list_cities(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_cities(db, skip=skip, limit=limit)


@router.post("", response_model=schemas.City, status_code=201)
def create_city(city: schemas.CityCreate, db: Session = Depends(get_db)):
    existing = crud.get_city_by_name(db, city.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"城市 {city.name} 已存在")
    return crud.create_city(db, city)


@router.get("/{city_id}", response_model=schemas.City)
def get_city(city_id: int, db: Session = Depends(get_db)):
    city = crud.get_city(db, city_id)
    if not city:
        raise HTTPException(status_code=404, detail="城市不存在")
    return city


@router.get("/name/{city_name}", response_model=schemas.City)
def get_city_by_name(city_name: str, db: Session = Depends(get_db)):
    city = crud.get_city_by_name(db, city_name)
    if not city:
        raise HTTPException(status_code=404, detail="城市不存在")
    return city


router_routes = APIRouter(prefix="/routes", tags=["routes"])


@router_routes.get("", response_model=List[schemas.RouteSegment])
def list_routes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_route_segments(db, skip=skip, limit=limit)


@router_routes.post("", response_model=schemas.RouteSegment, status_code=201)
def create_route(route: schemas.RouteSegmentCreate, db: Session = Depends(get_db)):
    return crud.create_route_segment(db, route)


@router_routes.get("/{route_id}", response_model=schemas.RouteSegment)
def get_route(route_id: int, db: Session = Depends(get_db)):
    route = crud.get_route_segment(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="路线不存在")
    return route


router_fleets = APIRouter(prefix="/fleets", tags=["fleets"])


@router_fleets.get("", response_model=List[schemas.Fleet])
def list_fleets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return crud.get_fleets(db, skip=skip, limit=limit)


@router_fleets.post("", response_model=schemas.Fleet, status_code=201)
def create_fleet(fleet: schemas.FleetCreate, db: Session = Depends(get_db)):
    return crud.create_fleet(db, fleet)


@router_fleets.get("/{fleet_id}", response_model=schemas.Fleet)
def get_fleet(fleet_id: int, db: Session = Depends(get_db)):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    return fleet


@router_fleets.post("/{fleet_id}/routes/{route_id}")
def add_route_to_fleet(fleet_id: int, route_id: int, db: Session = Depends(get_db)):
    result = crud.add_fleet_route(db, fleet_id, route_id)
    if not result:
        raise HTTPException(status_code=404, detail="车队或路线不存在")
    return {"status": "ok", "fleet_route_id": result.id}


@router_fleets.get("/{fleet_id}/routes", response_model=List[schemas.RouteSegment])
def get_fleet_routes(fleet_id: int, db: Session = Depends(get_db)):
    fleet = crud.get_fleet(db, fleet_id)
    if not fleet:
        raise HTTPException(status_code=404, detail="车队不存在")
    return crud.get_fleet_routes(db, fleet_id)
