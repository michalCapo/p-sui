"""Go-style data collation helpers for psui (Python port)."""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    List,
    Optional,
    Sequence,
    Mapping,
    TypeVar,
    Union,
    TYPE_CHECKING,
)

import ui

if TYPE_CHECKING:
    from ui_server import Context

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


Loader = Callable[[TQuery], Union[LoadResult[T], Awaitable[LoadResult[T]]]]


class CollateModel(Generic[T]):
    def __init__(self, init: TQuery, loader: Loader[T]) -> None:
        self._default = make_query(init)
        self._loader = loader
        self.target = ui.Target()
        self.target_filter = ui.Target()
        self.search_fields: List[TField] = []
        self.sort_fields: List[TField] = []
        self.filter_fields: List[TField] = []
        self.excel_fields: List[TField] = []
        self.on_row: Optional[Callable[[T, int], str]] = None
        self.on_excel: Optional[Callable[[List[T]], Dict[str, Any]]] = None

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

    def Export(self, fn: Callable[[List[T]], Dict[str, Any]]) -> None:
        self.on_excel = fn

    def Render(self, ctx: "Context") -> str:
        query = make_query(self._default)
        self._trigger_load(ctx, query)
        return self._render_ui(ctx, query, None, True)

    def _on_resize(self, ctx: "Context") -> str:
        query = self._read_query(ctx)
        if query.Limit <= 0:
            query.Limit = self._default.Limit if self._default.Limit > 0 else 10
        query.Limit *= 2
        self._trigger_load(ctx, query)
        return self._render_ui(ctx, query, None, True)

    def _on_sort(self, ctx: "Context") -> str:
        query = self._read_query(ctx)
        self._trigger_load(ctx, query)
        return self._render_ui(ctx, query, None, True)

    def _on_search(self, ctx: "Context") -> str:
        query = self._read_query(ctx)
        if query.Limit <= 0:
            query.Limit = self._default.Limit if self._default.Limit > 0 else 10
        if query.Offset < 0:
            query.Offset = 0
        self._trigger_load(ctx, query)
        return self._render_ui(ctx, query, None, True)

    def _on_reset(self, ctx: "Context") -> str:
        query = make_query(self._default)
        self._trigger_load(ctx, query)
        return self._render_ui(ctx, query, None, True)

    def _on_xls(self, ctx: "Context") -> str:
        ctx.Info("Export not implemented in this build.")
        return ""

    def _read_query(self, ctx: "Context") -> TQuery:
        payload = _query_to_payload(make_query(self._default))
        ctx.Body(payload)
        return make_query(_payload_to_query(payload))

    def _trigger_load(self, ctx: "Context", query: TQuery) -> None:
        if not self._loader:
            return

        query_payload = make_query(query)

        async def load_and_render() -> str:
            await asyncio.sleep(0)  # allow event loop to progress before heavy work
            try:
                result = self._loader(query_payload)
                if inspect.isawaitable(result):
                    result = await result
            except Exception:
                result = LoadResult(total=0, filtered=0, data=[])
            total = result.total if isinstance(result.total, int) else 0
            filtered = result.filtered if isinstance(result.filtered, int) else 0
            data = list(result.data or [])
            output = TCollateResult(
                Total=total,
                Filtered=filtered,
                Data=data,
                Query=query_payload,
            )
            await asyncio.sleep(0.2)
            return self._render_ui(ctx, query_payload, output, False)

        ctx.Patch(self.target.Replace, load_and_render())

    def _render_ui(
        self,
        ctx: "Context",
        query: TQuery,
        result: Optional[TCollateResult[T]],
        loading: bool,
    ) -> str:
        header = ui.div("flex flex-col" + (" pointer-events-none" if loading else ""))(
            ui.div("flex gap-x-2")(
                Sorting(ctx, self.sort_fields, self.target, self._on_sort, query),
                ui.Flex1,
                Searching(
                    ctx,
                    query,
                    self.target,
                    self.target_filter,
                    self.filter_fields,
                    self.excel_fields,
                    self._on_search,
                    self._on_xls,
                ),
            ),
            ui.div("flex justify-end")(
                Filtering(
                    ctx,
                    self.target,
                    self.target_filter,
                    self.filter_fields,
                    self._on_search,
                    query,
                ),
            ),
        )

        if loading or result is None:
            skeleton_rows = ui.Skeleton.List(ui.Target(), 6)
            skeleton_pager = ui.div("flex items-center justify-center")(
                ui.div("mx-4 font-bold text-lg")("\u00A0"),
                ui.div("flex gap-px flex-1 justify-end")(
                    ui.div("bg-gray-200 h-9 w-10 rounded-l border")(),
                    ui.div("bg-gray-200 h-9 w-36 rounded-r border")(),
                ),
            )
            return ui.div("flex flex-col gap-2 mt-2", self.target)(header, skeleton_rows, skeleton_pager)

        rows = render_rows(result.Data, self.on_row)
        pager = Paging(
            ctx,
            result,
            self._default.Limit if self._default.Limit > 0 else 10,
            self._on_reset,
            self._on_resize,
            self.target,
        )
        return ui.div("flex flex-col gap-2 mt-2", self.target)(header, rows, pager)


