"""
Configuration Management for AI DevOps Monitoring Platform
All settings are loaded from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv()


class Config:
    # ─── Flask ────────────────────────────────────────────────────────────────
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    PORT = int(os.getenv("PORT", 5000))

    # ─── Logging ──────────────────────────────────────────────────────────────
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    APP_LOG_FILE = os.path.join(LOG_DIR, "application.log")
    SECURITY_LOG_FILE = os.path.join(LOG_DIR, "security.log")
    ALERTS_DB_FILE = os.path.join(LOG_DIR, "alerts.json")

    # How often (seconds) the synthetic log generator fires
    LOG_GENERATION_INTERVAL = float(os.getenv("LOG_GENERATION_INTERVAL", 5))

    # ─── AI Provider ─────────────────────────────────────────────────────────
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")   # "openai" | "anthropic"
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

    # How many log lines to send to AI per analysis request
    AI_LOG_BATCH_SIZE = int(os.getenv("AI_LOG_BATCH_SIZE", 50))

    # ─── AWS ──────────────────────────────────────────────────────────────────
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")

    # SNS Topic ARN for alert notifications
    SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", "")

    # CloudWatch configuration
    CLOUDWATCH_LOG_GROUP = os.getenv("CLOUDWATCH_LOG_GROUP", "/ai-devops-platform/application")
    CLOUDWATCH_LOG_STREAM = os.getenv("CLOUDWATCH_LOG_STREAM", "app-stream")

    # ─── Alert Thresholds ─────────────────────────────────────────────────────
    # Number of errors in the last N minutes to trigger an alert
    ERROR_ALERT_THRESHOLD = int(os.getenv("ERROR_ALERT_THRESHOLD", 5))
    ERROR_ALERT_WINDOW_MINUTES = int(os.getenv("ERROR_ALERT_WINDOW_MINUTES", 5))

    # Failed login attempts within window that triggers brute-force alert
    BRUTE_FORCE_THRESHOLD = int(os.getenv("BRUTE_FORCE_THRESHOLD", 5))
    BRUTE_FORCE_WINDOW_SECONDS = int(os.getenv("BRUTE_FORCE_WINDOW_SECONDS", 60))

    # ─── Feature Flags ────────────────────────────────────────────────────────
    ENABLE_AWS = os.getenv("ENABLE_AWS", "false").lower() == "true"
    ENABLE_AI_ANALYSIS = os.getenv("ENABLE_AI_ANALYSIS", "true").lower() == "true"
    ENABLE_SNS_ALERTS = os.getenv("ENABLE_SNS_ALERTS", "false").lower() == "true"
    ENABLE_CLOUDWATCH = os.getenv("ENABLE_CLOUDWATCH", "false").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate critical configuration values."""
        warnings = []
        if cls.ENABLE_AI_ANALYSIS:
            if cls.AI_PROVIDER == "openai" and not cls.OPENAI_API_KEY:
                warnings.append("OPENAI_API_KEY is not set. AI analysis will be disabled.")
            if cls.AI_PROVIDER == "anthropic" and not cls.ANTHROPIC_API_KEY:
                warnings.append("ANTHROPIC_API_KEY is not set. AI analysis will be disabled.")
        if cls.ENABLE_SNS_ALERTS and not cls.SNS_TOPIC_ARN:
            warnings.append("SNS_TOPIC_ARN is not set. SNS alerts will be disabled.")
        return warnings
