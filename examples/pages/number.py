from __future__ import annotations

import ui
from ui_server import Context


def NumberContent(_ctx: Context) -> str:
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

    data = {"Age": 30, "Price": 19.9}

    basics = ui.div("flex flex-col gap-2")(
        row("Integer with range/step", ui.INumber("Age", data).Numbers(0, 120, 1).Render("Age")),
        row("Float formatted (%.2f)", ui.INumber("Price", data).Format("%.2f").Render("Price")),
        row("Required", ui.INumber("Req").Required().Render("Required")),
        row("Readonly", ui.INumber("RO").Readonly().Value("42").Render("Readonly")),
        row("Disabled", ui.INumber("D").Disabled().Render("Disabled")),
        row("Placeholder", ui.INumber("PH").Placeholder("0..100").Render("Number")),
    )

    styling = ui.div("flex flex-col gap-2")(
        row("Wrapper .Class()", ui.INumber("C").Class("p-2 rounded bg-yellow-50").Render("Styled wrapper")),
        row("Label .ClassLabel()", ui.INumber("CL").ClassLabel("text-purple-700 font-bold").Render("Custom label")),
        row("Input .ClassInput()", ui.INumber("CI").ClassInput("bg-blue-50").Render("Custom input background")),
        row("Size: LG", ui.INumber("S").Size(ui.LG).Render("Large size")),
    )

    behavior = ui.div("flex flex-col gap-2")(
        row(
            "Change handler (console.log)",
            ui.INumber("Change").Change("console.log('changed', this && this.value)").Render("On change, log"),
        ),
        row(
            "Click handler (console.log)",
            ui.INumber("Click").Click("console.log('clicked number')").Render("On click, log"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Number input"),
        ui.div("text-gray-600")("Ranges, formatting, and common attributes."),
        card("Basics & states", basics),
        card("Styling", styling),
        card("Behavior & attributes", behavior),
    )