def Collate(init: TQuery, loader: Loader[T]) -> CollateModel[T]:
    return CollateModel(init, loader)


def make_query(def_query: Optional[TQuery]) -> TQuery:
    d = def_query
    if d is None:
        d = TQuery(Limit=0, Offset=0, Order="", Search="", Filter=[])
    offset = d.Offset if d.Offset >= 0 else 0
    limit = d.Limit if d.Limit > 0 else 10
    return TQuery(
        Limit=limit,
        Offset=offset,
        Order=d.Order or "",
        Search=d.Search or "",
        Filter=list(d.Filter or []),
    )


def Empty(result: TCollateResult[Any]) -> str:
    if result.Total == 0:
        return ui.div(
            "mt-2 py-24 rounded text-xl flex justify-center items-center bg-white rounded-lg",
        )(
            ui.div("")(
                ui.div(
                    "text-black text-2xl p-4 mb-2 font-bold flex justify-center items-center",
                )("No records found"),
            ),
        )
    if result.Filtered == 0:
        return ui.div(
            "mt-2 py-24 rounded text-xl flex justify-center items-center bg-white rounded-lg",
        )(
            ui.div("flex gap-x-px items-center justify-center text-2xl")(
                ui.Icon("fa fa-fw fa-exclamation-triangle text-yellow-500"),
                ui.div(
                    "text-black p-4 mb-2 font-bold flex justify-center items-center",
                )("No records found for the selected filter"),
            ),
        )
    return ""


def Filtering(
    ctx: "Context",
    target: ui.Target,
    target_filter: ui.Target,
    filter_fields: Sequence[TField],
    on_search: Callable[["Context"], str],
    query: TQuery,
) -> str:
    if not filter_fields:
        return ""
    data = _query_to_payload(query)
    return ui.div("col-span-2 relative h-0 hidden z-30", target_filter)(
        ui.div("absolute top-2 right-0 w-96 bg-white rounded-xl shadow-xl ring-1 ring-black/10 border border-gray-200")(
            ui.form("flex flex-col p-4", ctx.Submit(on_search).Replace(target))(
                ui.Hidden("Search", "string", query.Search),
                ui.Hidden("Order", "string", query.Order),
                ui.Hidden("Limit", "number", query.Limit),
                ui.Hidden("Offset", "number", 0),
                ui.div("flex items-center justify-between mb-3")(
                    ui.div("font-semibold text-gray-800")("Filters"),
                    ui.Button()
                    .Click(
                        f"window.document.getElementById('{target_filter.id}')?.classList.add('hidden')",
                    )
                    .Class("rounded-full bg-white hover:bg-gray-100 h-8 w-8 border border-gray-300 flex items-center justify-center")
                    .Color(ui.White)
                    .Render(ui.Icon("fa fa-fw fa-times")),
                ),
                ui.div("grid grid-cols-2 gap-3")(
                    ui.Map2(list(filter_fields), lambda item, index, _first, _last: _render_filter_field(item, index, data)),
                ),
                ui.div("flex justify-end gap-2 mt-6 pt-3 border-t border-gray-200")(
                    ui.Button()
                    .Submit()
                    .Class("rounded-full h-10 px-4 bg-white")
                    .Color(ui.GrayOutline)
                    .Click(
                        "(function(e){try{var el=e.target;var form=null;"
                        "if(el&&el.closest){form=el.closest('form');}"
                        "if(!form){var p=el;while(p&&p.tagName&&p.tagName.toLowerCase()!=='form'){p=p.parentElement;}"
                        "form=p;}"
                        "if(form){var nodes=form.querySelectorAll('[name^=\\'Filter.\\']');"
                        "for(var i=0;i<nodes.length;i++){var it=nodes[i];var t=String(it.getAttribute('type')||'').toLowerCase();"
                        "if(t==='checkbox'){it.checked=false;}else{try{it.value='';}catch(_){} }}}}"
                        "catch(_){}})(event)",
                    )
                    .Render(ui.IconLeft("fa fa-fw fa-rotate-left", "Reset")),
                    ui.Button()
                    .Submit()
                    .Class("rounded-full h-10 px-4 shadow")
                    .Color(ui.Blue)
                    .Render(ui.IconLeft("fa fa-fw fa-check", "Apply")),
                ),
            ),
        ),
    )


