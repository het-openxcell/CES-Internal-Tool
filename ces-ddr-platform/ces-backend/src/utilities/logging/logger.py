import sys

from loguru import logger as loguru_logger


def setup_logger():
    loguru_logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )

    loguru_logger.add(
        sys.stdout,
        level="DEBUG",
        format=log_format,
        colorize=True,
    )

    return loguru_logger


logger = setup_logger()
