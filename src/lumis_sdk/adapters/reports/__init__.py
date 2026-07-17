"""Reference report-writer adapters."""

from .json_report import (
    JsonReportWriter,
    diagnosis_report_json_schema,
    legacy_diagnosis_report_json_schema,
    parse_json_report,
    render_json_report,
)
from .markdown import MarkdownReportWriter, append_resolution, render_markdown_report

__all__ = [
    "JsonReportWriter",
    "MarkdownReportWriter",
    "append_resolution",
    "diagnosis_report_json_schema",
    "legacy_diagnosis_report_json_schema",
    "parse_json_report",
    "render_json_report",
    "render_markdown_report",
]
