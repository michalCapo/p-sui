"""Server-side HTML utilities for psui.

This module mirrors the public API of the original implementation so the
example applications can be reused from Python. The implementation purposely
avoids third-party dependencies and relies solely on the standard library.
"""

from __future__ import annotations

import json
import re
import secrets
import string
import threading
import time
import html
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple, Union

Swap = str
Attr = Dict[str, Any]
AOption = Dict[str, str]


_RE_INLINE_GAP = re.compile(r"\s{4,}")
_RE_GAP = re.compile(r"[\t\n]+")
_RE_QUOTE = re.compile(r'"')
_RE_COMMENT_HTML = re.compile(r"<!--[\s\S]*?-->")
_RE_COMMENT_BLOCK = re.compile(r"/\*[\s\S]*?\*/")
_RE_COMMENT_LINE = re.compile(r"^[\t ]*//.*$", re.MULTILINE)


def Trim(value: str) -> str:
    """Mimic the TypeScript helper that normalises whitespace."""

    if not value:
        return ""
    result = str(value)
    result = _RE_COMMENT_HTML.sub(" ", result)
    result = _RE_COMMENT_BLOCK.sub(" ", result)
    result = _RE_COMMENT_LINE.sub(" ", result)
    result = _RE_GAP.sub(" ", result)
    result = _RE_INLINE_GAP.sub(" ", result)
    return result.strip()


def Normalize(value: str) -> str:
    if not value:
        return ""
    result = str(value)
    result = _RE_COMMENT_HTML.sub(" ", result)
    result = _RE_COMMENT_BLOCK.sub(" ", result)
    result = _RE_COMMENT_LINE.sub(" ", result)
    result = _RE_QUOTE.sub("&quot;", result)
    result = _RE_GAP.sub("", result)
    result = _RE_INLINE_GAP.sub(" ", result)
    return result.strip()


def Classes(*values: Union[str, None, bool]) -> str:
    parts = [str(v) for v in values if v]
    return Trim(" ".join(parts))


def _is_mapping(value: Any) -> bool:
    return isinstance(value, MutableMapping)


def getPath(data: Any, path: str) -> Any:
    if data is None:
        return None
    keys = str(path or "").split(".")
    current: Any = data
    for key in keys:
        if current is None:
            return None
        if isinstance(current, Mapping):
            current = current.get(key)
            continue
        if isinstance(current, Sequence) and not isinstance(current, (str, bytes, bytearray)):
            try:
                index = int(key)
            except ValueError:
                return None
            if index < 0 or index >= len(current):
                return None
            current = current[index]
            continue
        return None
    return current


def setPath(data: MutableMapping[str, Any], path: str, value: Any) -> None:
    keys = str(path or "").split(".")
    current: MutableMapping[str, Any] = data
    for idx, key in enumerate(keys):
        if idx == len(keys) - 1:
            current[key] = value
            return
        next_value = current.get(key)
        if not isinstance(next_value, MutableMapping):
            next_value = {}
            current[key] = next_value
        current = next_value  # type: ignore[assignment]


def If(condition: bool, value: Callable[[], str]) -> str:
    return value() if condition else ""


def Iff(condition: bool) -> Callable[..., str]:
    def inner(*values: str) -> str:
        return " ".join(values) if condition else ""

    return inner


def Map(values: Sequence[Any], iterator: Callable[[Any, int, bool, bool], str]) -> str:
    rendered: List[str] = []
    total = len(values)
    for idx, item in enumerate(values):
        rendered.append(iterator(item, idx, idx == 0, idx == total - 1))
    return " ".join(rendered)


def Map2(values: Sequence[Any], iterator: Callable[[Any, int, bool, bool], Sequence[str]]) -> str:
    rendered: List[str] = []
    total = len(values)
    for idx, item in enumerate(values):
        rendered.append(" ".join(iterator(item, idx, idx == 0, idx == total - 1)))
    return " ".join(rendered)


def For(start: int, stop: int, iterator: Callable[[int, bool, bool], str]) -> str:
    rendered: List[str] = []
    for idx in range(start, stop):
        rendered.append(iterator(idx, idx == start, idx == stop - 1))
    return " ".join(rendered)


def RandomString(length: int = 20) -> str:
    if length <= 0:
        return ""
    # Use secrets for cryptographic quality similar to crypto.randomBytes
    raw = secrets.token_urlsafe(length)
    safe = re.sub(r"[^A-Za-z0-9]", "", raw)
    if len(safe) >= length:
        return safe[:length]
    # In rare cases pad with random choices
    choices = string.ascii_letters + string.digits
    while len(safe) < length:
        safe += secrets.choice(choices)
    return safe[:length]


def makeId() -> str:
    return "i" + RandomString(15)


XS = " p-1"
SM = " p-2"
MD = " p-3"
ST = " p-4"
LG = " p-5"
XL = " p-6"

