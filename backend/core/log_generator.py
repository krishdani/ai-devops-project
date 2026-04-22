"""
Synthetic Log Generator
Simulates a realistic production application by continuously emitting
structured log events: routine traffic, warnings, errors, and security events
(brute-force attempts, SQL injection, port scans, etc.).
"""

import random
import time
import threading
from datetime import datetime, timezone

from utils.logger import get_application_logger, get_security_logger

# ── Scenario pools ────────────────────────────────────────────────────────────

INFO_MESSAGES = [
    "User {user} logged in successfully from IP {ip}",
    "GET /api/v1/dashboard completed in {ms}ms – 200 OK",
    "POST /api/v1/metrics ingested {count} data points",
    "Scheduled job 'cleanup_old_logs' completed successfully",
    "Database connection pool: {active}/{max} connections active",
    "Cache hit ratio: {ratio:.1f}% for key prefix 'metrics:'",
    "Health check passed – all services operational",
    "Config reloaded from environment variables",
    "Processed {count} events from SQS queue in {ms}ms",
    "S3 backup completed: {size}MB uploaded to s3://devops-backups/",
]

WARNING_MESSAGES = [
    "High memory usage detected: {pct}% – threshold is 80%",
    "Slow DB query on table 'audit_logs': {ms}ms (threshold 500ms)",
    "Rate limit approaching for IP {ip}: {count}/100 requests/min",
    "Disk usage on /var/log: {pct}% – consider log rotation",
    "API response time degraded: P99={ms}ms (normal <200ms)",
    "Retry {attempt}/3 for external service call to payment-gateway",
    "JWT token expiring soon for user {user} – refresh recommended",
    "Connection pool exhausted temporarily; request queued",
    "Certificate for api.devops-platform.io expires in {days} days",
    "Anomalous CPU spike: {pct}% on node {node}",
]

ERROR_MESSAGES = [
    "Unhandled exception in /api/v1/analyze: {error}",
    "Database connection failed: {error} – retrying in 5s",
    "Failed to publish SNS notification: {error}",
    "Redis cache unavailable – falling back to database",
    "Payment service timeout after {ms}ms – transaction rolled back",
    "File not found: /var/data/models/{model}.pkl",
    "Permission denied writing to /var/log/app/security.log",
    "ML model inference failed: input shape mismatch",
    "External API returned 503 after {attempt} retries",
    "Out-of-memory error in worker process PID {pid}",
]

SECURITY_EVENTS = [
    {
        "type": "FAILED_LOGIN",
        "message": "Failed login attempt for user '{user}' from IP {ip} – attempt {attempt}/5",
        "level": "WARNING",
    },
    {
        "type": "BRUTE_FORCE",
        "message": "BRUTE FORCE DETECTED: {count} failed logins for '{user}' from IP {ip} in 60s",
        "level": "CRITICAL",
    },
    {
        "type": "SQL_INJECTION",
        "message": "SQL injection attempt blocked on /api/v1/search from IP {ip}: payload='{payload}'",
        "level": "CRITICAL",
    },
    {
        "type": "XSS_ATTEMPT",
        "message": "XSS attempt detected on /api/v1/profile from IP {ip}: payload='{payload}'",
        "level": "ERROR",
    },
    {
        "type": "UNAUTHORIZED_ACCESS",
        "message": "Unauthorized access to /admin/users from IP {ip} – 403 returned",
        "level": "ERROR",
    },
    {
        "type": "PORT_SCAN",
        "message": "Potential port scan from IP {ip}: {ports} ports probed in {sec}s",
        "level": "CRITICAL",
    },
    {
        "type": "PRIVILEGE_ESCALATION",
        "message": "Privilege escalation attempt: user '{user}' tried to access admin endpoint",
        "level": "CRITICAL",
    },
    {
        "type": "SUSPICIOUS_USER_AGENT",
        "message": "Suspicious User-Agent from IP {ip}: '{ua}' – possible automated scanner",
        "level": "WARNING",
    },
]

# ── Helper data ────────────────────────────────────────────────────────────────

