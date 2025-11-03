"""Report formatter interface and registry."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from tox.journal.main import Journal

if TYPE_CHECKING:
    from pathlib import Path


class ReportFormatter(abc.ABC):
    """Base class for test report formatters."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Return the name/identifier of this formatter (e.g., 'xml', 'json')."""

    @property
    @abc.abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for this format (e.g., '.xml', '.json')."""

    @abc.abstractmethod
    def format(self, journal: Journal, output_path: Path | None = None) -> str | None:
        """
        Format the journal content and optionally write to file.

        :param journal: the journal containing test results
        :param output_path: optional path to write the formatted output to
        :return: the formatted content as string, or None if written to file
        """
        raise NotImplementedError


class ReportFormatterRegister:
    """Registry for report formatters."""

    def __init__(self) -> None:
        self._formatters: dict[str, ReportFormatter] = {}

    def register(self, formatter: ReportFormatter) -> None:
        """
        Register a report formatter.

        :param formatter: the formatter to register
        """
        if formatter.name in self._formatters:
            msg = f"formatter with name '{formatter.name}' already registered"
            raise ValueError(msg)
        self._formatters[formatter.name] = formatter

    def get(self, name: str) -> ReportFormatter | None:
        """
        Get a formatter by name.

        :param name: the formatter name
        :return: the formatter or None if not found
        """
        return self._formatters.get(name)

    def list_formatters(self) -> list[str]:
        """
        List all registered formatter names.

        :return: list of formatter names
        """
        return sorted(self._formatters.keys())


REGISTER = ReportFormatterRegister()

__all__ = (
    "ReportFormatter",
    "ReportFormatterRegister",
    "REGISTER",
)

