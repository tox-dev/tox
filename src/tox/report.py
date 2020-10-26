"""Handle reporting from within tox"""
import logging
import os
import sys

from colorama import Fore, Style, init

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
    def __init__(self, level: int) -> None:
        super().__init__(stream=sys.stdout)
        self.setLevel(level)
        self.error_formatter = self._get_formatter(logging.ERROR, level)
        self.warning_formatter = self._get_formatter(logging.WARNING, level)
        self.remaining_formatter = self._get_formatter(logging.INFO, level)

    @staticmethod
    def _get_formatter(level: int, enabled_level: int) -> logging.Formatter:
        if level >= logging.ERROR:
            color = Fore.RED
        elif level >= logging.WARNING:
            color = Fore.CYAN
        elif level >= logging.INFO:
            color = Fore.WHITE
        else:
            color = Fore.GREEN
        fmt = f"{Style.BRIGHT}{Fore.MAGENTA}%(name)s: {color}%(message)s{Style.RESET_ALL}"
        if enabled_level <= logging.DEBUG:
            fmt = f"%(relativeCreated)d %(levelname)s {fmt}{Style.DIM} [%(pathname)s:%(lineno)d]{Style.RESET_ALL}"
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
    MAP = {"INFO": "DEBUG", "DEBUG": "TRACE", "TRACE": "TRACE"}

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname in LowerInfoLevel.MAP:
            record.levelno = max(record.levelno - 10, 0)
            record.levelname = LowerInfoLevel.MAP[record.levelname]
        return True


def setup_report(verbosity: int, is_colored: bool) -> None:
    _clean_handlers(LOGGER)
    level = _get_level(verbosity)
    LOGGER.setLevel(level)
    lower_info_level = LowerInfoLevel()
    logging.getLogger("distlib.util").addFilter(lower_info_level)
    logging.getLogger("filelock").addFilter(lower_info_level)
    handler = ToxHandler(level)
    LOGGER.addHandler(handler)

    logging.debug("setup logging to %s", logging.getLevelName(level))
    if is_colored:
        init()


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
