"""
Log Watcher
Continuously monitors log files for anomalies and security threats.
Orchestrates AI analysis and alert firing based on configurable thresholds.

Architecture:
  • Tail-reads the application and security log files
  • Buffers lines and triggers AI analysis when batch size is reached
  • Runs pattern-matching detectors in parallel for instant threat response
  • Delegates alert creation to AlertManager
"""

import json
import os
import re
import threading
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import Config
from core.ai_analyzer import AIAnalyzer
from core.alert_manager import AlertManager, Alert, Severity
from utils.logger import setup_logger

logger = setup_logger("log_watcher", "logs/log_watcher.log")


# ── Log-line parser ───────────────────────────────────────────────────────────

def _parse_json_line(line: str) -> Optional[dict]:
    """Attempt to parse a JSON log line; return None on failure."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except (json.JSONDecodeError, ValueError):
        return None


# ── Threat Detector (real-time pattern matching) ──────────────────────────────

class ThreatDetector:
    """
    Stateful detector that identifies security threats in real time
    using sliding-window counters and pattern matching.
    """

    def __init__(self, alert_manager: AlertManager):
        self._alert_mgr = alert_manager
        self._lock = threading.Lock()

        # Sliding-window counters  ──  key: IP or user → list of timestamps
        self._failed_logins: dict[str, list[datetime]] = defaultdict(list)
        self._error_timestamps: list[datetime] = []

    # ── Brute-force detection ────────────────────────────────────────────────

    def check_brute_force(self, entry: dict):
        """Track failed logins per IP and fire alert when threshold is hit."""
        msg = entry.get("message", "")
        if "Failed login" not in msg and "FAILED_LOGIN" not in msg:
            return

        # Extract IP from message
        ip_match = re.search(r"IP\s+([\d.]+)", msg)
        ip = ip_match.group(1) if ip_match else "unknown"

        now = datetime.now(timezone.utc)
        window = timedelta(seconds=Config.BRUTE_FORCE_WINDOW_SECONDS)

        with self._lock:
            self._failed_logins[ip].append(now)
            # Prune old entries
            self._failed_logins[ip] = [
                t for t in self._failed_logins[ip] if (now - t) <= window
            ]
            count = len(self._failed_logins[ip])

        if count >= Config.BRUTE_FORCE_THRESHOLD:
            self._alert_mgr.fire(Alert(
                alert_type="BRUTE_FORCE_DETECTED",
                message=f"Brute force attack: {count} failed logins from IP {ip} in {Config.BRUTE_FORCE_WINDOW_SECONDS}s",
                severity=Severity.CRITICAL,
                source="threat_detector",
                metadata={"ip": ip, "failed_attempts": count},
            ))

    # ── Injection / XSS detection ────────────────────────────────────────────

    def check_injection(self, entry: dict):
        """Detect SQL injection and XSS attempts from log content."""
        msg = entry.get("message", "")

        if any(kw in msg for kw in ["SQL injection", "sql injection", "OR 1=1", "DROP TABLE", "UNION SELECT"]):
            self._alert_mgr.fire(Alert(
                alert_type="SQL_INJECTION",
                message=f"SQL injection attempt detected: {msg[:200]}",
                severity=Severity.CRITICAL,
                source="threat_detector",
                metadata={"raw_message": msg[:500]},
            ))

        if any(kw in msg for kw in ["XSS", "xss", "<script>", "onerror="]):
            self._alert_mgr.fire(Alert(
                alert_type="XSS_ATTEMPT",
                message=f"XSS attempt detected: {msg[:200]}",
                severity=Severity.ERROR,
                source="threat_detector",
                metadata={"raw_message": msg[:500]},
            ))

    # ── Port scan detection ──────────────────────────────────────────────────

    def check_port_scan(self, entry: dict):
        """Detect port scan events."""
        msg = entry.get("message", "")
        if "port scan" in msg.lower() or "PORT_SCAN" in msg:
            self._alert_mgr.fire(Alert(
                alert_type="PORT_SCAN",
                message=f"Port scan detected: {msg[:200]}",
                severity=Severity.CRITICAL,
                source="threat_detector",
                metadata={"raw_message": msg[:500]},
            ))

    # ── Privilege escalation detection ───────────────────────────────────────

    def check_privilege_escalation(self, entry: dict):
        """Detect privilege escalation attempts."""
        msg = entry.get("message", "")
        if "privilege escalation" in msg.lower() or "PRIVILEGE_ESCALATION" in msg:
            self._alert_mgr.fire(Alert(
                alert_type="PRIVILEGE_ESCALATION",
                message=f"Privilege escalation attempt: {msg[:200]}",
                severity=Severity.CRITICAL,
                source="threat_detector",
                metadata={"raw_message": msg[:500]},
            ))

    # ── Error-rate spike detection ───────────────────────────────────────────

    def check_error_spike(self, entry: dict):
        """Fire alert when error count exceeds threshold within the window."""
        level = entry.get("level", "")
        if level not in ("ERROR", "CRITICAL"):
            return

        now = datetime.now(timezone.utc)
        window = timedelta(minutes=Config.ERROR_ALERT_WINDOW_MINUTES)

        with self._lock:
            self._error_timestamps.append(now)
            self._error_timestamps = [
                t for t in self._error_timestamps if (now - t) <= window
            ]
            count = len(self._error_timestamps)

        if count >= Config.ERROR_ALERT_THRESHOLD:
            self._alert_mgr.fire(Alert(
                alert_type="ERROR_RATE_SPIKE",
                message=f"Error rate spike: {count} errors in the last {Config.ERROR_ALERT_WINDOW_MINUTES} minutes",
                severity=Severity.ERROR,
                source="threat_detector",
                metadata={"error_count": count, "window_minutes": Config.ERROR_ALERT_WINDOW_MINUTES},
            ))

    # ── Unified entry point ──────────────────────────────────────────────────

    def inspect(self, entry: dict):
        """Run all detectors against a parsed log entry."""
        self.check_brute_force(entry)
        self.check_injection(entry)
        self.check_port_scan(entry)
        self.check_privilege_escalation(entry)
        self.check_error_spike(entry)


# ── File Tailer ───────────────────────────────────────────────────────────────

class _FileTailer:
    """Reads new lines appended to a file since the last read."""

    def __init__(self, path: str):
        self.path = path
        self._offset = 0
        # Start at end of file if it already exists
        if os.path.exists(path):
            self._offset = os.path.getsize(path)

    def read_new_lines(self) -> list[str]:
        """Return list of new lines since last read."""
        if not os.path.exists(self.path):
            return []
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(self._offset)
                data = fh.read()
                self._offset = fh.tell()
            if not data:
                return []
            return data.strip().splitlines()
        except Exception as exc:
            logger.error("Failed to tail %s: %s", self.path, exc)
            return []


# ── Log Watcher (main service) ────────────────────────────────────────────────

class LogWatcher:
    """
    Background service that:
      1. Tails application.log and security.log
      2. Runs real-time threat detection on every line
      3. Buffers lines for batch AI analysis
      4. Fires alerts through AlertManager
    """

    def __init__(self, poll_interval: float = 3.0):
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()

        # Shared services
        self.alert_manager = AlertManager()
        self.ai_analyzer = AIAnalyzer()
        self.threat_detector = ThreatDetector(self.alert_manager)

        # File tailers
        self._app_tailer = _FileTailer(Config.APP_LOG_FILE)
        self._sec_tailer = _FileTailer(Config.SECURITY_LOG_FILE)

        # AI batch buffer
        self._buffer: list[str] = []
        self._buffer_lock = threading.Lock()

        # Stats
        self._lines_processed = 0
        self._analyses_run = 0

    # ── Processing pipeline ──────────────────────────────────────────────────

    def _process_lines(self, lines: list[str]):
        """Parse, detect threats, and buffer for AI analysis."""
        for line in lines:
            entry = _parse_json_line(line)
            if entry is None:
                continue

            self._lines_processed += 1

            # Real-time threat detection (fast, pattern-based)
            try:
                self.threat_detector.inspect(entry)
            except Exception as exc:
                logger.error("Threat detector error: %s", exc)

            # Buffer for batch AI analysis
            with self._buffer_lock:
                self._buffer.append(line)

    def _maybe_run_ai_analysis(self):
        """Trigger AI analysis when the buffer reaches batch size."""
        with self._buffer_lock:
            if len(self._buffer) < Config.AI_LOG_BATCH_SIZE:
                return
            batch = self._buffer[:Config.AI_LOG_BATCH_SIZE]
            self._buffer = self._buffer[Config.AI_LOG_BATCH_SIZE:]

        logger.info("Running AI analysis on batch of %d lines", len(batch))
        try:
            result = self.ai_analyzer.analyze(batch)
            self._analyses_run += 1

            # Fire alerts for AI-detected threats
            self._process_ai_result(result)
        except Exception as exc:
            logger.error("AI analysis failed: %s", exc)

    def _process_ai_result(self, result: dict):
        """Convert AI analysis findings into alerts."""
        risk = result.get("risk_level", "LOW")

        # Fire alert for high/critical risk
        if risk in ("HIGH", "CRITICAL"):
            self.alert_manager.fire(Alert(
                alert_type="AI_RISK_ASSESSMENT",
                message=f"AI detected {risk} risk: {result.get('summary', 'N/A')}",
                severity=Severity.CRITICAL if risk == "CRITICAL" else Severity.ERROR,
                source="ai_analyzer",
                metadata={
                    "risk_level": risk,
                    "anomaly_count": len(result.get("anomalies", [])),
                    "threat_count": len(result.get("security_threats", [])),
                },
            ))

        # Fire individual threat alerts from AI
        for threat in result.get("security_threats", []):
            self.alert_manager.fire(Alert(
                alert_type=f"AI_THREAT_{threat.get('threat_type', 'unknown').upper()}",
                message=threat.get("description", "AI-detected security threat"),
                severity=threat.get("severity", Severity.WARNING),
                source="ai_analyzer",
                metadata=threat,
            ))

        # Fire anomaly alerts from AI
        for anomaly in result.get("anomalies", []):
            sev = anomaly.get("severity", Severity.WARNING)
            if Severity.gte(sev, Severity.ERROR):
                self.alert_manager.fire(Alert(
                    alert_type=f"AI_ANOMALY_{anomaly.get('type', 'unknown').upper()}",
                    message=anomaly.get("description", "AI-detected anomaly"),
                    severity=sev,
                    source="ai_analyzer",
                    metadata=anomaly,
                ))

    # ── Public interface ─────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Return watcher runtime statistics."""
        return {
            "lines_processed": self._lines_processed,
            "ai_analyses_run": self._analyses_run,
            "buffer_size": len(self._buffer),
            "alert_stats": self.alert_manager.get_stats(),
        }

    def run(self):
        """Main loop — poll log files and process new entries."""
        logger.info("LogWatcher starting — poll interval=%.1fs, AI batch size=%d",
                     self.poll_interval, Config.AI_LOG_BATCH_SIZE)

        while not self._stop_event.is_set():
            try:
                # Read new lines from both log files
                app_lines = self._app_tailer.read_new_lines()
                sec_lines = self._sec_tailer.read_new_lines()
                all_lines = app_lines + sec_lines

                if all_lines:
                    self._process_lines(all_lines)
                    self._maybe_run_ai_analysis()

            except Exception as exc:
                logger.error("LogWatcher loop error: %s", exc)

            self._stop_event.wait(self.poll_interval)

        logger.info("LogWatcher stopped — processed %d lines, ran %d analyses",
                     self._lines_processed, self._analyses_run)

    def stop(self):
        """Signal the run loop to exit."""
        self._stop_event.set()