def Searching(
    ctx: "Context",
    query: TQuery,
    target: ui.Target,
    target_filter: ui.Target,
    filter_fields: Sequence[TField],
    excel_fields: Sequence[TField],
    on_search: Callable[["Context"], str],
    on_xls: Callable[["Context"], str],
) -> str:
    data = _query_to_payload(query)
    has_search = bool(str(query.Search or "").strip())

    clear_button = ""
    if has_search:
        clear_button = ui.div("absolute right-3 top-1/2 transform -translate-y-1/2")(
            ui.Button()
            .Class("rounded-full bg-white hover:bg-gray-100 h-8 w-8 border border-gray-300 flex items-center justify-center")
            .Click(
                ctx.Call(
                    on_search,
                    {
                        "Search": "",
                        "Order": query.Order,
                        "Limit": query.Limit,
                        "Offset": 0,
                    },
                ).Replace(target)
            )
            .Render(ui.Icon("fa fa-fw fa-times"))
        )

    search_form = ui.form("flex", ctx.Submit(on_search).Replace(target))(
        ui.div("relative flex-1 w-72")(
            ui.div("absolute left-3 top-1/2 transform -translate-y-1/2")(
                ui.Button()
                .Submit()
                .Class("rounded-full bg-white hover:bg-gray-100 h-8 w-8 border border-gray-300 flex items-center justify-center")
                .Render(ui.Icon("fa fa-fw fa-search")),
            ),
            ui.IText("Search", data)
            .Class("p-1 w-full")
            .ClassInput("cursor-pointer bg-white border-gray-300 hover:border-blue-500 block w-full py-3 pl-12 pr-12")
            .Placeholder("Search")
            .Render(""),
            clear_button,
        ),
    )

    excel_button = ""
    if excel_fields:
        excel_button = (
            ui.Button()
            .Color(ui.Blue)
            .Click(ctx.Call(on_xls).Replace(target))
            .Render(ui.IconLeft("fa fa-download", "XLS"))
        )

    filter_button = ""
    if filter_fields:
        filter_button = (
            ui.Button()
            .Submit()
            .Class("rounded-r-lg shadow bg-white")
            .Color(ui.Blue)
            .Click(
                f"window.document.getElementById('{target_filter.id}')?.classList.toggle('hidden')",
            )
            .Render(ui.IconLeft("fa fa-fw fa-chevron-down", "Filter"))
        )

    return ui.div("flex gap-px bg-blue-800 rounded-lg")(
        search_form,
        excel_button,
        filter_button,
    )


