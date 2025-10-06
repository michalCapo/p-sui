from __future__ import annotations

import ui
from ui_server import Context
from typing import TypedDict


class CheckboxData(TypedDict):
    Agree: bool


def CheckboxContent(_ctx: Context) -> str:
    def row(title: str, content: str) -> str:
        return ui.div(
            "bg-white p-4 rounded-lg shadow border border-gray-200 flex flex-col gap-3",
        )(ui.div("text-sm font-bold text-gray-700")(title), content)

    def ex(label: str, control: str) -> str:
        return ui.div("flex items-center justify-between gap-4 w-full")(
            ui.div("text-sm text-gray-600")(label),
            control,
        )

    data: CheckboxData = {"Agree": True}

    basics = ui.div("flex flex-col gap-2")(
        ex("Default", ui.ICheckbox("Agree", data).Render("I agree")),
        ex("Required", ui.ICheckbox("Terms").Required().Render("Accept terms")),
        ex("Unchecked", ui.ICheckbox("X").Render("Unchecked")),
        ex("Disabled", ui.ICheckbox("D").Disabled().Render("Disabled")),
    )

    sizes = ui.div("flex flex-col gap-2")(
        ex("Small (SM)", ui.ICheckbox("S").Size(ui.SM).Render("Small")),
        ex(
            "Extra small (XS)",
            ui.ICheckbox("XS").Size(ui.XS).Render("Extra small"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Checkbox"),
        ui.div("text-gray-600")(
            "Checkbox states, sizes, and required validation.",
        ),
        row("Basics", basics),
        row("Sizes", sizes),
    )

