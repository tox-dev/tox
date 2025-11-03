"""JSON report formatter."""

from __future__ import annotations

import json
import locale
from pathlib import Path

from tox.journal.main import Journal
from tox.report.formatter import ReportFormatter


class JsonFormatter(ReportFormatter):
    """JSON format report formatter."""

    @property
    def name(self) -> str:
        return "json"

    @property
    def file_extension(self) -> str:
        return ".json"

    def format(self, journal: Journal, output_path: Path | None = None) -> str | None:
        content = journal.content
        json_content = json.dumps(content, indent=2, ensure_ascii=False)

        if output_path is not None:
            with Path(output_path).open("w", encoding=locale.getpreferredencoding(do_setlocale=False)) as file_handler:
                file_handler.write(json_content)
            return None

        return json_content


__all__ = ("JsonFormatter",)

