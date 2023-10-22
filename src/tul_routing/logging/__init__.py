import logging
import warnings
from typing import Any

_logger = logging.getLogger('viroco')
_logger.setLevel(logging.INFO)

_stream = logging.StreamHandler()
_stream.setLevel(logging.INFO)
_logger.addHandler(_stream)
_logger.propagate = False

logger = _logger
logger.warn = warnings.warn


def __set_level(level: Any):
    logger.setLevel(level)
    _stream.setLevel(level)


logger.set_level_for_all = __set_level

__all__ = ['logger']
