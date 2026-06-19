import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models import models
from app.api.weather import router as weather_router
from app.api.resources import router as cities_router, router_routes, router_fleets
from app.api.alerts import router as alerts_router, router_subs
from app.api.operations import router as operations_router
from app.services.alert_service import AlertService
from app import crud
from app.schemas.schemas import CityCreate

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    db = SessionLocal()
    try:
        AlertService(db).ensure_default_rules()
        _seed_cities(db)
    except Exception as e:
        logger.error(f"DB initialization error: {e}")
    finally:
        db.close()


def _seed_cities(db):
    default_cities = [
        ("北京", "北京市", 39.9042, 116.4074),
        ("上海", "上海市", 31.2304, 121.4737),
        ("广州", "广东省", 23.1291, 113.2644),
        ("深圳", "广东省", 22.5431, 114.0579),
        ("成都", "四川省", 30.5728, 104.0668),
        ("杭州", "浙江省", 30.2741, 120.1551),
        ("武汉", "湖北省", 30.5928, 114.3055),
        ("西安", "陕西省", 34.3416, 108.9398),
        ("南京", "江苏省", 32.0603, 118.7969),
        ("重庆", "重庆市", 29.4316, 106.9123),
        ("天津", "天津市", 39.3434, 117.3616),
        ("苏州", "江苏省", 31.2990, 120.5853),
        ("郑州", "河南省", 34.7466, 113.6254),
        ("长沙", "湖南省", 28.2282, 112.9388),
        ("青岛", "山东省", 36.0671, 120.3826),
    ]
    count = 0
    for name, prov, lat, lon in default_cities:
        existing = crud.get_city_by_name(db, name)
        if not existing:
            crud.create_city(db, CityCreate(name=name, province=prov, latitude=lat, longitude=lon))
            count += 1
    if count > 0:
        logger.info(f"Seeded {count} default cities")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    init_db()
    try:
        from app.scheduler import start_scheduler, stop_scheduler
        start_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    yield
    try:
        from app.scheduler import stop_scheduler
        stop_scheduler()
    except Exception:
        pass
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description="冷链物流天气数据聚合服务 - 支持多天气源聚合、预警阈值检测、车队简报、定时推送",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", tags=["system"])
    async def root():
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "providers": settings.provider_list,
            "docs": "/docs",
        }

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "healthy"}

    app.include_router(weather_router, prefix="/api/v1")
    app.include_router(cities_router, prefix="/api/v1")
    app.include_router(router_routes, prefix="/api/v1")
    app.include_router(router_fleets, prefix="/api/v1")
    app.include_router(alerts_router, prefix="/api/v1")
    app.include_router(router_subs, prefix="/api/v1")
    app.include_router(operations_router, prefix="/api/v1")

    return app


app = create_app()