AREA = " cursor-pointer bg-white border border-gray-300 hover:border-blue-500 rounded-lg block w-full"
INPUT = " cursor-pointer bg-white border border-gray-300 hover:border-blue-500 rounded-lg block w-full h-12"
VALUE = " bg-white border border-gray-300 hover:border-blue-500 rounded-lg block h-12"
BTN = " cursor-pointer font-bold text-center select-none"
DISABLED = " cursor-text pointer-events-none bg-gray-50"
Yellow = " bg-yellow-400 text-gray-800 hover:text-gray-200 hover:bg-yellow-600 font-bold border-gray-300 flex items-center justify-center"
YellowOutline = " border border-yellow-500 text-yellow-600 hover:text-gray-700 hover:bg-yellow-500 flex items-center justify-center"
Green = " bg-green-600 text-white hover:bg-green-700 checked:bg-green-600 border-gray-300 flex items-center justify-center"
GreenOutline = " border border-green-500 text-green-500 hover:text-white hover:bg-green-600 flex items-center justify-center"
Purple = " bg-purple-500 text-white hover:bg-purple-700 border-purple-500 flex items-center justify-center"
PurpleOutline = " border border-purple-500 text-purple-500 hover:text-white hover:bg-purple-600 flex items-center justify-center"
Blue = " bg-blue-800 text-white hover:bg-blue-700 border-gray-300 flex items-center justify-center"
BlueOutline = " border border-blue-500 text-blue-600 hover:text-white hover:bg-blue-700 checked:bg-blue-700 flex items-center justify-center"
Red = " bg-red-600 text-white hover:bg-red-800 border-gray-300 flex items-center justify-center"
RedOutline = " border border-red-500 text-red-600 hover:text-white hover:bg-red-700 flex items-center justify-center"
Gray = " bg-gray-600 text-white hover:bg-gray-800 focus:bg-gray-800 border-gray-300 flex items-center justify-center"
GrayOutline = " border border-gray-300 text-black hover:text-white hover:bg-gray-700 flex items-center justify-center"
White = " bg-white text-black hover:bg-gray-200 border-gray-200 flex items-center justify-center"
WhiteOutline = " border border-white text-balck hover:text-black hover:bg-white flex items-center justify-center"

space = "&nbsp;"


def attributes(*items: Optional[Attr]) -> str:
    result: List[str] = []
    for item in items:
        if not item:
            continue
        if not isinstance(item, MutableMapping) and hasattr(item, "id"):
            item = {"id": getattr(item, "id")}
        for key, value in item.items():
            if value is None or value is False:
                continue
            if key in {"disabled", "required", "readonly"}:
                if value:
                    result.append(f"{key}=\"{key}\"")
                continue
            # Don't double-escape onclick attributes as they're already escaped by Normalize()
            if key == "onclick":
                result.append(f"{key}=\"{str(value)}\"")
            else:
                result.append(f"{key}=\"{html.escape(str(value), quote=True)}\"")
    return " ".join(result)


def open_tag(tag: str) -> Callable[[str, *Attr], Callable[..., str]]:
    def with_css(css: str = "", *extra: Attr) -> Callable[..., str]:
        def renderer(*elements: Any) -> str:
            content = " ".join(str(el) for el in elements if el)
            attr_str = attributes(*extra, {"class": Classes(css)})
            if attr_str:
                return f"<{tag} {attr_str}>{content}</{tag}>"
            return f"<{tag}>{content}</{tag}>"

        return renderer

    return with_css


def closed_tag(tag: str) -> Callable[[str, *Attr], str]:
    def renderer(css: str = "", *extra: Attr) -> str:
        attr_str = attributes(*extra, {"class": Classes(css)})
        if attr_str:
            return f"<{tag} {attr_str}/>"
        return f"<{tag}/>"

    return renderer


a = open_tag("a")
i = open_tag("i")
p = open_tag("p")
div = open_tag("div")
span = open_tag("span")
form = open_tag("form")
textarea = open_tag("textarea")
select = open_tag("select")
option = open_tag("option")
ul = open_tag("ul")
li = open_tag("li")
label = open_tag("label")
canvas = open_tag("canvas")
button = open_tag("button")

img = closed_tag("img")
input = closed_tag("input")

Flex1 = div("flex-1")()


def Icon(css: str, *attrs: Attr) -> str:
    return div(css, *attrs)()


def IconStart(css: str, text: str) -> str:
    return div("flex-1 flex items-center gap-2")(
        Icon(css),
        Flex1,
        div("text-center")(text),
        Flex1,
    )


def IconLeft(css: str, text: str) -> str:
    return div("flex-1 flex items-center gap-2")(
        Flex1,
        Icon(css),
        div("text-center")(text),
        Flex1,
    )


def IconRight(css: str, text: str) -> str:
    return div("flex-1 flex items-center gap-2")(
        Flex1,
        div("text-center")(text),
        Icon(css),
        Flex1,
    )


def IconEnd(css: str, text: str) -> str:
    return div("flex-1 flex items-center gap-2")(
        Flex1,
        div("text-center")(text),
        Flex1,
        Icon(css),
    )


def Label(css: str, *attrs: Attr) -> Callable[[str], str]:
    required = False
    for attr in attrs:
        if isinstance(attr, Mapping):
            if attr.get("required"):
                required = True
                break

    def render(text: str) -> str:
        if required:
            indicator = '<span class="psui-required-indicator text-red-500" aria-hidden="true">*</span>'
            pieces = [part for part in (text, indicator) if part]
            content = " ".join(pieces) if pieces else indicator
            return label(css, *attrs)(content)
        return label(css, *attrs)(text)

    return render


