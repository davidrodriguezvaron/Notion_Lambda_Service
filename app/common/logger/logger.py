import logging
import sys
from app.common.environment.environment_handler import environment_handler


def get_logger(name):
    """
    Returns a configured logger based on the environment.

    Uses EnvironmentHandler to determine if running in AWS Lambda
    and to set the appropriate log level.
    """
    logger = logging.getLogger(name)

    # Clear existing handlers to avoid duplicate logs if get_logger is called multiple times
    if logger.handlers:
        logger.handlers.clear()

    # Set log level
    log_level = environment_handler.log_level
    logger.setLevel(log_level)

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    # Create formatter
    # Lambda runtime already adds timestamp and request ID to CloudWatch logs,
    # but we add a consistent format for clarity.
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    # Prevent propagation to root logger to avoid double logging in some environments
    logger.propagate = False

    return logger
