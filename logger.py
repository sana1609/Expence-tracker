import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import sys
import traceback

try:
    from config import LOG_LEVEL, LOG_FILE_MAX_SIZE_MB, LOG_BACKUP_COUNT, ENV
except ImportError:
    # Default values if config.py is not available
    ENV = "development"
    LOG_LEVEL = logging.INFO
    LOG_FILE_MAX_SIZE_MB = 10
    LOG_BACKUP_COUNT = 10

# Create logs directory if it doesn't exist
logs_dir = "logs"
if not os.path.exists(logs_dir):
    os.makedirs(logs_dir)

# Set up logger
def setup_logger(name, log_file=None, level=None):
    """
    Set up and return a logger with specified name, log file, and level
    """
    # Use config level if not specified
    if level is None:
        level = LOG_LEVEL
    
    # Create specific log file name if not provided
    if log_file is None:
        # In production, group logs by component
        # In development, include the date for easier debugging
        if ENV == "production":
            log_file = os.path.join(logs_dir, f"{name}.log")
        else:
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(logs_dir, f"{name}_{today}.log")
    
    # Set up logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers to avoid duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Create formatter with more details in development
    if ENV == "production":
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(filename)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    # Create file handler with configurable rotation
    file_handler = RotatingFileHandler(
        log_file, 
        maxBytes=LOG_FILE_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT, 
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Create console handler for errors and warnings
    # Only in development mode or for warnings and above in production
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

# Main application logger
app_logger = setup_logger('app')

# Database logger
db_logger = setup_logger('database')

# Authentication logger
auth_logger = setup_logger('auth')

# API logger for potential future API endpoints
api_logger = setup_logger('api')

# General utility functions for logging
def log_function_call(logger, func_name, args=None, kwargs=None):
    """Log function calls with arguments"""
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}
    
    args_str = ', '.join([str(arg) for arg in args])
    kwargs_str = ', '.join([f"{k}={v}" for k, v in kwargs.items()])
    params = ", ".join(filter(None, [args_str, kwargs_str]))
    
    logger.debug(f"Called function: {func_name}({params})")

def log_exception(logger, e, context=None):
    """Log exceptions with traceback and context"""
    if context:
        logger.error(f"Exception in {context}: {str(e)}")
    else:
        logger.error(f"Exception: {str(e)}")
    
    logger.debug(f"Traceback: {traceback.format_exc()}")

class LoggingContextManager:
    """Context manager for logging function execution time and exceptions"""
    
    def __init__(self, logger, context_name):
        self.logger = logger
        self.context_name = context_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.debug(f"Starting: {self.context_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            log_exception(self.logger, exc_val, self.context_name)
            return False  # re-raise the exception
        
        duration = (datetime.now() - self.start_time).total_seconds()
        self.logger.debug(f"Completed: {self.context_name} in {duration:.2f} seconds")