@dataclass
class Target:
    id: str = field(default_factory=makeId)

    def Skeleton(self, skeleton_type: Optional[str] = None) -> str:
        if skeleton_type == "list":
            return Skeleton.List(self, 5)
        if skeleton_type == "component":
            return Skeleton.Component(self)
        if skeleton_type == "page":
            return Skeleton.Page(self)
        if skeleton_type == "form":
            return Skeleton.Form(self)
        return Skeleton.Default(self)

    @property
    def Replace(self) -> Attr:
        return {"id": self.id, "swap": "outline"}

    @property
    def Append(self) -> Attr:
        return {"id": self.id, "swap": "append"}

    @property
    def Prepend(self) -> Attr:
        return {"id": self.id, "swap": "prepend"}

    @property
    def Render(self) -> Attr:
        return {"id": self.id, "swap": "inline"}


class _Button:
    def __init__(self, target: Optional[Target] = None) -> None:
        self._target = target or Target()
        self._attrs: List[Attr] = []
        self._size = MD
        self._color = Blue
        self._css = ""
        self._visible = True
        self._disabled = False
        self._onclick: Optional[str] = None
        self._as = "button"

    def Submit(self) -> "_Button":
        self._as = "button"
        self._attrs.append({"type": "submit"})
        return self

    def Reset(self) -> "_Button":
        self._as = "button"
        self._attrs.append({"type": "reset"})
        return self

    def If(self, visible: bool) -> "_Button":
        self._visible = visible
        return self

    def Disabled(self, disabled: bool) -> "_Button":
        self._disabled = disabled
        return self

    def Class(self, css: str) -> "_Button":
        self._css = css
        return self

    def Color(self, css: str) -> "_Button":
        self._color = css
        return self

    def Size(self, css: str) -> "_Button":
        self._size = css
        return self

    def Click(self, code: str) -> "_Button":
        self._onclick = code
        return self

    def Href(self, href: str) -> "_Button":
        self._as = "a"
        self._attrs.append({"href": href})
        return self

    def Render(self, text: str) -> str:
        if not self._visible:
            return ""
        cls = Classes(
            BTN,
            self._size,
            self._color,
            self._css,
            self._disabled and DISABLED + " opacity-25",
        )
        attrs: List[Attr] = list(self._attrs)
        attrs.append({"id": self._target.id, "class": cls})
        if self._onclick:
            attrs.append({"onclick": self._onclick})
        if self._disabled:
            attrs.append({"disabled": True})
        if self._as == "a":
            return a(cls, *attrs)(text)
        if self._as == "div":
            return div(cls, *attrs)(text)
        return button(cls, *attrs)(text)


class _BaseInput:
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None, as_type: str = "text") -> None:
        self.data = data
        self.rows = 0
        self.placeholder = ""
        self.css = ""
        self.cssLabel = ""
        self.cssInput = ""
        self.autocomplete = ""
        self.size = MD
        self.onclick = ""
        self.onchange = ""
        self.as_type = as_type
        self.name = name
        self.pattern = ""
        self.value = ""
        self.visible = True
        self.required = False
        self.disabled = False
        self.readonly = False
        self._target = Target()

    def Class(self, *css: str) -> "_BaseInput":
        self.css = " ".join(css)
        return self

    def ClassLabel(self, *css: str) -> "_BaseInput":
        self.cssLabel = " ".join(css)
        return self

    def ClassInput(self, *css: str) -> "_BaseInput":
        self.cssInput = " ".join(css)
        return self

    def Size(self, css: str) -> "_BaseInput":
        self.size = css
        return self

    def Placeholder(self, placeholder: str) -> "_BaseInput":
        self.placeholder = placeholder
        return self

    def Pattern(self, pattern: str) -> "_BaseInput":
        self.pattern = pattern
        return self

    def Autocomplete(self, value: str) -> "_BaseInput":
        self.autocomplete = value
        return self

    def Required(self, value: bool = True) -> "_BaseInput":
        self.required = value
        return self

    def Readonly(self, value: bool = True) -> "_BaseInput":
        self.readonly = value
        return self

    def Disabled(self, value: bool = True) -> "_BaseInput":
        self.disabled = value
        return self

    def Type(self, value: str) -> "_BaseInput":
        self.as_type = value
        return self

    def Rows(self, value: int) -> "_BaseInput":
        self.rows = value
        return self

    def Value(self, value: str) -> "_BaseInput":
        self.value = value
        return self

    def Change(self, code: str) -> "_BaseInput":
        self.onchange = code
        return self

    def Click(self, code: str) -> "_BaseInput":
        self.onclick = code
        return self

    def If(self, visible: bool) -> "_BaseInput":
        self.visible = visible
        return self

    def resolveValue(self) -> str:
        if not self.data:
            return self.value
        value = getPath(self.data, self.name)
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, time.struct_time):
            return time.strftime("%Y-%m-%d", value)
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", "ignore")
        if value is None:
            return self.value
        return str(value)

    def Render(self, label_text: str) -> str:
        raise NotImplementedError


