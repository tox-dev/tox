"""Built-in report formatters."""

from __future__ import annotations

from tox.report.formatters.json import JsonFormatter
from tox.report.formatters.xml import XmlFormatter

__all__ = (
    "JsonFormatter",
    "XmlFormatter",
)