def Sorting(
    ctx: "Context",
    sort_fields: Sequence[TField],
    target: ui.Target,
    on_sort: Callable[["Context"], str],
    query: TQuery,
) -> str:
    if not sort_fields:
        return ""

    def render_field(sort: TField, _index: int, _first: bool, _last: bool) -> str:
        if not sort.DB:
            sort.DB = sort.Field
        direction = ""
        color = ui.GrayOutline
        field = (sort.DB or "").lower()
        order = (query.Order or "").lower()
        if order.startswith(field + " ") or order == field:
            direction = "asc" if "asc" in order else "desc"
            color = ui.Purple
        reverse = "asc" if direction == "desc" else "desc"
        payload = {
            "Order": f"{sort.DB} {reverse}".strip(),
            "Search": query.Search,
            "Limit": query.Limit if query.Limit > 0 else 10,
            "Offset": 0,
        }
        return (
            ui.Button()
            .Class("bg-white rounded")
            .Color(color)
            .Click(ctx.Call(on_sort, payload).Replace(target))
            .Render(
                ui.div("flex gap-2 items-center")(
                    ui.Iff(direction == "asc")(ui.Icon("fa fa-fw fa-sort-amount-asc")),
                    ui.Iff(direction == "desc")(ui.Icon("fa fa-fw fa-sort-amount-desc")),
                    ui.Iff(direction == "")(ui.Icon("fa fa-fw fa-sort")),
                    sort.Text,
                ),
            )
        )

    return ui.div("flex gap-1")(ui.Map(list(sort_fields), render_field))


def Paging(
    ctx: "Context",
    result: TCollateResult[T],
    init_limit: int,
    on_reset: Callable[["Context"], str],
    on_resize: Callable[["Context"], str],
    target: ui.Target,
) -> str:
    if result.Filtered == 0:
        return Empty(result)
    size = len(result.Data) if result.Data else 0
    count = f"Showing {size} / {result.Filtered} of {result.Total} in total"
    if result.Filtered == result.Total:
        count = f"Showing {size} / {result.Total}"
    return ui.div("flex items-center justify-center")(
        ui.div("mx-4 font-bold text-lg")(count),
        ui.div("flex gap-px flex-1 justify-end")(
            ui.Button()
            .Class("bg-white rounded-l")
            .Color(ui.PurpleOutline)
            .Disabled(size == 0 or size <= int(init_limit))
            .Click(ctx.Call(on_reset, _query_to_payload(result.Query)).Replace(target))
            .Render(ui.Icon("fa fa-fw fa-undo")),
            ui.Button()
            .Class("rounded-r")
            .Color(ui.Purple)
            .Disabled(size >= int(result.Filtered))
            .Click(ctx.Call(on_resize, _query_to_payload(result.Query)).Replace(target))
            .Render(
                ui.div("flex gap-2 items-center")(
                    ui.Icon("fa fa-arrow-down"),
                    "Load more items",
                ),
            ),
        ),
    )


def render_rows(data: Sequence[T], on_row: Optional[Callable[[T, int], str]]) -> str:
    if not data:
        return ""
    if on_row is None:
        return ui.div("")("Missing row renderer")
    return ui.Map(list(data), lambda item, idx, _first, _last: on_row(item, idx))


def _query_to_payload(query: TQuery) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "Search": query.Search,
        "Order": query.Order,
        "Limit": query.Limit,
        "Offset": query.Offset,
        "Filter": [],
    }
    filters: List[Dict[str, Any]] = []
    for item in query.Filter or []:
        filters.append(
            {
                "DB": item.DB,
                "Field": item.Field,
                "Text": item.Text,
                "Value": item.Value,
                "As": item.As,
                "Condition": item.Condition,
                "Options": list(item.Options or []),
                "Bool": item.Bool,
                "Dates": {
                    "From": item.Dates.From if item.Dates else None,
                    "To": item.Dates.To if item.Dates else None,
                },
            }
        )
    payload["Filter"] = filters
    return payload


