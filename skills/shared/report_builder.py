"""
Report builder for Skills.

Provides utilities for building formatted reports in various formats.
"""

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class ReportFormat(Enum):
    """Supported report formats."""

    MARKDOWN = "markdown"
    JSON = "json"
    TEXT = "text"
    HTML = "html"


@dataclass
class ReportSection:
    """A section in a report."""

    title: str
    content: str
    level: int = 2  # Heading level (1-6)
    data: Any = None  # Optional structured data


@dataclass
class TableColumn:
    """Table column definition."""

    header: str
    key: str
    align: str = "left"  # left, center, right
    format_fn: callable = None  # Optional formatting function


class ReportBuilder:
    """
    Builder for creating formatted reports.

    Supports Markdown, JSON, Text, and HTML formats.
    """

    def __init__(self, title: str, report_format: ReportFormat = ReportFormat.MARKDOWN):
        """
        Initialize report builder.

        Args:
            title: Report title
            report_format: Output format
        """
        self.title = title
        self.format = report_format
        self.sections: list[ReportSection] = []
        self.metadata: dict[str, Any] = {
            "generated_at": datetime.now().isoformat(),
            "title": title,
        }

    def add_section(
        self,
        title: str,
        content: str = "",
        level: int = 2,
        data: Any = None,
    ) -> "ReportBuilder":
        """
        Add a section to the report.

        Args:
            title: Section title
            content: Section content (text)
            level: Heading level
            data: Optional structured data

        Returns:
            Self for chaining
        """
        self.sections.append(ReportSection(title, content, level, data))
        return self

    def add_text(self, text: str) -> "ReportBuilder":
        """Add plain text to the last section or create new one."""
        if self.sections:
            self.sections[-1].content += text
        else:
            self.add_section("", text, level=0)
        return self

    def add_line(self, text: str = "") -> "ReportBuilder":
        """Add a line of text."""
        return self.add_text(text + "\n")

    def add_blank_line(self) -> "ReportBuilder":
        """Add a blank line."""
        return self.add_text("\n")

    def add_list(self, items: list[str], ordered: bool = False) -> "ReportBuilder":
        """
        Add a list.

        Args:
            items: List items
            ordered: Use numbered list

        Returns:
            Self for chaining
        """
        if self.format == ReportFormat.MARKDOWN:
            for i, item in enumerate(items):
                prefix = f"{i + 1}." if ordered else "-"
                self.add_line(f"{prefix} {item}")
        else:
            for i, item in enumerate(items):
                prefix = f"{i + 1}." if ordered else "*"
                self.add_line(f"{prefix} {item}")
        return self

    def add_key_value(self, key: str, value: Any) -> "ReportBuilder":
        """Add a key-value pair."""
        formatted_value = self._format_value(value)
        if self.format == ReportFormat.MARKDOWN:
            self.add_line(f"- **{key}**: {formatted_value}")
        else:
            self.add_line(f"{key}: {formatted_value}")
        return self

    def add_table(
        self,
        data: list[dict],
        columns: list[TableColumn] = None,
    ) -> "ReportBuilder":
        """
        Add a table.

        Args:
            data: List of dicts (rows)
            columns: Column definitions (default: auto from keys)

        Returns:
            Self for chaining
        """
        if not data:
            return self

        # Auto-generate columns if not provided
        if columns is None:
            keys = list(data[0].keys())
            columns = [TableColumn(header=k, key=k) for k in keys]

        if self.format == ReportFormat.MARKDOWN:
            self._add_markdown_table(data, columns)
        elif self.format == ReportFormat.HTML:
            self._add_html_table(data, columns)
        else:
            self._add_text_table(data, columns)

        return self

    def _add_markdown_table(self, data: list[dict], columns: list[TableColumn]) -> None:
        """Add markdown formatted table."""
        # Header row
        headers = [col.header for col in columns]
        self.add_line("| " + " | ".join(headers) + " |")

        # Separator row with alignment
        separators = []
        for col in columns:
            if col.align == "center":
                separators.append(":---:")
            elif col.align == "right":
                separators.append("---:")
            else:
                separators.append("---")
        self.add_line("| " + " | ".join(separators) + " |")

        # Data rows
        for row in data:
            cells = []
            for col in columns:
                value = row.get(col.key, "")
                if col.format_fn:
                    value = col.format_fn(value)
                cells.append(str(self._format_value(value)))
            self.add_line("| " + " | ".join(cells) + " |")

    def _add_html_table(self, data: list[dict], columns: list[TableColumn]) -> None:
        """Add HTML formatted table."""
        self.add_line("<table>")
        self.add_line("<thead><tr>")
        for col in columns:
            self.add_line(f"  <th>{col.header}</th>")
        self.add_line("</tr></thead>")
        self.add_line("<tbody>")
        for row in data:
            self.add_line("<tr>")
            for col in columns:
                value = row.get(col.key, "")
                if col.format_fn:
                    value = col.format_fn(value)
                self.add_line(f"  <td>{self._format_value(value)}</td>")
            self.add_line("</tr>")
        self.add_line("</tbody>")
        self.add_line("</table>")

    def _add_text_table(self, data: list[dict], columns: list[TableColumn]) -> None:
        """Add plain text formatted table."""
        # Calculate column widths
        widths = {}
        for col in columns:
            widths[col.key] = len(col.header)
            for row in data:
                value = str(self._format_value(row.get(col.key, "")))
                widths[col.key] = max(widths[col.key], len(value))

        # Header
        header_parts = []
        for col in columns:
            header_parts.append(col.header.ljust(widths[col.key]))
        self.add_line(" | ".join(header_parts))

        # Separator
        sep_parts = ["-" * widths[col.key] for col in columns]
        self.add_line("-+-".join(sep_parts))

        # Data rows
        for row in data:
            row_parts = []
            for col in columns:
                value = str(self._format_value(row.get(col.key, "")))
                if col.align == "right":
                    row_parts.append(value.rjust(widths[col.key]))
                elif col.align == "center":
                    row_parts.append(value.center(widths[col.key]))
                else:
                    row_parts.append(value.ljust(widths[col.key]))
            self.add_line(" | ".join(row_parts))

    def add_code_block(self, code: str, language: str = "") -> "ReportBuilder":
        """Add a code block."""
        if self.format == ReportFormat.MARKDOWN:
            self.add_line(f"```{language}")
            self.add_text(code)
            if not code.endswith("\n"):
                self.add_line("")
            self.add_line("```")
        elif self.format == ReportFormat.HTML:
            self.add_line(f"<pre><code class='{language}'>")
            self.add_text(code)
            self.add_line("</code></pre>")
        else:
            self.add_text(code)
            self.add_blank_line()
        return self

    def add_divider(self) -> "ReportBuilder":
        """Add a horizontal divider."""
        if self.format == ReportFormat.MARKDOWN:
            self.add_line("\n---\n")
        elif self.format == ReportFormat.HTML:
            self.add_line("<hr>")
        else:
            self.add_line("-" * 40)
        return self

    def add_alert(self, message: str, level: str = "info") -> "ReportBuilder":
        """
        Add an alert/callout box.

        Args:
            message: Alert message
            level: Alert level (info, warning, error, success)

        Returns:
            Self for chaining
        """
        icons = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
        icon = icons.get(level, "")

        if self.format == ReportFormat.MARKDOWN:
            self.add_line(f"> {icon} **{level.upper()}**: {message}")
        else:
            self.add_line(f"[{level.upper()}] {message}")
        return self

    def set_metadata(self, key: str, value: Any) -> "ReportBuilder":
        """Set metadata value."""
        self.metadata[key] = value
        return self

    def _format_value(self, value: Any) -> str:
        """Format a value for display."""
        if value is None:
            return "-"
        if isinstance(value, Decimal):
            # Format decimal with appropriate precision
            if abs(value) >= 1000:
                return f"{value:,.2f}"
            elif abs(value) >= 1:
                return f"{value:.2f}"
            else:
                return f"{value:.4f}"
        if isinstance(value, float):
            if abs(value) >= 1000:
                return f"{value:,.2f}"
            return f"{value:.2f}"
        if isinstance(value, (date, datetime)):
            return value.strftime("%Y-%m-%d")
        if isinstance(value, bool):
            return "Yes" if value else "No"
        return str(value)

    def build(self) -> str:
        """
        Build the final report.

        Returns:
            Formatted report string
        """
        if self.format == ReportFormat.JSON:
            return self._build_json()
        elif self.format == ReportFormat.HTML:
            return self._build_html()
        else:
            return self._build_text()

    def _build_text(self) -> str:
        """Build markdown/text report."""
        lines = []

        # Title
        if self.format == ReportFormat.MARKDOWN:
            lines.append(f"# {self.title}")
        else:
            lines.append(self.title)
            lines.append("=" * len(self.title))
        lines.append("")

        # Generated timestamp
        lines.append(f"*Generated: {self.metadata['generated_at']}*")
        lines.append("")

        # Sections
        for section in self.sections:
            if section.title:
                if self.format == ReportFormat.MARKDOWN:
                    prefix = "#" * section.level
                    lines.append(f"{prefix} {section.title}")
                else:
                    lines.append(section.title)
                    lines.append("-" * len(section.title))
                lines.append("")

            if section.content:
                lines.append(section.content)

        return "\n".join(lines)

    def _build_json(self) -> str:
        """Build JSON report."""
        report_data = {
            "metadata": self.metadata,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "data": s.data,
                }
                for s in self.sections
            ],
        }

        # Custom JSON encoder for Decimal and date
        def encoder(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, (date, datetime)):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        return json.dumps(report_data, indent=2, default=encoder, ensure_ascii=False)

    def _build_html(self) -> str:
        """Build HTML report."""
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            f"  <title>{self.title}</title>",
            "  <style>",
            "    body { font-family: -apple-system, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            "    table { border-collapse: collapse; width: 100%; margin: 10px 0; }",
            "    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "    th { background-color: #f5f5f5; }",
            "    pre { background-color: #f5f5f5; padding: 10px; overflow-x: auto; }",
            "    hr { border: none; border-top: 1px solid #ddd; margin: 20px 0; }",
            "  </style>",
            "</head>",
            "<body>",
            f"  <h1>{self.title}</h1>",
            f"  <p><em>Generated: {self.metadata['generated_at']}</em></p>",
        ]

        for section in self.sections:
            if section.title:
                lines.append(f"  <h{section.level}>{section.title}</h{section.level}>")
            if section.content:
                # Convert content to HTML paragraphs
                content_html = section.content.replace("\n\n", "</p><p>")
                content_html = content_html.replace("\n", "<br>")
                lines.append(f"  <p>{content_html}</p>")

        lines.extend(["</body>", "</html>"])
        return "\n".join(lines)


# Convenience functions
def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage."""
    if value is None:
        return "-"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_currency(value: float, currency: str = "") -> str:
    """Format value as currency."""
    if value is None:
        return "-"
    formatted = f"{value:,.2f}"
    if currency:
        return f"{currency} {formatted}"
    return formatted


def format_score(value: float) -> str:
    """Format value as score with rating."""
    if value is None:
        return "-"
    if value >= 80:
        rating = "Excellent"
    elif value >= 60:
        rating = "Good"
    elif value >= 40:
        rating = "Fair"
    else:
        rating = "Poor"
    return f"{value:.1f} ({rating})"
