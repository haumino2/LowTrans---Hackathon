"""Infer chart type and summary from analyst query results."""

from __future__ import annotations

from typing import Any


def _is_numeric(val: Any) -> bool:
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return True
    if isinstance(val, str):
        try:
            float(val.replace(",", ""))
            return True
        except ValueError:
            return False
    return False


def _to_number(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    return float(str(val).replace(",", ""))


def build_visualization(
    *,
    question: str,
    columns: list[str],
    rows: list[list[Any]],
    explanation: str = "",
) -> dict[str, Any]:
    """Pick bar chart vs table and build a short analyst summary."""
    row_count = len(rows)
    chart_type = "table"
    label_col: str | None = None
    value_col: str | None = None

    if row_count and len(columns) >= 2:
        numeric_idxs = [
            i for i, col in enumerate(columns) if _is_numeric(rows[0][i])
        ]
        text_idxs = [i for i in range(len(columns)) if i not in numeric_idxs]
        if numeric_idxs and text_idxs:
            label_col = columns[text_idxs[0]]
            value_col = columns[numeric_idxs[0]]
            if row_count <= 12:
                chart_type = "bar"

    summary = explanation or f"Analysis returned {row_count} row(s)."
    if chart_type == "bar" and label_col and value_col:
        top = sorted(
            rows,
            key=lambda r: _to_number(r[columns.index(value_col)]),
            reverse=True,
        )[:3]
        parts = [
            f"{r[columns.index(label_col)]}: {_to_number(r[columns.index(value_col)]):,.0f}"
            for r in top
        ]
        summary = f"Top results — {', '.join(parts)}."

    return {
        "chart_type": chart_type,
        "columns": columns,
        "rows": rows,
        "label_column": label_col,
        "value_column": value_col,
        "row_count": row_count,
        "summary": summary,
        "question": question,
    }
