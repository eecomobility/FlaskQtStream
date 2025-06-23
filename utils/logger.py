import logging
from datetime import datetime

def get_shared_logger():
    logger = logging.getLogger("shared_logger")
    if not logger.handlers:
        handler = logging.FileHandler("time_delay_logs.log", mode="a")
        formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler.setFormatter(formatter)
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
    return logger