class _TextInput(_BaseInput):
    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""

        value = self.resolveValue()
        
        return div(self.css)(
            Label(self.cssLabel, {"for": self._target.id, "required": self.required})(label_text),
            input(
                Classes(INPUT, self.size, self.cssInput, self.disabled and DISABLED),
                self._input_attrs(value),
            ),
        )

    def _input_attrs(self, value: str) -> Attr:
        attrs: Attr = {
            "id": self._target.id,
            "name": self.name,
            "type": self.as_type,
            "onclick": self.onclick,
            "onchange": self.onchange,
            "required": self.required,
            "disabled": self.disabled,
            "readonly": self.readonly,
            "placeholder": self.placeholder,
            "pattern": self.pattern,
            "value": value,
        }
        if self.autocomplete:
            attrs["autocomplete"] = self.autocomplete
        return attrs


class _AreaInput(_BaseInput):
    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""
        value = self.resolveValue()
        rows = self.rows if self.rows > 0 else 5
        return div(self.css)(
            Label(self.cssLabel, {"for": self._target.id, "required": self.required})(label_text),
            textarea(
                Classes(AREA, self.size, self.cssInput, self.disabled and DISABLED),
                {
                    "id": self._target.id,
                    "name": self.name,
                    "rows": rows,
                    "onclick": self.onclick,
                    "required": self.required,
                    "disabled": self.disabled,
                    "readonly": self.readonly,
                    "placeholder": self.placeholder,
                },
            )(value),
        )


class _NumberInput(_BaseInput):
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None) -> None:
        super().__init__(name, data, "number")
        self._min: Optional[float] = None
        self._max: Optional[float] = None
        self._step: Optional[float] = None
        self._format = "%v"

    def Numbers(self, min_value: Optional[float] = None, max_value: Optional[float] = None, step: Optional[float] = None) -> "_NumberInput":
        self._min = min_value
        self._max = max_value
        self._step = step
        return self

    def Format(self, fmt: str) -> "_NumberInput":
        self._format = fmt
        return self

    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""
        value = self.resolveValue()
        if self._format and value:
            try:
                numeric = float(value)
            except ValueError:
                pass
            else:
                if "%.2f" in self._format:
                    value = f"{numeric:.2f}"
        attrs: Attr = {
            "id": self._target.id,
            "name": self.name,
            "type": self.as_type,
            "onclick": self.onclick,
            "required": self.required,
            "disabled": self.disabled,
            "value": value,
            "placeholder": self.placeholder,
        }
        if self._min is not None:
            attrs["min"] = self._min
        if self._max is not None:
            attrs["max"] = self._max
        if self._step is not None:
            attrs["step"] = self._step
        return div(self.css)(
            Label(self.cssLabel, {"for": self._target.id, "required": self.required})(label_text),
            input(
                Classes(INPUT, self.size, self.cssInput, self.disabled and DISABLED),
                attrs,
            ),
        )


class _DateInput(_BaseInput):
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None, as_type: str = "date") -> None:
        super().__init__(name, data, as_type)
        self._min: Optional[time.struct_time] = None
        self._max: Optional[time.struct_time] = None

    def Dates(self, min_value: Optional[time.struct_time] = None, max_value: Optional[time.struct_time] = None) -> "_DateInput":
        self._min = min_value
        self._max = max_value
        return self

    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""
        value = self.resolveValue()
        attrs: Attr = {
            "id": self._target.id,
            "name": self.name,
            "type": self.as_type,
            "onclick": self.onclick,
            "onchange": self.onchange,
            "required": self.required,
            "disabled": self.disabled,
            "value": value,
            "placeholder": self.placeholder,
        }
        if self._min is not None:
            attrs["min"] = time.strftime("%Y-%m-%d", self._min)
        if self._max is not None:
            attrs["max"] = time.strftime("%Y-%m-%d", self._max)
        return div(self.css + " min-w-0")(
            Label(self.cssLabel, {"for": self._target.id, "required": self.required})(label_text),
            input(
                Classes(INPUT, self.size, "min-w-0 max-w-full", self.cssInput, self.disabled and DISABLED),
                attrs,
            ),
        )


class _TimeInput(_DateInput):
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None, as_type: str = "time") -> None:
        super().__init__(name, data, as_type)

    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""
        value = self.resolveValue()
        attrs: Attr = {
            "id": self._target.id,
            "name": self.name,
            "type": self.as_type,
            "onclick": self.onclick,
            "required": self.required,
            "disabled": self.disabled,
            "value": value,
            "placeholder": self.placeholder,
        }
        if self._min is not None:
            attrs["min"] = time.strftime("%H:%M", self._min)
        if self._max is not None:
            attrs["max"] = time.strftime("%H:%M", self._max)
        return div(self.css)(
            Label(self.cssLabel, {"for": self._target.id, "required": self.required})(label_text),
            input(
                Classes(INPUT, self.size, self.cssInput, self.disabled and DISABLED),
                attrs,
            ),
        )


