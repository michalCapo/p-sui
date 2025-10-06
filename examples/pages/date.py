from __future__ import annotations

import ui
from ui_server import Context
from datetime import datetime
from typing import TypedDict


class DateData(TypedDict):
    Birth: str


def DateContent(_ctx: Context) -> str:
    def card(title: str, body: str) -> str:
        return ui.div("bg-white p-4 rounded-lg shadow flex flex-col gap-3")(
            ui.div("text-sm font-bold text-gray-700")(title),
            body,
        )

    def row(label: str, control: str) -> str:
        return ui.div("flex items-center justify-between gap-4")(
            ui.div("text-sm text-gray-600")(label),
            ui.div("w-64")(control),
        )

    data: DateData = {"Birth": datetime.now().strftime("%Y-%m-%d")}

    basics = ui.div("flex flex-col gap-2")(
        row("Date", ui.IDate("Birth", data).Render("Birth date")),
        row("Time", ui.ITime("Alarm").Render("Alarm")),
        row("DateTime", ui.IDateTime("Meeting").Render("Meeting time")),
        row(
            "Required date",
            ui.IDate("Req").Required().Render("Required date"),
        ),
        row(
            "Readonly time",
            ui.ITime("RO").Readonly().Value("10:00").Render("Readonly time"),
        ),
        row(
            "Disabled datetime",
            ui.IDateTime("D").Disabled().Render("Disabled datetime"),
        ),
    )

    styling = ui.div("flex flex-col gap-2")(
        row(
            "Wrapper .Class()",
            ui.IDate("C")
            .Class("p-2 rounded bg-yellow-50")
            .Render("Styled wrapper"),
        ),
        row(
            "Label .ClassLabel()",
            ui.ITime("CL")
            .ClassLabel("text-purple-700 font-bold")
            .Render("Custom label"),
        ),
        row(
            "Input .ClassInput()",
            ui.IDateTime("CI")
            .ClassInput("bg-blue-50")
            .Render("Custom input background"),
        ),
        row("Size: ST", ui.IDate("S").Size(ui.ST).Render("Standard size")),
    )

    behavior = ui.div("flex flex-col gap-2")(
        row(
            "Change handler (console.log)",
            ui.IDate("Change")
            .Change("console.log('changed', this && this.value)")
            .Render("On change, log"),
        ),
        row(
            "Click handler (console.log)",
            ui.IDateTime("Click")
            .Click("console.log('clicked datetime')")
            .Render("On click, log"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Date, Time, DateTime"),
        ui.div("text-gray-600")("Common attributes across temporal inputs."),
        card("Basics & states", basics),
        card("Styling", styling),
        card("Behavior & attributes", behavior),
    )

