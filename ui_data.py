"""Simplified data utilities for psui (Python server-side UI helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Generic, List, Optional, Sequence, TypeVar

import ui

T = TypeVar("T")


def NormalizeForSearch(value: str) -> str:
    mapping = {
        "á": "a",
        "ä": "a",
        "à": "a",
        "â": "a",
        "ã": "a",
        "å": "a",
        "æ": "ae",
        "č": "c",
        "ć": "c",
        "ç": "c",
        "ď": "d",
        "đ": "d",
        "é": "e",
        "ë": "e",
        "è": "e",
        "ê": "e",
        "ě": "e",
        "í": "i",
        "ï": "i",
        "ì": "i",
        "î": "i",
        "ľ": "l",
        "ĺ": "l",
        "ł": "l",
        "ň": "n",
        "ń": "n",
        "ñ": "n",
        "ó": "o",
        "ö": "o",
        "ò": "o",
        "ô": "o",
        "õ": "o",
        "ø": "o",
        "œ": "oe",
        "ř": "r",
        "ŕ": "r",
        "š": "s",
        "ś": "s",
        "ş": "s",
        "ș": "s",
        "ť": "t",
        "ț": "t",
        "ú": "u",
        "ü": "u",
        "ù": "u",
        "û": "u",
        "ů": "u",
        "ý": "y",
        "ÿ": "y",
        "ž": "z",
        "ź": "z",
        "ż": "z",
    }
    normalized = (value or "").lower()
    for key, repl in mapping.items():
        normalized = normalized.replace(key, repl)
    return normalized


BOOL = 0
NOT_ZERO_DATE = 1
ZERO_DATE = 2
DATES = 3
SELECT = 4


@dataclass
class TFieldDates:
    From: Optional[str] = None
    To: Optional[str] = None


@dataclass
class TField:
    DB: str
    Field: str
    Text: str
    Value: str
    As: int
    Condition: str
    Options: List[Dict[str, str]]
    Bool: bool
    Dates: TFieldDates


@dataclass
class TQuery:
    Limit: int
    Offset: int
    Order: str
    Search: str
    Filter: List[TField]


@dataclass
class LoadResult(Generic[T]):
    total: int
    filtered: int
    data: List[T]


Loader = Callable[[TQuery], LoadResult[T]]


class CollateModel(Generic[T]):
    def __init__(self, init: TQuery, loader: Loader[T]) -> None:
        self._init = init
        self._loader = loader
        self._target = ui.Target()
        self._on_row: Optional[Callable[[T, int], str]] = None
        self._sort_fields: List[TField] = []
        self._filter_fields: List[TField] = []

    def setSort(self, fields: Sequence[TField]) -> None:
        self._sort_fields = list(fields)

    def setFilter(self, fields: Sequence[TField]) -> None:
        self._filter_fields = list(fields)

    def setSearch(self, fields: Sequence[TField]) -> None:
        # Present for API compatibility; search fields are not used in the simplified implementation.
        pass

    def setExcel(self, fields: Sequence[TField]) -> None:
        # API placeholder.
        pass

    def Row(self, fn: Callable[[T, int], str]) -> None:
        self._on_row = fn

    def Render(self, ctx) -> str:  # noqa: ANN001 - Context from ui_server
        query = self._init
        result = self._loader(query)
        rows = []
        if self._on_row:
            for index, item in enumerate(result.data):
                rows.append(self._on_row(item, index))
        body = ui.div("flex flex-col gap-2", self._target)("".join(rows) or ui.div("text-gray-500")("No data"))
        summary = ui.div("flex items-center justify-between text-sm text-gray-600")(
            ui.span("")(f"Total: {result.total}"),
            ui.span("")(f"Filtered: {result.filtered}"),
            ui.span("")(f"Showing {len(result.data)} rows"),
        )
        header = ui.div("flex flex-wrap gap-2 items-center")(
            ui.span("font-semibold")("Simplified Collate"),
            ui.span("text-gray-400 text-sm")(
                "Interactive sorting, filters, and paging are not yet implemented in the Python port.",
            ),
        )
        return ui.div("flex flex-col gap-3")(
            header,
            summary,
            body,
        )


def Collate(init: TQuery, loader: Loader[T]) -> CollateModel[T]:
    return CollateModel(init, loader)


__all__ = [
    "NormalizeForSearch",
    "BOOL",
    "NOT_ZERO_DATE",
    "ZERO_DATE",
    "DATES",
    "SELECT",
    "TField",
    "TFieldDates",
    "TQuery",
    "LoadResult",
    "Collate",
]