class _SelectInput:
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None) -> None:
        self.data = data
        self.name = name
        self.css = ""
        self.cssLabel = ""
        self.cssInput = ""
        self.size = MD
        self.required = False
        self.disabled = False
        self.placeholder = ""
        self.options: List[AOption] = []
        self.target = Target()
        self.onchange = ""
        self.empty = False
        self.emptyText = ""
        self.visible = True
        self.error = False

    def Class(self, *css: str) -> "_SelectInput":
        self.css = " ".join(css)
        return self

    def ClassLabel(self, *css: str) -> "_SelectInput":
        self.cssLabel = " ".join(css)
        return self

    def ClassInput(self, *css: str) -> "_SelectInput":
        self.cssInput = " ".join(css)
        return self

    def Size(self, css: str) -> "_SelectInput":
        self.size = css
        return self

    def Required(self, value: bool = True) -> "_SelectInput":
        self.required = value
        return self

    def Disabled(self, value: bool = True) -> "_SelectInput":
        self.disabled = value
        return self

    def Options(self, values: Sequence[AOption]) -> "_SelectInput":
        self.options = list(values)
        return self

    def Placeholder(self, value: str) -> "_SelectInput":
        self.placeholder = value
        return self

    def Change(self, code: str) -> "_SelectInput":
        self.onchange = code
        return self

    def Empty(self) -> "_SelectInput":
        self.empty = True
        return self

    def EmptyText(self, text: str) -> "_SelectInput":
        self.emptyText = text
        self.empty = True
        return self

    def If(self, visible: bool) -> "_SelectInput":
        self.visible = visible
        return self

    def Error(self, value: bool = True) -> "_SelectInput":
        self.error = value
        return self

    def Render(self, label_text: str) -> str:
        if not self.visible:
            return ""
        current = ""
        if self.data is not None:
            value = getPath(self.data, self.name)
            if value is not None:
                current = str(value)
        options_html: List[str] = []
        if self.placeholder:
            options_html.append(option("", {"value": ""})(self.placeholder))
        if self.empty:
            options_html.append(option("", {"value": ""})(self.emptyText))
        for opt in self.options:
            attrs: Attr = {"value": opt.get("id", "")}
            if current == opt.get("id"):
                attrs["selected"] = "selected"
            options_html.append(option("", attrs)(opt.get("value", "")))
        css = Classes(INPUT, self.size, self.cssInput, self.disabled and DISABLED)
        select_attrs: Attr = {
            "id": self.target.id,
            "name": self.name,
            "required": self.required,
            "disabled": self.disabled,
            "placeholder": self.placeholder,
            "onchange": self.onchange,
        }
        wrapper = Classes(self.css, self.required and "invalid-if", self.error and "invalid")
        return div(wrapper)(
            Label(self.cssLabel, {"for": self.target.id, "required": self.required})(label_text),
            select(css, select_attrs)(" ".join(options_html)),
        )


class _CheckboxInput:
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None) -> None:
        self.data = data
        self.name = name
        self.css = ""
        self.size = MD
        self.required = False
        self.disabled = False
        self.error = False

    def Class(self, *css: str) -> "_CheckboxInput":
        self.css = " ".join(css)
        return self

    def Size(self, css: str) -> "_CheckboxInput":
        self.size = css
        return self

    def Required(self, value: bool = True) -> "_CheckboxInput":
        self.required = value
        return self

    def Disabled(self, value: bool = True) -> "_CheckboxInput":
        self.disabled = value
        return self

    def Error(self, value: bool = True) -> "_CheckboxInput":
        self.error = value
        return self

    def Render(self, text: str) -> str:
        checked = False
        if self.data is not None:
            checked = bool(getPath(self.data, self.name))
        input_el = input(
            Classes("cursor-pointer select-none"),
            {
                "type": "checkbox",
                "name": self.name,
                "checked": "checked" if checked else None,
                "required": self.required,
                "disabled": self.disabled,
            },
        )
        wrapper = Classes(
            self.css,
            self.size,
            self.disabled and "opacity-50 pointer-events-none",
            self.required and "invalid-if",
            self.error and "invalid",
        )
        return div(wrapper)(label("flex items-center gap-2 cursor-pointer select-none")(input_el + " " + text))


class _RadioInput:
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None) -> None:
        self.data = data
        self.name = name
        self.css = ""
        self.cssLabel = ""
        self.size = MD
        self.valueSet = ""
        self.target = Target()
        self.disabled = False
        self.required = False
        self.error = False

    def Class(self, *css: str) -> "_RadioInput":
        self.css = " ".join(css)
        return self

    def ClassLabel(self, *css: str) -> "_RadioInput":
        self.cssLabel = " ".join(css)
        return self

    def Size(self, css: str) -> "_RadioInput":
        self.size = css
        return self

    def Value(self, value: str) -> "_RadioInput":
        self.valueSet = value
        return self

    def Disabled(self, value: bool = True) -> "_RadioInput":
        self.disabled = value
        return self

    def Required(self, value: bool = True) -> "_RadioInput":
        self.required = value
        return self

    def Error(self, value: bool = True) -> "_RadioInput":
        self.error = value
        return self

    def Render(self, text: str) -> str:
        selected = ""
        if self.data is not None:
            value = self.data.get(self.name)
            if value is not None:
                selected = str(value)
        attrs: Attr = {
            "id": self.target.id,
            "type": "radio",
            "name": self.name,
            "value": self.valueSet,
            "checked": "checked" if selected == self.valueSet else None,
            "disabled": self.disabled,
            "required": self.required,
        }
        input_el = input(Classes("hover:cursor-pointer"), attrs)
        wrapper = Classes(
            self.css,
            self.size,
            self.disabled and "opacity-50 pointer-events-none",
            self.required and "invalid-if",
            self.error and "invalid",
        )
        label_css = Classes("flex items-center gap-2 cursor-pointer select-none", self.cssLabel)
        label_body = f"{input_el} {text}".strip()
        field_label = Label(label_css, {"for": self.target.id, "required": self.required})(label_body)
        return div(wrapper)(field_label)


