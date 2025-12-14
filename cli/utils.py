"""CLI utility functions for enhanced user experience."""

import json
import sys
from enum import Enum
from typing import Any, Callable, Optional, Sequence

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

# Console instances
console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    """Output format options."""

    TABLE = "table"
    JSON = "json"
    CSV = "csv"


def print_success(message: str) -> None:
    """Print success message in green."""
    console.print(f"[bold green]Success:[/bold green] {message}")


def print_error(message: str, exit_code: Optional[int] = None) -> None:
    """Print error message in red."""
    error_console.print(f"[bold red]Error:[/bold red] {message}")
    if exit_code is not None:
        sys.exit(exit_code)


def print_warning(message: str) -> None:
    """Print warning message in yellow."""
    console.print(f"[bold yellow]Warning:[/bold yellow] {message}")


def print_info(message: str) -> None:
    """Print info message in blue."""
    console.print(f"[bold blue]Info:[/bold blue] {message}")


def print_panel(
    content: str, title: str = "", style: str = "blue", border_style: str = "blue"
) -> None:
    """Print content in a panel."""
    console.print(Panel(content, title=title, style=style, border_style=border_style))


def print_table(
    data: Sequence[dict],
    columns: Optional[list[tuple[str, str]]] = None,
    title: str = "",
    show_lines: bool = False,
) -> None:
    """
    Print data as a rich table.

    Args:
        data: List of dictionaries containing row data.
        columns: List of (key, header) tuples. If None, auto-detect from data.
        title: Optional table title.
        show_lines: Whether to show row separating lines.
    """
    if not data:
        console.print("[dim]No data to display[/dim]")
        return

    # Auto-detect columns if not provided
    if columns is None:
        first_row = data[0]
        columns = [(k, k.replace("_", " ").title()) for k in first_row.keys()]

    table = Table(title=title, show_lines=show_lines)

    # Add columns
    for key, header in columns:
        table.add_column(header, style="cyan" if key == columns[0][0] else None)

    # Add rows
    for row in data:
        values = []
        for key, _ in columns:
            value = row.get(key, "")
            # Format special values
            if isinstance(value, float):
                if key in ("pl_ratio", "weight", "change_pct"):
                    # Percentage formatting with color
                    color = "green" if value >= 0 else "red"
                    values.append(f"[{color}]{value:+.2%}[/{color}]")
                elif key in ("pl_val", "pl_value", "market_val", "market_value"):
                    color = "green" if value >= 0 else "red"
                    values.append(f"[{color}]{value:,.2f}[/{color}]")
                else:
                    values.append(f"{value:,.2f}")
            elif isinstance(value, int):
                values.append(f"{value:,}")
            elif isinstance(value, bool):
                values.append("[green]Yes[/green]" if value else "[red]No[/red]")
            else:
                values.append(str(value) if value is not None else "")
        table.add_row(*values)

    console.print(table)


def format_output(
    data: Sequence[dict],
    output_format: OutputFormat = OutputFormat.TABLE,
    columns: Optional[list[tuple[str, str]]] = None,
    title: str = "",
) -> str:
    """
    Format data for output.

    Args:
        data: List of dictionaries containing data.
        output_format: Output format (table, json, csv).
        columns: List of (key, header) tuples for column selection.
        title: Optional title for table format.

    Returns:
        Formatted string for json/csv, or empty string for table (prints directly).
    """
    if not data:
        return ""

    if output_format == OutputFormat.JSON:
        return json.dumps(data, indent=2, ensure_ascii=False, default=str)

    elif output_format == OutputFormat.CSV:
        import csv
        from io import StringIO

        output = StringIO()
        if columns:
            fieldnames = [k for k, _ in columns]
        else:
            fieldnames = list(data[0].keys())

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in data:
            # Convert non-string values
            clean_row = {k: str(v) if v is not None else "" for k, v in row.items()}
            writer.writerow(clean_row)

        return output.getvalue()

    else:  # TABLE
        print_table(data, columns, title)
        return ""


def create_progress(
    description: str = "Processing...",
    total: Optional[int] = None,
    transient: bool = False,
) -> Progress:
    """
    Create a progress bar with standard styling.

    Args:
        description: Task description.
        total: Total number of items. If None, creates indeterminate spinner.
        transient: Whether to remove progress after completion.

    Returns:
        Progress instance.
    """
    if total is None or total == 0:
        # Indeterminate progress (spinner)
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=transient,
        )
    else:
        # Determinate progress bar
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=transient,
        )


def with_progress(
    items: Sequence[Any],
    description: str = "Processing",
    callback: Optional[Callable[[Any], None]] = None,
) -> list[Any]:
    """
    Process items with a progress bar.

    Args:
        items: Sequence of items to process.
        description: Progress description.
        callback: Optional callback function for each item.

    Returns:
        List of processed items or results.
    """
    results = []
    total = len(items)

    with create_progress(description, total) as progress:
        task = progress.add_task(description, total=total)

        for item in items:
            if callback:
                result = callback(item)
                results.append(result)
            else:
                results.append(item)
            progress.advance(task)

    return results


def format_pnl(value: float, include_sign: bool = True) -> Text:
    """Format P&L value with color coding."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value > 0 and include_sign else ""
    return Text(f"{sign}{value:,.2f}", style=color)


def format_percent(value: float, include_sign: bool = True) -> Text:
    """Format percentage value with color coding."""
    color = "green" if value >= 0 else "red"
    sign = "+" if value > 0 and include_sign else ""
    return Text(f"{sign}{value:.2%}", style=color)


def confirm_action(message: str, default: bool = False) -> bool:
    """
    Ask user for confirmation.

    Args:
        message: Confirmation message.
        default: Default value if user just presses Enter.

    Returns:
        True if confirmed, False otherwise.
    """
    from rich.prompt import Confirm

    return Confirm.ask(message, default=default)


def prompt_choice(
    message: str,
    choices: list[str],
    default: Optional[str] = None,
) -> str:
    """
    Prompt user to choose from a list.

    Args:
        message: Prompt message.
        choices: List of choices.
        default: Default choice.

    Returns:
        Selected choice.
    """
    from rich.prompt import Prompt

    choices_str = ", ".join(choices)
    return Prompt.ask(
        f"{message} [{choices_str}]",
        choices=choices,
        default=default,
    )


def show_spinner(description: str = "Loading..."):
    """
    Context manager for showing a spinner during operation.

    Usage:
        with show_spinner("Loading data..."):
            # do something
    """
    from contextlib import contextmanager

    @contextmanager
    def _spinner():
        with console.status(description):
            yield

    return _spinner()
