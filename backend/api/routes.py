"""
API Routes
RESTful endpoints for the AI DevOps Monitoring Dashboard.

All routes are prefixed with /api/v1/ and return JSON.
"""

import json
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

from config import Config
from utils.logger import setup_logger

logger = setup_logger("api", "logs/api.log")

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")

# ── Lazy references to shared services ────────────────────────────────────────
# These are set by register_routes() after app init to avoid circular imports.

_log_watcher = None


def _get_watcher():
    """Return the LogWatcher instance, importing lazily to avoid circular deps."""
    global _log_watcher
    if _log_watcher is None:
        from core.log_watcher import LogWatcher
        _log_watcher = LogWatcher()
    return _log_watcher


def set_watcher(watcher):
    """Allow app.py to inject the running LogWatcher instance."""
    global _log_watcher
    _log_watcher = watcher


# ── Health & Status ───────────────────────────────────────────────────────────

@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
        "services": {
            "log_generator": "running",
            "log_watcher": "running",
            "ai_analysis": "enabled" if Config.ENABLE_AI_ANALYSIS else "disabled",
            "sns_alerts": "enabled" if Config.ENABLE_SNS_ALERTS else "disabled",
        },
    }), 200


@api_bp.route("/status", methods=["GET"])
def system_status():
    """Detailed system status with watcher statistics."""
    watcher = _get_watcher()
    stats = watcher.get_stats()
    return jsonify({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "ai_provider": Config.AI_PROVIDER,
            "ai_enabled": Config.ENABLE_AI_ANALYSIS,
            "sns_enabled": Config.ENABLE_SNS_ALERTS,
            "log_generation_interval": Config.LOG_GENERATION_INTERVAL,
            "ai_batch_size": Config.AI_LOG_BATCH_SIZE,
        },
        "watcher_stats": stats,
    }), 200


# ── Logs ──────────────────────────────────────────────────────────────────────

@api_bp.route("/logs", methods=["GET"])
def get_logs():
    """
    Retrieve recent log entries.

    Query params:
      ?type=application|security   (default: application)
      ?limit=100                   (max 500)
      ?level=ERROR                 (filter by level)
    """
    log_type = request.args.get("type", "application")
    limit = min(int(request.args.get("limit", 100)), 500)
    level_filter = request.args.get("level", "").upper()

    log_file = Config.APP_LOG_FILE if log_type == "application" else Config.SECURITY_LOG_FILE

    if not os.path.exists(log_file):
        return jsonify({"logs": [], "total": 0, "message": "Log file not found"}), 200

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()

        # Parse JSON lines
        entries = []
        for line in reversed(lines):  # most recent first
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if level_filter and entry.get("level") != level_filter:
                    continue
                entries.append(entry)
                if len(entries) >= limit:
                    break
            except (json.JSONDecodeError, ValueError):
                continue

        return jsonify({
            "logs": entries,
            "total": len(entries),
            "log_type": log_type,
            "level_filter": level_filter or None,
        }), 200

    except Exception as exc:
        logger.error("Failed to read logs: %s", exc)
        return jsonify({"error": "Failed to read logs", "details": str(exc)}), 500


@api_bp.route("/logs/stream", methods=["GET"])
def get_log_stream():
    """
    Return the latest N log lines for live-tail display.

    Query params:
      ?lines=20  (default 20, max 100)
    """
    count = min(int(request.args.get("lines", 20)), 100)

    results = {"application": [], "security": []}
    for log_type, path in [("application", Config.APP_LOG_FILE), ("security", Config.SECURITY_LOG_FILE)]:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
            tail = lines[-count:] if len(lines) >= count else lines
            for line in tail:
                line = line.strip()
                if line:
                    try:
                        results[log_type].append(json.loads(line))
                    except (json.JSONDecodeError, ValueError):
                        results[log_type].append({"raw": line})
        except Exception as exc:
            logger.error("Failed to stream %s logs: %s", log_type, exc)

    return jsonify(results), 200


# ── Alerts ────────────────────────────────────────────────────────────────────

@api_bp.route("/alerts", methods=["GET"])
def get_alerts():
    """
    Retrieve alerts.

    Query params:
      ?limit=50
      ?severity=CRITICAL
      ?acknowledged=false
    """
    watcher = _get_watcher()
    limit = min(int(request.args.get("limit", 50)), 200)
    severity = request.args.get("severity")
    ack_param = request.args.get("acknowledged")
    acknowledged = None
    if ack_param is not None:
        acknowledged = ack_param.lower() == "true"

    alerts = watcher.alert_manager.get_alerts(
        limit=limit, severity=severity, acknowledged=acknowledged,
    )
    stats = watcher.alert_manager.get_stats()

    return jsonify({
        "alerts": alerts,
        "total_returned": len(alerts),
        "stats": stats,
    }), 200


