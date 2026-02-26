"""
MapGen — Thread-safe logging.

Provides safe_print() and is_latin_script() utilities used throughout the engine.
"""

import logging

_logger = logging.getLogger("mapgen")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)


def safe_print(msg: str) -> None:
    """Thread-safe print that won't crash in Flask background threads."""
    try:
        _logger.info(msg)
    except OSError:
        pass


def is_latin_script(text: str) -> bool:
    """Check if text is primarily Latin script (for letter-spacing decisions)."""
    if not text:
        return True
    latin_count = 0
    total_alpha = 0
    for char in text:
        if char.isalpha():
            total_alpha += 1
            if ord(char) < 0x250:
                latin_count += 1
    if total_alpha == 0:
        return True
    return (latin_count / total_alpha) > 0.8
