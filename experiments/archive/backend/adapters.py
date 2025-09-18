from __future__ import annotations

"""
Adapters between backend.models.RowData and core.schemas.LineItem.

Usage:
  from backend.adapters import row_to_lineitem, lineitem_to_row
"""

from typing import List, Literal

from core.schemas import LineItem, Timing


TextSource = Literal["original", "narr", "follow"]


def _make_id(line_no: int) -> str:
    return f"L{int(line_no):04d}"


def row_to_lineitem(row: "RowData", text_source: TextSource = "original") -> LineItem:
    """Convert RowData to LineItem.

    text_source controls which field becomes LineItem.text (default: original).
    """
    # Lazy import to avoid hard dependency initialisation order
    from .models import RowData  # noqa: F401

    txt = (row.original or "")
    if text_source == "narr":
        txt = (row.narr or row.original or "")
    elif text_source == "follow":
        txt = (row.follow or row.original or "")

    timing = Timing(tStart=row.tStart or 0.0, tEnd=row.tEnd or 0.0, tDur=row.tDur or 0.0)

    return LineItem(
        id=_make_id(row.line),
        index=row.line,
        role=row.role or "NA",
        character=row.character or "-",
        text=txt,
        tags=[],
        locked=bool(row.locked),
        timing=timing,
        status=dict(row.status or {}),
        notes=row.notes or "",
    )


def lineitem_to_row(item: LineItem) -> "RowData":
    """Convert LineItem to RowData (minimal mapping)."""
    from .models import RowData

    return RowData(
        sel=True,
        line=int(item.index),
        role=item.role or "NA",
        character=item.character or "-",
        original=item.text or "",
        follow="",
        narr="",
        storyText="",
        storyKeywords="",
        annot="",
        bgm="",
        se="",
        rate=1.0,
        locked=bool(item.locked),
        notes=item.notes or "",
        status=dict(item.status or {}),
        tDur=float(item.timing.tDur or 0.0),
        tStart=float(item.timing.tStart or 0.0),
        tEnd=float(item.timing.tEnd or 0.0),
    )


def rows_to_lineitems(rows: List["RowData"], text_source: TextSource = "original") -> List[LineItem]:
    return [row_to_lineitem(r, text_source=text_source) for r in rows]


def lineitems_to_rows(items: List[LineItem]) -> List["RowData"]:
    return [lineitem_to_row(it) for it in items]

