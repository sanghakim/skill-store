#!/usr/bin/env python3
"""Format CSV data into markdown tables."""

import csv
import io
import sys


def csv_to_markdown(csv_text: str, max_rows: int = 50) -> str:
    """Convert CSV text to a markdown table."""
    reader = csv.reader(io.StringIO(csv_text))
    rows = list(reader)

    if not rows:
        return "*No data*"

    headers = rows[0]
    data = rows[1 : max_rows + 1]

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in data:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], len(cell))

    # Build markdown table
    lines = []

    # Header
    header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
    lines.append(header_line)

    # Separator
    sep_line = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    lines.append(sep_line)

    # Data rows
    for row in data:
        padded = []
        for i, cell in enumerate(row):
            w = widths[i] if i < len(widths) else len(cell)
            padded.append(cell.ljust(w))
        lines.append("| " + " | ".join(padded) + " |")

    if len(rows) - 1 > max_rows:
        lines.append(f"\n*... and {len(rows) - 1 - max_rows} more rows*")

    return "\n".join(lines)


if __name__ == "__main__":
    csv_input = sys.stdin.read()
    print(csv_to_markdown(csv_input))
