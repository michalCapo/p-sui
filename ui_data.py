"""Simplified data utilities for psui (Python server-side UI helpers)."""

from __future__ import annotations

from dataclasses import dataclass, field
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
    DB: str = ""
    Field: str = ""
    Text: str = ""
    Value: str = ""
    As: int = 0
    Condition: str = ""
    Options: List[Dict[str, str]] = field(default_factory=list)
    Bool: bool = False
    Dates: TFieldDates = field(default_factory=TFieldDates)


BOOL_ZERO_OPTIONS = [
    {"id": "", "value": "All"},
    {"id": "yes", "value": "On"},
    {"id": "no", "value": "Off"},
]


@dataclass
class TQuery:
    Limit: int = 10
    Offset: int = 0
    Order: str = ""
    Search: str = ""
    Filter: List[TField] = field(default_factory=list)


@dataclass
class LoadResult(Generic[T]):
    total: int
    filtered: int
    data: List[T]


@dataclass
class TCollateResult(Generic[T]):
    Total: int
    Filtered: int
    Data: List[T]
    Query: TQuery


Loader = Callable[[TQuery], LoadResult[T]]


class CollateModel(Generic[T]):
    def __init__(self, init: TQuery, loader: Loader[T]) -> None:
        self._init = init
        self._loader = loader
        self.target = ui.Target()
        self.target_filter = ui.Target()
        self.on_row: Optional[Callable[[T, int], str]] = None
        self.sort_fields: List[TField] = []
        self.filter_fields: List[TField] = []
        self.search_fields: List[TField] = []
        self.excel_fields: List[TField] = []
        self.on_excel: Optional[Callable[[List[T]], Dict]] = None

    def setSort(self, fields: Sequence[TField]) -> None:
        self.sort_fields = list(fields)

    def setFilter(self, fields: Sequence[TField]) -> None:
        self.filter_fields = list(fields)

    def setSearch(self, fields: Sequence[TField]) -> None:
        self.search_fields = list(fields)

    def setExcel(self, fields: Sequence[TField]) -> None:
        self.excel_fields = list(fields)

    def Row(self, fn: Callable[[T, int], str]) -> None:
        self.on_row = fn

    def Export(self, fn: Callable[[List[T]], Dict]) -> None:
        self.on_excel = fn

    def Render(self, ctx) -> str:  # noqa: ANN001 - Context from ui_server
        query = self._make_query(self._init)
        result = self._loader(query) if self._loader else LoadResult(total=0, filtered=0, data=[])
        collate_result = TCollateResult(
            Total=result.total if isinstance(result.total, int) else 0,
            Filtered=result.filtered if isinstance(result.filtered, int) else 0,
            Data=result.data if result.data else [],
            Query=query,
        )
        return self._render_ui(ctx, query, collate_result, False)

    def _make_query(self, def_query: Optional[TQuery]) -> TQuery:
        """Create a normalized query from a default."""
        d = def_query
        if d is None:
            d = TQuery(Limit=0, Offset=0, Order="", Search="", Filter=[])
        if d.Offset < 0:
            d.Offset = 0
        if d.Limit <= 0:
            d.Limit = 10
        return TQuery(
            Limit=d.Limit,
            Offset=d.Offset,
            Order=d.Order or "",
            Search=d.Search or "",
            Filter=d.Filter or [],
        )

    def _render_ui(self, ctx, query: TQuery, result: TCollateResult[T], loading: bool) -> str:
        """Render the main UI - simplified version without interactive callbacks."""
        header = ui.div("flex flex-col")(
            ui.div("flex gap-x-2")(
                ui.div("flex gap-1")(),  # Sorting placeholder
                ui.Flex1,
                ui.div("flex gap-px bg-blue-800 rounded-lg")(),  # Search placeholder
            ),
        )

        rows = self._render_rows(result.Data, self.on_row)
        
        size = len(result.Data) if result.Data else 0
        if result.Filtered == result.Total:
            count = f"Showing {size} / {result.Total}"
        else:
            count = f"Showing {size} / {result.Filtered} of {result.Total} in total"

        pager = ui.div("flex items-center justify-center")(
            ui.div("mx-4 font-bold text-lg")(count),
        )

        return ui.div("flex flex-col gap-2 mt-2", self.target)(header, rows, pager)

    def _render_rows(self, data: List[T], on_row: Optional[Callable[[T, int], str]]) -> str:
        """Render data rows."""
        if not data:
            return ""
        if not on_row:
            return ui.div("")("Missing row renderer")
        return "".join([on_row(item, i) for i, item in enumerate(data)])


def Collate(init: TQuery, loader: Loader[T]) -> CollateModel[T]:
    return CollateModel(init, loader)


__all__ = [
    "NormalizeForSearch",
    "BOOL",
    "NOT_ZERO_DATE",
    "ZERO_DATE",
    "DATES",
    "SELECT",
    "BOOL_ZERO_OPTIONS",
    "TField",
    "TFieldDates",
    "TQuery",
    "LoadResult",
    "TCollateResult",
    "Collate",
    "CollateModel",
]