def _payload_to_query(data: Mapping[str, Any]) -> TQuery:
    def _as_int(value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _as_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            return normalized in {"1", "true", "yes", "on"}
        return False

    limit = _as_int(data.get("Limit"), 10)
    offset = _as_int(data.get("Offset"), 0)
    order = str(data.get("Order") or "")
    search = str(data.get("Search") or "")

    filters_out: List[TField] = []
    raw_filters: Any = data.get("Filter") or []

    def _iter_filters(value: Any) -> List[Mapping[str, Any]]:
        items: List[Mapping[str, Any]] = []
        if isinstance(value, Mapping):
            for key in sorted(value.keys(), key=lambda k: str(k)):
                item = value.get(key)
                if isinstance(item, Mapping):
                    items.append(item)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, Mapping):
                    items.append(item)
        return items

    for raw in _iter_filters(raw_filters):
        field_name = str(raw.get("Field") or raw.get("DB") or "")
        if not field_name:
            continue
        try:
            as_value = int(raw.get("As", 0) or 0)
        except (TypeError, ValueError):
            as_value = 0
        bool_value = _as_bool(raw.get("Bool", False))
        value_raw = raw.get("Value", "")
        value_str = "" if value_raw is None else str(value_raw)
        dates_raw = raw.get("Dates", {})
        if isinstance(dates_raw, Mapping):
            from_raw = dates_raw.get("From")
            to_raw = dates_raw.get("To")
        else:
            from_raw = to_raw = None
        date_from = str(from_raw) if from_raw not in (None, "") else None
        date_to = str(to_raw) if to_raw not in (None, "") else None
        options: List[Dict[str, str]] = []
        options_raw = raw.get("Options") or []
        if isinstance(options_raw, Sequence) and not isinstance(options_raw, (str, bytes, bytearray)):
            for opt in options_raw:
                if isinstance(opt, Mapping):
                    options.append(
                        {
                            "id": str(opt.get("id", "")),
                            "value": str(opt.get("value", "")),
                        }
                    )
        filters_out.append(
            TField(
                DB=str(raw.get("DB") or field_name),
                Field=field_name,
                Text=str(raw.get("Text") or ""),
                Value=value_str,
                As=as_value,
                Condition=str(raw.get("Condition") or ""),
                Options=options,
                Bool=bool_value,
                Dates=TFieldDates(From=date_from, To=date_to),
            )
        )

    return TQuery(
        Limit=limit if limit > 0 else 10,
        Offset=offset if offset >= 0 else 0,
        Order=order,
        Search=search,
        Filter=filters_out,
    )


def _render_filter_field(field: TField, index: int, data: Mapping[str, Any]) -> Sequence[str]:
    if not field.DB:
        field.DB = field.Field
    position = f"Filter.{index}"

    def hidden() -> List[str]:
        return [
            ui.Hidden(f"{position}.Field", "string", field.DB),
            ui.Hidden(f"{position}.As", "number", field.As),
        ]

    blocks: List[str] = []
    if field.As == ZERO_DATE:
        blocks.append(
            ui.div("col-span-2")(
                *hidden(),
                ui.ICheckbox(f"{position}.Bool", data).Render(field.Text),
            )
        )
    if field.As == NOT_ZERO_DATE:
        blocks.append(
            ui.div("col-span-2")(
                *hidden(),
                ui.ICheckbox(f"{position}.Bool", data).Render(field.Text),
            )
        )
    if field.As == DATES:
        blocks.append(
            ui.div("col-span-2 grid grid-cols-2 gap-3")(
                *hidden(),
                ui.IDate(f"{position}.Dates.From", data).Render("From"),
                ui.IDate(f"{position}.Dates.To", data).Render("To"),
            )
        )
    if field.As == SELECT:
        blocks.append(
            ui.div("col-span-2")(
                *hidden(),
                ui.ISelect(f"{position}.Value", data)
                .Options(field.Options)
                .Render(field.Text),
            )
        )
    if field.As == BOOL:
        blocks.append(
            ui.div("col-span-2")(
                *hidden(),
                ui.Hidden(f"{position}.Condition", "string", field.Condition),
                ui.ICheckbox(f"{position}.Bool", data).Render(field.Text),
            )
        )
    return blocks


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
