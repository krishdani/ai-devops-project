"""
Alert Manager
Handles alert lifecycle: creation, storage, deduplication, and delivery
via AWS SNS.  Operates independently of the AI layer so alerts fire even
when AI analysis is disabled.
"""

import json
import os
import threading
import time
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import Config
from utils.logger import setup_logger

logger = setup_logger("alert_manager", "logs/alert_manager.log")


# ── Severity levels (ordered) ────────────────────────────────────────────────

class Severity:
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    _ORDER = {"INFO": 0, "WARNING": 1, "ERROR": 2, "CRITICAL": 3}

    @classmethod
    def gte(cls, level: str, threshold: str) -> bool:
        """Return True if *level* is >= *threshold*."""
        return cls._ORDER.get(level, 0) >= cls._ORDER.get(threshold, 0)


# ── Alert data class ─────────────────────────────────────────────────────────

class Alert:
    """Represents a single alert event."""

    def __init__(
        self,
        alert_type: str,
        message: str,
        severity: str = Severity.WARNING,
        source: str = "system",
        metadata: Optional[dict] = None,
    ):
        self.id = self._generate_id(alert_type, message)
        self.alert_type = alert_type
        self.message = message
        self.severity = severity
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.acknowledged = False

    @staticmethod
    def _generate_id(alert_type: str, message: str) -> str:
        """Deterministic short ID for deduplication within a time window."""
        raw = f"{alert_type}:{message}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alert_type": self.alert_type,
            "message": self.message,
            "severity": self.severity,
            "source": self.source,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "acknowledged": self.acknowledged,
        }


# ── SNS Client wrapper ───────────────────────────────────────────────────────

class SNSNotifier:
    """Thin wrapper around boto3 SNS publish.  No-ops gracefully when AWS
    is disabled or credentials are missing."""

    def __init__(self):
        self._client = None
        if Config.ENABLE_SNS_ALERTS and Config.SNS_TOPIC_ARN:
            try:
                import boto3
                self._client = boto3.client(
                    "sns",
                    region_name=Config.AWS_REGION,
                    aws_access_key_id=Config.AWS_ACCESS_KEY_ID or None,
                    aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY or None,
                )
                logger.info("SNS notifier initialized — topic: %s", Config.SNS_TOPIC_ARN)
            except Exception as exc:
                logger.warning("SNS client init failed: %s — alerts will be local-only", exc)

    def send(self, alert: Alert) -> bool:
        """Publish an alert to the configured SNS topic.  Returns True on
        success, False otherwise."""
        if self._client is None:
            return False

        subject = f"[{alert.severity}] {alert.alert_type}"
        body = (
            f"AI DevOps Platform Alert\n"
            f"{'=' * 40}\n"
            f"Type:      {alert.alert_type}\n"
            f"Severity:  {alert.severity}\n"
            f"Source:    {alert.source}\n"
            f"Time:      {alert.timestamp}\n"
            f"{'=' * 40}\n\n"
            f"{alert.message}\n\n"
            f"Metadata: {json.dumps(alert.metadata, indent=2)}"
        )

        try:
            self._client.publish(
                TopicArn=Config.SNS_TOPIC_ARN,
                Subject=subject[:100],  # SNS subject limit
                Message=body,
            )
            logger.info("SNS notification sent for alert %s", alert.id)
            return True
        except Exception as exc:
            logger.error("SNS publish failed for alert %s: %s", alert.id, exc)
            return False


# ── Alert Manager (singleton-friendly) ────────────────────────────────────────

class AlertManager:
    """
    Central alert management service.

    Responsibilities:
      • Create and store alerts (thread-safe)
      • Deduplicate alerts within a configurable cooldown window
      • Persist alerts to a JSON file for dashboard retrieval
      • Deliver high-severity alerts via AWS SNS
    """

    _DEDUP_WINDOW = timedelta(minutes=5)  # ignore duplicate alert IDs within 5 min
    _MAX_STORED = 500  # keep most recent N alerts in memory

    def __init__(self):
        self._lock = threading.Lock()
        self._alerts: list[dict] = []
        self._recent_ids: dict[str, datetime] = {}  # id -> last fired time
        self._sns = SNSNotifier()
        self._load_from_disk()

    # ── Persistence ──────────────────────────────────────────────────────────

    def _disk_path(self) -> str:
        return Config.ALERTS_DB_FILE

    def _load_from_disk(self):
        """Load previously persisted alerts from JSON file."""
        path = self._disk_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    self._alerts = json.load(fh)
                logger.info("Loaded %d historical alerts from %s", len(self._alerts), path)
            except Exception as exc:
                logger.warning("Failed to load alerts DB: %s — starting fresh", exc)
                self._alerts = []

    def _persist(self):
        """Write current alerts list to disk (call while holding _lock)."""
        path = self._disk_path()
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(self._alerts, fh, indent=2)
        except Exception as exc:
            logger.error("Failed to persist alerts: %s", exc)

    # ── Core API ─────────────────────────────────────────────────────────────

    def fire(self, alert: Alert) -> bool:
        """
        Process a new alert: deduplicate → store → notify.

        Returns True if the alert was accepted (not a duplicate).
        """
        now = datetime.now(timezone.utc)

        with self._lock:
            # Deduplication check
            last_fired = self._recent_ids.get(alert.id)
            if last_fired and (now - last_fired) < self._DEDUP_WINDOW:
                logger.debug("Alert %s suppressed (dedup window)", alert.id)
                return False

            # Store
            self._recent_ids[alert.id] = now
            self._alerts.append(alert.to_dict())

            # Trim to max
            if len(self._alerts) > self._MAX_STORED:
                self._alerts = self._alerts[-self._MAX_STORED:]

            self._persist()

        logger.info(
            "Alert fired: [%s] %s — %s",
            alert.severity, alert.alert_type, alert.message[:80],
        )

        # Send SNS for ERROR and CRITICAL alerts
        if Severity.gte(alert.severity, Severity.ERROR):
            self._sns.send(alert)

        return True

    def get_alerts(
        self,
        limit: int = 50,
        severity: Optional[str] = None,
        acknowledged: Optional[bool] = None,
    ) -> list[dict]:
        """Return stored alerts, most recent first, with optional filters."""
        with self._lock:
            result = list(reversed(self._alerts))

        if severity:
            result = [a for a in result if a["severity"] == severity.upper()]
        if acknowledged is not None:
            result = [a for a in result if a["acknowledged"] == acknowledged]

        return result[:limit]

    def acknowledge(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged.  Returns True if found."""
        with self._lock:
            for alert in self._alerts:
                if alert["id"] == alert_id:
                    alert["acknowledged"] = True
                    self._persist()
                    logger.info("Alert %s acknowledged", alert_id)
                    return True
        return False

    def get_stats(self) -> dict:
        """Return summary statistics for the dashboard."""
        with self._lock:
            total = len(self._alerts)
            by_severity = {}
            unacknowledged = 0
            for a in self._alerts:
                sev = a["severity"]
                by_severity[sev] = by_severity.get(sev, 0) + 1
                if not a["acknowledged"]:
                    unacknowledged += 1

        return {
            "total_alerts": total,
            "unacknowledged": unacknowledged,
            "by_severity": by_severity,
        }

    def clear(self):
        """Purge all alerts (useful for testing)."""
        with self._lock:
            self._alerts.clear()
            self._recent_ids.clear()
            self._persist()
        logger.info("All alerts cleared")
