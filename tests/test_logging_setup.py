from src.logging_setup import ErrorCode, ec, configure_module_levels
import logging

def test_error_code_enum_values():
    assert ErrorCode.QUEUE_OVERFLOW.value == "ERR_QUEUE_OVERFLOW"
    assert ec(ErrorCode.QUEUE_OVERFLOW, "test") == "[ERR_QUEUE_OVERFLOW] test"

def test_configure_module_levels_sets_level():
    configure_module_levels({"tests.test_logging_setup": "DEBUG"})
    logger = logging.getLogger("tests.test_logging_setup")
    assert logger.level == logging.DEBUG

def test_configure_module_levels_invalid_level():
    configure_module_levels({"tests.test_logging_setup": "INVALID"})

def test_configure_module_levels_none():
    configure_module_levels(None)
