import logging
import json
from typing import List, Optional
from sqlalchemy.orm import Session
from app import models

logger = logging.getLogger(__name__)


class NotificationService:
    @staticmethod
    def send_alert(db: Session, alert_record: models.AlertRecord, channels: List[str]) -> bool:
        success = False
        for channel in channels:
            try:
                if NotificationService._send_by_channel(channel, alert_record):
                    success = True
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")
        if success:
            from app import crud
            crud.mark_alert_notified(db, alert_record.id)
        return success

    @staticmethod
    def _send_by_channel(channel: str, alert_record: models.AlertRecord) -> bool:
        if channel == "log":
            logger.warning(f"[ALERT-{alert_record.alert_type}] {alert_record.message} "
                           f"location={alert_record.location} value={alert_record.trigger_value} "
                           f"threshold={alert_record.threshold_value}")
            return True
        if channel == "console":
            print(f"[ALERT] {alert_record.message}")
            return True
        if channel == "webhook":
            NotificationService._send_webhook(alert_record)
            return True
        if channel == "email":
            logger.info(f"Would send email alert: {alert_record.message}")
            return True
        if channel == "sms":
            logger.info(f"Would send SMS alert: {alert_record.message}")
            return True
        logger.warning(f"Unknown notification channel: {channel}")
        return False

    @staticmethod
    def _send_webhook(alert_record: models.AlertRecord) -> None:
        import httpx
        payload = {
            "id": alert_record.id,
            "alert_type": alert_record.alert_type,
            "location": alert_record.location,
            "latitude": alert_record.latitude,
            "longitude": alert_record.longitude,
            "trigger_value": alert_record.trigger_value,
            "threshold_value": alert_record.threshold_value,
            "message": alert_record.message,
            "data_source": alert_record.data_source,
            "created_at": alert_record.created_at.isoformat() if alert_record.created_at else None,
        }
        logger.info(f"Webhook payload (not sent, no webhook URL configured): {json.dumps(payload, ensure_ascii=False)}")

    @staticmethod
    def send_subscription_push(db: Session, subscription: models.WeatherSubscription,
                                content: dict) -> bool:
        success = False
        for channel in subscription.push_channels:
            try:
                if NotificationService._send_push_by_channel(channel, subscription, content):
                    success = True
            except Exception as e:
                logger.error(f"Failed to push via {channel}: {e}")
        if success:
            from app import crud
            crud.update_subscription_last_push(db, subscription.id)
        return success

    @staticmethod
    def _send_push_by_channel(channel: str, subscription: models.WeatherSubscription,
                              content: dict) -> bool:
        if channel == "log":
            logger.info(f"[PUSH-{subscription.name}] {json.dumps(content, ensure_ascii=False, default=str)}")
            return True
        if channel == "console":
            print(f"[PUSH {subscription.name}] {json.dumps(content, ensure_ascii=False, default=str)}")
            return True
        if channel == "webhook":
            logger.info(f"Subscription push webhook (no URL configured): {subscription.name}")
            return True
        if channel == "email":
            logger.info(f"Would send email push to subscription {subscription.name}")
            return True
        return False