class _RadioButtons:
    def __init__(self, name: str, data: Optional[Mapping[str, Any]] = None) -> None:
        self.name = name
        self.data = data
        self.css = ""
        self.size = MD
        self.options: List[AOption] = []
        self.disabled = False
        self.required = False
        self.error = False
        self.target = Target()

    def Class(self, *css: str) -> "_RadioButtons":
        self.css = " ".join(css)
        return self

    def Size(self, css: str) -> "_RadioButtons":
        self.size = css
        return self

    def Options(self, values: Sequence[AOption]) -> "_RadioButtons":
        self.options = list(values)
        return self

    def Disabled(self, value: bool = True) -> "_RadioButtons":
        self.disabled = value
        return self

    def Required(self, value: bool = True) -> "_RadioButtons":
        self.required = value
        return self

    def Error(self, value: bool = True) -> "_RadioButtons":
        self.error = value
        return self

    def Render(self, text: str) -> str:
        selected = ""
        if self.data is not None:
            value = self.data.get(self.name)
            if value is not None:
                selected = str(value)
        items = ""
        for opt in self.options:
            value = opt.get("id", "")
            cls = Classes(
                "flex items-center gap-2 px-3 py-2 border rounded cursor-pointer", self.disabled and "opacity-50"
            )
            attrs: Attr = {
                "type": "radio",
                "name": self.name,
                "value": value,
                "checked": "checked" if selected == value else None,
                "disabled": self.disabled,
                "required": self.required,
            }
            input_el = input("", attrs)
            items += label(cls)(input_el + " " + opt.get("value", ""))
        wrapper = Classes(self.css, self.required and "invalid-if", self.error and "invalid")
        legend = Label("font-bold", {"required": self.required})(text)
        return div(wrapper)(
            legend,
            div("flex gap-2 flex-wrap")(items),
        )


class SimpleTable:
    def __init__(self, cols: int, css: str = "") -> None:
        self.cols = cols
        self.css = css
        self.rows: List[List[str]] = []
        self.colClasses: List[str] = [""] * cols
        self.cellAttrs: List[List[str]] = []
        self.sealed: List[bool] = []

    def Class(self, col: int, *classes: str) -> "SimpleTable":
        if 0 <= col < self.cols:
            self.colClasses[col] = Classes(*classes)
        return self

    def Empty(self) -> "SimpleTable":
        return self.Field("")

    def Field(self, value: str, *classes: str) -> "SimpleTable":
        if not self.rows or len(self.rows[-1]) == self.cols or (self.sealed and self.sealed[-1]):
            self.rows.append([])
            self.cellAttrs.append([])
            self.sealed.append(False)
        cell_class = Classes(" ".join(classes))
        if cell_class:
            value = f'<div class="{cell_class}">{value}</div>'
        self.rows[-1].append(value)
        self.cellAttrs[-1].append("")
        return self

    def Attr(self, attrs: str) -> "SimpleTable":
        if not self.cellAttrs:
            return self
        row = self.cellAttrs[-1]
        if not row:
            return self
        if row[-1]:
            row[-1] += " " + attrs
        else:
            row[-1] = attrs
        used = 0
        for cell_attrs in row:
            span = 1
            m = re.search(r"colspan=['\"]?(\d+)", cell_attrs)
            if m:
                try:
                    span = int(m.group(1))
                except ValueError:
                    span = 1
            used += span
        if used >= self.cols:
            self.sealed[-1] = True
        return self

    def Render(self) -> str:
        rows_html: List[str] = []
        for row_idx, row in enumerate(self.rows):
            cells: List[str] = []
            used_cols = 0
            for col_idx, cell in enumerate(row):
                cls = self.colClasses[col_idx] if col_idx < len(self.colClasses) else ""
                cls_attr = f' class="{cls}"' if cls else ""
                attrs = ""
                if row_idx < len(self.cellAttrs) and col_idx < len(self.cellAttrs[row_idx]):
                    cell_attr = self.cellAttrs[row_idx][col_idx]
                    if cell_attr:
                        attrs = " " + cell_attr
                        m = re.search(r"colspan=['\"]?(\d+)", cell_attr)
                        if m:
                            try:
                                used_cols += int(m.group(1))
                            except ValueError:
                                used_cols += 1
                        else:
                            used_cols += 1
                    else:
                        used_cols += 1
                else:
                    used_cols += 1
                cells.append(f"<td{cls_attr}{attrs}>{cell}</td>")
            while used_cols < self.cols:
                cls = self.colClasses[used_cols] if used_cols < len(self.colClasses) else ""
                cls_attr = f' class="{cls}"' if cls else ""
                cells.append(f"<td{cls_attr}></td>")
                used_cols += 1
            rows_html.append("<tr>" + "".join(cells) + "</tr>")
        return (
            f'<table class="table-auto {self.css}"><tbody>' + "".join(rows_html) + "</tbody></table>"
        )


