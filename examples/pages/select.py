from __future__ import annotations

import ui
from ui_server import Context
from typing import TypedDict


class SelectData(TypedDict):
    Country: str


def SelectContent(_ctx: Context) -> str:
    def row(title: str, content: str) -> str:
        return ui.div(
            "bg-white p-4 rounded-lg shadow border border-gray-200 flex flex-col gap-3",
        )(ui.div("text-sm font-bold text-gray-700")(title), content)

    def ex(label: str, control: str, extra: str = "") -> str:
        return ui.div("flex items-center justify-between gap-4 w-full")(
            ui.div("text-sm text-gray-600")(label),
            ui.div("flex items-center gap-3")(ui.div("w-64")(control), extra),
        )

    opts = [
        {"id": "", "value": "Select..."},
        {"id": "one", "value": "One"},
        {"id": "two", "value": "Two"},
        {"id": "three", "value": "Three"},
    ]
    
    data: SelectData = {"Country": ""}
    
    opts_no_placeholder = [
        {"id": "one", "value": "One"},
        {"id": "two", "value": "Two"},
        {"id": "three", "value": "Three"},
    ]

    basics = ui.div("flex flex-col gap-2")(
        ex(
            "Default",
            ui.ISelect("Country", data).Options(opts).Render("Country"),
        ),
        ex(
            "Placeholder",
            ui.ISelect("Country", data)
            .Options(opts)
            .Placeholder("Pick one")
            .Render("Choose"),
        ),
    )

    validation = ui.div("flex flex-col gap-2")(
        ex(
            "Error state",
            ui.ISelect("Err")
            .Options(opts)
            .Placeholder("Please select")
            .Error()
            .Render("Invalid"),
        ),
        ex(
            "Required + empty",
            ui.ISelect("Z").Options(opts).Empty().Required().Render("Required"),
        ),
        ex(
            "Disabled",
            ui.ISelect("Y").Options(opts).Disabled().Render("Disabled"),
        ),
    )

    variants = ui.div("flex flex-col gap-2")(
        ex(
            "No placeholder + <empty>",
            ui.ISelect("Country", data)
            .Options(opts_no_placeholder)
            .EmptyText("<empty>")
            .Render("Choose"),
        ),
    )

    sizes = ui.div("flex flex-col gap-2")(
        ex(
            "Small (SM)",
            ui.ISelect("Country", data)
            .Options(opts)
            .Size(ui.SM)
            .ClassLabel("text-sm")
            .Render("Country"),
        ),
        ex(
            "Extra small (XS)",
            ui.ISelect("Country", data)
            .Options(opts)
            .Size(ui.XS)
            .ClassLabel("text-sm")
            .Render("Country"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Select"),
        ui.div("text-gray-600")(
            "Select input variations, validation, and sizing.",
        ),
        row("Basics", basics),
        row("Validation", validation),
        row("Variants", variants),
        row("Sizes", sizes),
    )

