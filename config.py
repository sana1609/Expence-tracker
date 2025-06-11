"""
Configuration settings for the expense tracker application.
This separates configuration from application code to make it more production-ready.
"""
import os
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Application environment settings
ENV = os.getenv("APP_ENV", "development")  # 'development', 'testing', or 'production'
DEBUG = ENV != "production"
VERSION = "1.0.0"

# Database settings
DATABASE_URL = os.getenv("SQL_URL")

# Logging settings
LOG_LEVEL = {
    "development": logging.DEBUG,
    "testing": logging.INFO,
    "production": logging.WARNING
}.get(ENV, logging.DEBUG)

# Maximum file size for logs in MB
LOG_FILE_MAX_SIZE_MB = int(os.getenv("LOG_FILE_MAX_SIZE_MB", 10))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 10))

# Application secrets
SECRET_KEY = os.getenv("SECRET_KEY", "dev-key-please-change-in-production")

# Error monitoring (e.g., Sentry)
ENABLE_SENTRY = ENV == "production"
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Other application settings
DEFAULT_CURRENCY = "₹"
DEFAULT_LANGUAGE = "en"
