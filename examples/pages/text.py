from __future__ import annotations

import ui
from ui_server import Context


def TextContent(_ctx: Context) -> str:
    def card(title: str, body: str) -> str:
        return ui.div("bg-white p-4 rounded-lg shadow flex flex-col gap-3")(
            ui.div("text-sm font-bold text-gray-700")(title),
            body,
        )

    def row(label: str, control: str) -> str:
        return ui.div("flex items-center justify-between gap-4")(
            ui.div("text-sm text-gray-600")(label),
            control,
        )

    data = {"Name": "John Doe"}

    basics = ui.div("flex flex-col gap-2")(
        row("Default", ui.IText("Name", data).Render("Name")),
        row("With placeholder", ui.IText("X").Placeholder("Type your name").Render("Your name")),
        row("Required field", ui.IText("Y").Required().Render("Required field")),
        row(
            "Readonly",
            ui.IText("Y2").Readonly().Value("Read-only value").Render("Readonly field"),
        ),
        row(
            "Disabled",
            ui.IText("Z").Disabled().Placeholder("Cannot type").Render("Disabled"),
        ),
        row("With preset value", ui.IText("Preset").Value("Preset text").Render("Preset")),
    )

    styling = ui.div("flex flex-col gap-2")(
        row(
            "Wrapper .Class()",
            ui.IText("C1").Class("p-2 rounded bg-yellow-50").Render("Styled wrapper"),
        ),
        row(
            "Label .ClassLabel()",
            ui.IText("C2").ClassLabel("text-purple-700 font-bold").Render("Custom label"),
        ),
        row(
            "Input .ClassInput()",
            ui.IText("C3").ClassInput("bg-blue-50").Render("Custom input background"),
        ),
        row("Size: XS", ui.IText("S1").Size(ui.XS).Render("XS")),
        row("Size: MD (default)", ui.IText("S2").Size(ui.MD).Render("MD")),
        row("Size: XL", ui.IText("S3").Size(ui.XL).Render("XL")),
    )

    behavior = ui.div("flex flex-col gap-2")(
        row("Autocomplete", ui.IText("Auto").Autocomplete("name").Render("Name (autocomplete)")),
        row(
            "Pattern (email-like)",
            ui.IText("Pattern")
            .Type("email")
            .Pattern("[^@]+@[^@]+\\.[^@]+")
            .Placeholder("user@example.com")
            .Render("Email"),
        ),
        row("Type switch (password)", ui.IText("PassLike").Type("password").Render("Password-like")),
        row(
            "Change handler (console.log)",
            ui.IText("Change")
            .Change("console.log('changed', this && this.value)")
            .Render("On change, log value"),
        ),
        row(
            "Click handler (console.log)",
            ui.IText("Click")
            .Click("console.log('clicked input')")
            .Render("On click, log"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Text input"),
        ui.div("text-gray-600")("Common features supported by text-like inputs."),
        card("Basics & states", basics),
        card("Styling", styling),
        card("Behavior & attributes", behavior),
    )

