import logging
import os

LOG_LEVEL_ENV = 'SHIPPER_LOG_LEVEL'
DEFAULT_LEVEL = 'INFO'


def get_logger(name):
    level_str = os.getenv(LOG_LEVEL_ENV, DEFAULT_LEVEL)
    logger = logging.getLogger(name)
    try:
        level = logging.getLevelName(level_str)
        logger.setLevel(level)
    except Exception as e:
        logger.setLevel(logging.INFO)
        logger.warning(f'Could not set logger to level {level_str}, setting to default level {DEFAULT_LEVEL}: {e}')
    return logger