SAMPLE_IPS = [
    "192.168.1.{x}".format(x=i) for i in range(1, 20)
] + [
    "10.0.{a}.{b}".format(a=random.randint(0, 5), b=random.randint(1, 254))
    for _ in range(10)
] + ["45.33.32.156", "185.220.101.42", "178.62.55.120", "104.21.8.1"]

SAMPLE_USERS = ["alice", "bob", "carol", "dave", "eve", "mallory", "admin", "root", "deploy"]
SQL_PAYLOADS = ["' OR 1=1 --", "1; DROP TABLE users--", "' UNION SELECT * FROM credentials--"]
XSS_PAYLOADS = ["<script>alert('xss')</script>", "javascript:void(0)", "<img src=x onerror=alert(1)>"]
USER_AGENTS = ["sqlmap/1.6", "Nikto/2.1.6", "Masscan/1.0", "ZAP/2.11", "dirbuster"]


def _rand(lst):
    return random.choice(lst)


def _fmt(template: str) -> str:
    """Fill template placeholders with random realistic values."""
    return template.format(
        user=_rand(SAMPLE_USERS),
        ip=_rand(SAMPLE_IPS),
        ms=random.randint(10, 3000),
        count=random.randint(1, 500),
        size=round(random.uniform(0.1, 500), 1),
        max=20,
        active=random.randint(1, 20),
        ratio=random.uniform(60, 99),
        pct=random.randint(50, 99),
        attempt=random.randint(1, 3),
        days=random.randint(1, 30),
        node=f"node-{random.randint(1, 5)}",
        error=_rand(["ConnectionRefusedError", "TimeoutError", "IntegrityError", "MemoryError"]),
        model=_rand(["anomaly_v2", "classifier_v1", "nlp_v3"]),
        pid=random.randint(1000, 9999),
        payload=_rand(SQL_PAYLOADS + XSS_PAYLOADS),
        ports=random.randint(50, 500),
        sec=random.randint(5, 30),
        ua=_rand(USER_AGENTS),
    )


class LogGenerator:
    """
    Generates realistic mixed log traffic.

    Weights govern how often each severity is emitted:
      INFO 60% | WARNING 20% | ERROR 12% | SECURITY 8%
    """

    def __init__(self, interval: float = 5.0):
        self.interval = interval
        self.app_logger = get_application_logger()
        self.sec_logger = get_security_logger()
        self._stop_event = threading.Event()

    # ── Internal emitters ─────────────────────────────────────────────────────

    def _emit_info(self):
        self.app_logger.info(_fmt(_rand(INFO_MESSAGES)))

    def _emit_warning(self):
        self.app_logger.warning(_fmt(_rand(WARNING_MESSAGES)))

    def _emit_error(self):
        self.app_logger.error(_fmt(_rand(ERROR_MESSAGES)))

    def _emit_security(self):
        evt = _rand(SECURITY_EVENTS)
        msg = _fmt(evt["message"])
        level = evt["level"]
        entry = {
            "event_type": evt["type"],
            "message": msg,
            "severity": level,
        }

        if level == "CRITICAL":
            self.sec_logger.critical(msg, extra={"extra_event_type": evt["type"]})
        elif level == "ERROR":
            self.sec_logger.error(msg, extra={"extra_event_type": evt["type"]})
        else:
            self.sec_logger.warning(msg, extra={"extra_event_type": evt["type"]})

    # ── Public interface ──────────────────────────────────────────────────────

    def emit_one(self):
        """Emit a single log event based on weighted probability."""
        roll = random.random()
        if roll < 0.60:
            self._emit_info()
        elif roll < 0.80:
            self._emit_warning()
        elif roll < 0.92:
            self._emit_error()
        else:
            self._emit_security()

    def run(self):
        """Main loop – emit logs continuously until stopped."""
        self.app_logger.info("LogGenerator starting – interval=%.1fs", self.interval)
        while not self._stop_event.is_set():
            try:
                self.emit_one()
            except Exception as exc:  # noqa: BLE001
                self.app_logger.error("LogGenerator internal error: %s", exc)
            time.sleep(self.interval)

    def stop(self):
        """Signal the run loop to exit."""
        self._stop_event.set()
