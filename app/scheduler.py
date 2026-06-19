import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from app.database import SessionLocal
from app.services.alert_service import AlertService
from app.services.briefing import BriefingService, SubscriptionService
from app.config import settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")
    return _scheduler


async def _run_alert_check():
    db = SessionLocal()
    try:
        svc = AlertService(db)
        results = await svc.run_global_alert_check()
        if results:
            logger.info(f"Scheduled alert check: triggered {len(results)} alerts")
        else:
            logger.info("Scheduled alert check: no alerts triggered")
    except Exception as e:
        logger.error(f"Scheduled alert check failed: {e}")
    finally:
        db.close()


async def _run_briefing_generation():
    db = SessionLocal()
    try:
        svc = BriefingService(db)
        results = await svc.generate_all_fleet_briefings()
        logger.info(f"Scheduled briefing generation: generated {len(results)} briefings")
    except Exception as e:
        logger.error(f"Scheduled briefing generation failed: {e}")
    finally:
        db.close()


async def _run_subscription_push():
    db = SessionLocal()
    try:
        svc = SubscriptionService(db)
        count = await svc.process_due_subscriptions()
        if count > 0:
            logger.info(f"Scheduled subscription push: pushed {count} subscriptions")
    except Exception as e:
        logger.error(f"Scheduled subscription push failed: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = get_scheduler()

    scheduler.add_job(
        _run_alert_check,
        trigger=IntervalTrigger(minutes=settings.ALERT_CHECK_INTERVAL_MINUTES),
        id="alert_check",
        name="全局预警检查",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_briefing_generation,
        trigger=CronTrigger(hour=settings.BRIEFING_GENERATION_HOUR, minute=0),
        id="briefing_generation",
        name="每日车队简报生成",
        replace_existing=True,
    )

    scheduler.add_job(
        _run_subscription_push,
        trigger=IntervalTrigger(minutes=max(settings.SUBSCRIPTION_PUSH_INTERVAL_MINUTES, 5)),
        id="subscription_push",
        name="订阅推送",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Scheduler started with jobs: alert_check, briefing_generation, subscription_push")


def stop_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown()
        logger.info("Scheduler stopped")
