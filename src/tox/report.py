"""Handle reporting from within tox"""
import logging
import os
import sys
from typing import Union

from colorama import Fore, Style, deinit, init

LEVELS = {
    0: logging.CRITICAL,
    1: logging.ERROR,
    2: logging.WARNING,
    3: logging.INFO,
    4: logging.DEBUG,
    5: logging.NOTSET,
}

MAX_LEVEL = max(LEVELS.keys())
LOGGER = logging.getLogger()


class ToxHandler(logging.StreamHandler):
    def __init__(self, level: int, is_colored: bool) -> None:
        super().__init__(stream=sys.stdout)
        self.setLevel(level)
        if is_colored:
            deinit()
            init()
        self.error_formatter = self._get_formatter(logging.ERROR, level, is_colored)
        self.warning_formatter = self._get_formatter(logging.WARNING, level, is_colored)
        self.remaining_formatter = self._get_formatter(logging.INFO, level, is_colored)

    @staticmethod
    def _get_formatter(level: int, enabled_level: int, is_colored: bool) -> logging.Formatter:
        color: Union[int, str] = ""
        if is_colored:
            if level >= logging.ERROR:
                color = Fore.RED
            elif level >= logging.WARNING:
                color = Fore.CYAN
            else:
                color = Fore.WHITE
        fmt = (
            f"{Style.BRIGHT if color else ''}{Fore.MAGENTA if color else ''}"
            f"%(name)s: {color}%(message)s{Style.RESET_ALL if color else ''}"
        )
        if enabled_level <= logging.DEBUG:
            fmt = (
                f"%(relativeCreated)d %(levelname)s {fmt}{Style.DIM if color else ''}"
                f" [%(pathname)s:%(lineno)d]{Style.RESET_ALL if color else ''}"
            )
        formatter = logging.Formatter(fmt)
        return formatter

    def format(self, record: logging.LogRecord) -> str:
        # shorten the pathname to start from within the site-packages folder
        basename = os.path.dirname(record.pathname)
        sys_path_match = sorted([p for p in sys.path if basename.startswith(p)], key=len, reverse=True)
        record.pathname = record.pathname[len(sys_path_match[0]) + 1 :]

        if record.levelno >= logging.ERROR:
            return self.error_formatter.format(record)
        if record.levelno >= logging.WARNING:
            return self.warning_formatter.format(record)
        return self.remaining_formatter.format(record)


class LowerInfoLevel(logging.Filter):
    def __init__(self, level: int) -> None:
        super().__init__()
        self.level = level

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname in "INFO":
            record.levelno = logging.DEBUG
            record.levelname = "DEBUG"
        return record.levelno >= self.level


def setup_report(verbosity: int, is_colored: bool) -> None:
    _clean_handlers(LOGGER)
    level = _get_level(verbosity)
    LOGGER.setLevel(level)
    lower_info_level = LowerInfoLevel(level)
    for name in ("distlib.util", "filelock"):
        logger = logging.getLogger(name)
        logger.filters.clear()
        logger.addFilter(lower_info_level)
    handler = ToxHandler(level, is_colored)
    LOGGER.addHandler(handler)

    logging.debug("setup logging to %s", logging.getLevelName(level))


def _get_level(verbosity: int) -> int:
    if verbosity > MAX_LEVEL:
        verbosity = MAX_LEVEL
    level = LEVELS[verbosity]
    return level


def _clean_handlers(log: logging.Logger) -> None:
    for log_handler in list(log.handlers):  # remove handlers of libraries
        log.removeHandler(log_handler)


class HandledError(RuntimeError):
    """Error that has been handled so no need for stack trace"""
