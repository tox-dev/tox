"""This module handles collecting and persisting test reports in various formats."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .env import EnvJournal
from .main import Journal

if TYPE_CHECKING:
    from tox.config.main import Config


def write_journal(path: Path | None, journal: Journal, config: Config | None = None) -> None:
    """
    Write journal to file using the configured format.

    :param path: path to write the report to
    :param journal: the journal containing test results
    :param config: optional config to determine format (if None, uses JSON default)
    """
    if path is None:
        return

    # Determine format from config or default to JSON
    report_format: str | None = None
    if config is not None:
        try:
            report_format = config.core["report_format"]
        except KeyError:
            report_format = None

    # If no format specified, default to JSON (backward compatibility)
    if report_format is None:
        report_format = "json"

    # Get formatter from registry
    from tox.report.formatter import REGISTER  # noqa: PLC0415

    formatter = REGISTER.get(report_format)
    if formatter is None:
        # Fallback to JSON if format not found
        from tox.report.formatters import JsonFormatter  # noqa: PLC0415

        formatter = JsonFormatter()

    # Ensure output path has correct extension if it doesn't match formatter
    output_path = Path(path)
    if not output_path.suffix or output_path.suffix != formatter.file_extension:
        output_path = output_path.with_suffix(formatter.file_extension)

    # Format and write
    formatter.format(journal, output_path)


__all__ = (
    "EnvJournal",
    "Journal",
    "write_journal",
)