class Skeleton:
    @staticmethod
    def Default(target: Target) -> str:
        return div("animate-pulse", {"id": target.id})(
            div("bg-gray-200 h-5 rounded w-5/6 mb-2")(),
            div("bg-gray-200 h-5 rounded w-2/3 mb-2")(),
            div("bg-gray-200 h-5 rounded w-4/6")(),
        )

    @staticmethod
    def List(target: Target, count: int = 5) -> str:
        count = max(1, count)
        items = []
        for _ in range(count):
            items.append(
                div("flex items-center gap-3 mb-3")(
                    div("bg-gray-200 rounded-full h-10 w-10")(),
                    div("flex-1")(
                        div("bg-gray-200 h-4 rounded w-5/6 mb-2")(),
                        div("bg-gray-200 h-4 rounded w-3/6")(),
                    ),
                )
            )
        return div("animate-pulse", {"id": target.id})("".join(items))

    @staticmethod
    def Component(target: Target) -> str:
        return div("animate-pulse", {"id": target.id})(
            div("bg-gray-200 h-6 rounded w-2/5 mb-4")(),
            div("bg-gray-200 h-4 rounded w-full mb-2")(),
            div("bg-gray-200 h-4 rounded w-5/6 mb-2")(),
            div("bg-gray-200 h-4 rounded w-4/6")(),
        )

    @staticmethod
    def Page(target: Target) -> str:
        def card() -> str:
            return div("bg-white rounded-lg p-4 shadow mb-4")(
                div("bg-gray-200 h-5 rounded w-2/5 mb-3")(),
                div("bg-gray-200 h-4 rounded w-full mb-2")(),
                div("bg-gray-200 h-4 rounded w-5/6 mb-2")(),
                div("bg-gray-200 h-4 rounded w-4/6")(),
            )

        return div("animate-pulse", {"id": target.id})(
            div("bg-gray-200 h-8 rounded w-1/3 mb-6")(),
            card(),
            card(),
        )

    @staticmethod
    def Form(target: Target) -> str:
        def field_short() -> str:
            return div("")(
                div("bg-gray-200 h-4 rounded w-3/6 mb-2")(),
                div("bg-gray-200 h-10 rounded w-full")(),
            )

        def field_area() -> str:
            return div("")(
                div("bg-gray-200 h-4 rounded w-5/6 mb-2")(),
                div("bg-gray-200 h-20 rounded w-full")(),
            )

        def actions() -> str:
            return div("flex gap-2 mt-4")(
                div("bg-gray-200 h-10 rounded w-24")(),
                div("bg-gray-200 h-10 rounded w-32")(),
            )

        return div("animate-pulse", {"id": target.id})(
            div("bg-white rounded-lg p-4 shadow")(
                div("bg-gray-200 h-6 rounded w-2/5 mb-5")(),
                div("grid grid-cols-1 md:grid-cols-2 gap-4")(
                    div("")(field_short()),
                    div("")(field_short()),
                    div("")(field_area()),
                    div("")(field_short()),
                ),
                actions(),
            ),
        )


def Interval(timeout: int, callback: Callable[[], None]) -> Callable[[], None]:
    timer = threading.Event()

    def runner() -> None:
        while not timer.is_set():
            if timer.wait(timeout / 1000):
                break
            callback()

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()

    def stop() -> None:
        timer.set()

    return stop


def Timeout(timeout: int, callback: Callable[[], None]) -> Callable[[], None]:
    timer = threading.Timer(timeout / 1000, callback)
    timer.daemon = True
    timer.start()

    def cancel() -> None:
        timer.cancel()

    return cancel


def Hidden(name: str, input_type: str, value: Any) -> str:
    return input(
        "",
        {
            "type": input_type,
            "name": name,
            "value": value,
            "style": "display:none;visibility:hidden;position:absolute;left:-9999px;top:-9999px;",
        },
    )


def Script(body: str) -> str:
    return f"<script>{body}</script>"


# Public factory functions -------------------------------------------------


def Button(target: Optional[Target] = None) -> _Button:
    return _Button(target)


def IText(name: str, data: Optional[Mapping[str, Any]] = None) -> _TextInput:
    return _TextInput(name, data, "text")


def IPassword(name: str, data: Optional[Mapping[str, Any]] = None) -> _TextInput:
    return _TextInput(name, data, "password")


def IArea(name: str, data: Optional[Mapping[str, Any]] = None) -> _AreaInput:
    return _AreaInput(name, data)


def INumber(name: str, data: Optional[Mapping[str, Any]] = None) -> _NumberInput:
    return _NumberInput(name, data)


def IDate(name: str, data: Optional[Mapping[str, Any]] = None) -> _DateInput:
    return _DateInput(name, data, "date")


def ITime(name: str, data: Optional[Mapping[str, Any]] = None) -> _TimeInput:
    return _TimeInput(name, data, "time")


def IDateTime(name: str, data: Optional[Mapping[str, Any]] = None) -> _DateInput:
    return _DateInput(name, data, "datetime-local")