@api_bp.route("/alerts/<alert_id>/acknowledge", methods=["POST"])
def acknowledge_alert(alert_id: str):
    """Mark an alert as acknowledged."""
    watcher = _get_watcher()
    found = watcher.alert_manager.acknowledge(alert_id)
    if found:
        return jsonify({"message": f"Alert {alert_id} acknowledged"}), 200
    return jsonify({"error": f"Alert {alert_id} not found"}), 404


@api_bp.route("/alerts/stats", methods=["GET"])
def alert_stats():
    """Return alert summary statistics."""
    watcher = _get_watcher()
    return jsonify(watcher.alert_manager.get_stats()), 200


# ── AI Analysis ───────────────────────────────────────────────────────────────

@api_bp.route("/analysis/latest", methods=["GET"])
def latest_analysis():
    """Return the most recent AI analysis result."""
    watcher = _get_watcher()
    result = watcher.ai_analyzer.get_latest()
    if result:
        return jsonify(result), 200
    return jsonify({"message": "No analysis available yet"}), 200


@api_bp.route("/analysis/history", methods=["GET"])
def analysis_history():
    """
    Return AI analysis history.

    Query params:
      ?limit=20
    """
    watcher = _get_watcher()
    limit = min(int(request.args.get("limit", 20)), 100)
    history = watcher.ai_analyzer.get_history(limit=limit)
    return jsonify({
        "analyses": history,
        "total": len(history),
    }), 200


@api_bp.route("/analysis/trigger", methods=["POST"])
def trigger_analysis():
    """
    Manually trigger an AI analysis on recent logs.

    Body (optional JSON):
      {"log_type": "application", "lines": 50}
    """
    watcher = _get_watcher()
    body = request.get_json(silent=True) or {}
    log_type = body.get("log_type", "application")
    line_count = min(int(body.get("lines", Config.AI_LOG_BATCH_SIZE)), 200)

    log_file = Config.APP_LOG_FILE if log_type == "application" else Config.SECURITY_LOG_FILE

    if not os.path.exists(log_file):
        return jsonify({"error": "Log file not found"}), 404

    try:
        with open(log_file, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()

        recent = [l.strip() for l in lines[-line_count:] if l.strip()]
        if not recent:
            return jsonify({"error": "No log entries to analyze"}), 400

        result = watcher.ai_analyzer.analyze(recent)
        return jsonify(result), 200

    except Exception as exc:
        logger.error("Manual analysis trigger failed: %s", exc)
        return jsonify({"error": "Analysis failed", "details": str(exc)}), 500


# ── Dashboard Aggregated View ────────────────────────────────────────────────

@api_bp.route("/dashboard", methods=["GET"])
def dashboard():
    """
    Aggregated dashboard payload — a single call that returns
    everything the frontend needs to render the main view.
    """
    watcher = _get_watcher()

    # Latest analysis
    latest = watcher.ai_analyzer.get_latest()

    # Recent alerts (top 10 unacknowledged)
    recent_alerts = watcher.alert_manager.get_alerts(limit=10, acknowledged=False)

    # Watcher stats
    stats = watcher.get_stats()

    # Log level distribution (quick scan of last 200 app log lines)
    level_dist = {"INFO": 0, "WARNING": 0, "ERROR": 0, "CRITICAL": 0}
    if os.path.exists(Config.APP_LOG_FILE):
        try:
            with open(Config.APP_LOG_FILE, "r", encoding="utf-8", errors="replace") as fh:
                tail = fh.readlines()[-200:]
            for line in tail:
                try:
                    entry = json.loads(line.strip())
                    lvl = entry.get("level", "INFO")
                    if lvl in level_dist:
                        level_dist[lvl] += 1
                except (json.JSONDecodeError, ValueError):
                    pass
        except Exception:
            pass

    return jsonify({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_health": "healthy",
        "risk_level": latest.get("risk_level", "UNKNOWN") if latest else "UNKNOWN",
        "watcher_stats": stats,
        "latest_analysis": latest,
        "recent_alerts": recent_alerts,
        "log_level_distribution": level_dist,
        "config_summary": {
            "ai_provider": Config.AI_PROVIDER,
            "ai_enabled": Config.ENABLE_AI_ANALYSIS,
            "sns_enabled": Config.ENABLE_SNS_ALERTS,
        },
    }), 200


# ── Route Registration ───────────────────────────────────────────────────────

def register_routes(app):
    """Register the API blueprint with the Flask app."""
    app.register_blueprint(api_bp)
    logger.info("API routes registered under /api/v1/")
