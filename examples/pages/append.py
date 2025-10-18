from __future__ import annotations

import ui
from ui_server import Context
from datetime import datetime


def pad2(value: int) -> str:
    if value < 10:
        return "0" + str(value)
    return str(value)


def format_time(date: datetime) -> str:
    hours = pad2(date.hour)
    minutes = pad2(date.minute)
    seconds = pad2(date.second)
    return hours + ":" + minutes + ":" + seconds


def render_entry(text: str) -> str:
    return ui.div("p-2 rounded border border-gray-200 bg-white dark:bg-gray-900")(
        ui.span("text-sm text-gray-600")(text),
    )


def add_end(_ctx: Context) -> str:
    label = "Appended at " + format_time(datetime.now())
    return render_entry(label)


def add_start(_ctx: Context) -> str:
    label = "Prepended at " + format_time(datetime.now())
    return render_entry(label)


def AppendContent(ctx: Context) -> str:
    target = ui.Target()
    controls = ui.div("flex gap-2")(
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded")
        .Click(ctx.Call(add_end).Append(target))
        .Render("Add at end"),
        ui.Button()
        .Color(ui.Green)
        .Class("rounded")
        .Click(ctx.Call(add_start).Prepend(target))
        .Render("Add at start"),
    )
    container = ui.div("space-y-2", target)(
        render_entry("Initial item"),
    )
    return ui.div("max-w-5xl mx-auto flex flex-col gap-4")(
        ui.div("text-2xl font-bold")("Append / Prepend Demo"),
        ui.div("text-gray-600")("Click buttons to insert items at the beginning or end of the list."),
        controls,
        container,
    )