def ISelect(name: str, data: Optional[Mapping[str, Any]] = None) -> _SelectInput:
    return _SelectInput(name, data)


def ICheckbox(name: str, data: Optional[Mapping[str, Any]] = None) -> _CheckboxInput:
    return _CheckboxInput(name, data)


def IRadio(name: str, data: Optional[Mapping[str, Any]] = None) -> _RadioInput:
    return _RadioInput(name, data)


def IRadioButtons(name: str, data: Optional[Mapping[str, Any]] = None) -> _RadioButtons:
    return _RadioButtons(name, data)


def ThemeSwitcher(css: str = "") -> str:
    element_id = "psui_theme_" + RandomString(8)
    sun = '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6.76 4.84l-1.8-1.79-1.41 1.41 1.79 1.8 1.42-1.42zm10.48 14.32l1.79 1.8 1.41-1.41-1.8-1.79-1.4 1.4zM12 4V1h-0 0 0 0v3zm0 19v-3h0 0 0 0v3zM4 12H1v0 0 0 0h3zm19 0h-3v0 0 0 0h3zM6.76 19.16l-1.79 1.8 1.41 1.41 1.8-1.79-1.42-1.42zM19.16 6.76l1.8-1.79-1.41-1.41-1.8 1.79 1.41 1.41zM12 8a4 4 0 100 8 4 4 0 000-8z"/></svg>'
    moon = '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24"><path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/></svg>'
    desktop = '<svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="currentColor" viewBox="0 0 24 24"><path d="M3 4h18v12H3z"/><path d="M8 20h8v-2H8z"/></svg>'
    button_html = Trim(
        f"""
        <button id="{element_id}" type="button" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full border border-gray-300 bg-white text-gray-700 hover:bg-gray-100 dark:bg-gray-800 dark:text-gray-200 dark:border-gray-600 dark:hover:bg-gray-700 shadow-sm {css}">
            <span class="icon">{desktop}</span>
            <span class="label">Auto</span>
        </button>
        """
    )
    sun_js = json.dumps(sun)
    moon_js = json.dumps(moon)
    desktop_js = json.dumps(desktop)
    script = Trim(
        f"""
        <script>(function(){{
            var btn=document.getElementById('{element_id}');
            if(!btn) return;
            var modes=['system','light','dark'];
            function getPref(){{ try {{ return localStorage.getItem('theme')||'system'; }} catch(_) {{ return 'system'; }} }}
            function resolve(mode){{
                if(mode==='system'){{
                    try {{ return (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)?'dark':'light'; }}
                    catch(_){{ return 'light'; }}
                }}
                return mode;
            }}
            function setMode(mode){{ try {{ if(typeof setTheme==='function') setTheme(mode); }} catch(_){{}} }}
            function labelFor(mode){{ return mode==='system'?'Auto':(mode.charAt(0).toUpperCase()+mode.slice(1)); }}
            function iconFor(eff){{ if(eff==='dark') return {moon_js}; if(eff==='light') return {sun_js}; return {desktop_js}; }}
            function render(){{
                var pref=getPref();
                var eff=resolve(pref);
                var icon=iconFor(eff);
                var iconNode=btn.querySelector('.icon');
                if(iconNode) iconNode.innerHTML=icon;
                var labelNode=btn.querySelector('.label');
                if(labelNode) labelNode.textContent=labelFor(pref);
            }}
            render();
            btn.addEventListener('click', function(){{
                var pref=getPref();
                var idx=modes.indexOf(pref);
                var next=modes[(idx+1)%modes.length];
                setMode(next);
                render();
            }});
            try {{
                if(window.matchMedia){{
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(){{
                        if(getPref()==='system') render();
                    }});
                }}
            }} catch(_){{}}
        }})();</script>
        """
    )
    return button_html + script


script = Script

__all__ = [
    "Trim",
    "Normalize",
    "Classes",
    "If",
    "Iff",
    "Map",
    "Map2",
    "For",
    "RandomString",
    "makeId",
    "XS",
    "SM",
    "MD",
    "ST",
    "LG",
    "XL",
    "AREA",
    "INPUT",
    "VALUE",
    "BTN",
    "DISABLED",
    "Yellow",
    "YellowOutline",
    "Green",
    "GreenOutline",
    "Purple",
    "PurpleOutline",
    "Blue",
    "BlueOutline",
    "Red",
    "RedOutline",
    "Gray",
    "GrayOutline",
    "White",
    "WhiteOutline",
    "a",
    "i",
    "p",
    "div",
    "span",
    "form",
    "textarea",
    "select",
    "option",
    "ul",
    "li",
    "canvas",
    "img",
    "input",
    "label",
    "space",
    "Flex1",
    "Icon",
    "IconStart",
    "IconLeft",
    "IconRight",
    "IconEnd",
    "Target",
    "Button",
    "Label",
    "IText",
    "IPassword",
    "IArea",
    "INumber",
    "IDate",
    "ITime",
    "IDateTime",
    "ISelect",
    "ICheckbox",
    "IRadio",
    "IRadioButtons",
    "SimpleTable",
    "Skeleton",
    "ThemeSwitcher",
    "Interval",
    "Timeout",
    "Hidden",
    "Script",
    "script",
]
