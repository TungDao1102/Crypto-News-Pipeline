import logging
import logging.handlers
from enum import Enum
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"

class ErrorCode(str, Enum):
    QUEUE_OVERFLOW = "ERR_QUEUE_OVERFLOW"
    ALL_MODELS_EXHAUSTED = "ERR_ALL_MODELS_EXHAUSTED"
    PUBLISH_FAIL = "ERR_PUBLISH_FAIL"
    SOURCE_DISCONNECT = "ERR_SOURCE_DISCONNECT"
    JSON_VALIDATION_FAIL = "ERR_JSON_VALIDATION_FAIL"
    BINANCE_DAILY_LIMIT = "ERR_BINANCE_DAILY_LIMIT"
    BOT_PERMISSION = "ERR_BOT_PERMISSION"
    DLQ_ITEM_ADDED = "ERR_DLQ_ITEM_ADDED"
    QUEUE_DEPTH_CRITICAL = "ERR_QUEUE_DEPTH_CRITICAL"
    MODE_AUTO_SWITCH = "ERR_MODE_AUTO_SWITCH"

def ec(code: ErrorCode, message: str) -> str:
    """Format a structured error code prefix with message."""
    return f"[{code.value}] {message}"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: int = logging.DEBUG) -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    try:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            str(log_dir / "app.log"),
            maxBytes=50 * 1024 * 1024,
            backupCount=10,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except OSError as e:
        root_logger.warning("Could not create log file handler: %s", e)


LogLevelsConfig = dict[str, str] | None

def configure_module_levels(levels_config: LogLevelsConfig) -> None:
    if not levels_config:
        return
    for logger_name, level_name in levels_config.items():
        level = getattr(logging, level_name.upper(), None)
        if level is None:
            logging.getLogger(__name__).warning(
                "Invalid log level '%s' for logger '%s'", level_name, logger_name
            )
            continue
        logging.getLogger(logger_name).setLevel(level)
        logging.getLogger(__name__).info(
            "Set %s log level to %s", logger_name, level_name
        )
