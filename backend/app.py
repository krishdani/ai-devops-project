"""
AI-Powered DevOps Monitoring & Security Platform
Main Application Entry Point
"""

import os
import threading
import time
from flask import Flask
from flask_cors import CORS

from config import Config
from api.routes import register_routes, set_watcher
from core.log_generator import LogGenerator
from core.log_watcher import LogWatcher
from utils.logger import setup_logger

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend communication
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Setup application logger
logger = setup_logger("app", "logs/app.log")

# Register all API routes
register_routes(app)


def start_background_services():
    """Start background services: log generator and log watcher."""
    # Start the synthetic log generator (simulates real app logs)
    log_gen = LogGenerator(interval=Config.LOG_GENERATION_INTERVAL)
    gen_thread = threading.Thread(target=log_gen.run, daemon=True)
    gen_thread.start()
    logger.info("Log generator service started.")

    # Start the log watcher (monitors logs, triggers AI analysis + SNS alerts)
    log_watcher = LogWatcher()
    set_watcher(log_watcher)  # Share with API routes for dashboard access
    watcher_thread = threading.Thread(target=log_watcher.run, daemon=True)
    watcher_thread.start()
    logger.info("Log watcher service started.")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AI DevOps Monitoring Platform Starting...")
    logger.info("=" * 60)

    # Start background services in separate threads
    start_background_services()

    # Give services a moment to initialize
    time.sleep(1)

    logger.info(f"Server starting on port {Config.PORT}")
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG,
        use_reloader=False  # Disable reloader to prevent duplicate threads
    )
