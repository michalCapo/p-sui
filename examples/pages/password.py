from __future__ import annotations

import ui
from ui_server import Context


def PasswordContent(_ctx: Context) -> str:
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

    # Basics & states
    basics = ui.div("flex flex-col gap-2")(
        row("Default", ui.IPassword("P1").Render("Password")),
        row(
            "With placeholder",
            ui.IPassword("P2").Placeholder("••••••••").Render("Password"),
        ),
        row(
            "Required",
            ui.IPassword("P3").Required().Render("Password (required)"),
        ),
        row(
            "Readonly",
            ui.IPassword("P4")
            .Readonly()
            .Value("secret")
            .Render("Readonly password"),
        ),
        row(
            "Disabled",
            ui.IPassword("P5").Disabled().Render("Password (disabled)"),
        ),
        row(
            "Preset value",
            ui.IPassword("P6").Value("topsecret").Render("Preset value"),
        ),
        row(
            "Type switched to text (visible)",
            ui.IPassword("P7")
            .Type("text")
            .Value("visible value")
            .Render("As text"),
        ),
    )

    # Styling
    styling = ui.div("flex flex-col gap-2")(
        row(
            "Wrapper .Class()",
            ui.IPassword("C1")
            .Class("p-2 rounded bg-yellow-50")
            .Render("Styled wrapper"),
        ),
        row(
            "Label .ClassLabel()",
            ui.IPassword("C2")
            .ClassLabel("text-purple-700 font-bold")
            .Render("Custom label"),
        ),
        row(
            "Input .ClassInput()",
            ui.IPassword("C3")
            .ClassInput("bg-blue-50")
            .Render("Custom input background"),
        ),
        row("Size: XS", ui.IPassword("S1").Size(ui.XS).Render("XS")),
        row("Size: XL", ui.IPassword("S2").Size(ui.XL).Render("XL")),
    )

    # Behavior & attributes
    behavior = ui.div("flex flex-col gap-2")(
        row(
            "Autocomplete (new-password)",
            ui.IPassword("A1")
            .Autocomplete("new-password")
            .Render("New password"),
        ),
        row(
            "Pattern (min 8 chars)",
            ui.IPassword("A2")
            .Pattern(".{8,}")
            .Placeholder("at least 8 characters")
            .Render("Min length pattern"),
        ),
        row(
            "Change handler (console.log)",
            ui.IPassword("A3")
            .Change("console.log('changed pw', this && this.value)")
            .Render("On change, log"),
        ),
        row(
            "Click handler (console.log)",
            ui.IPassword("A4")
            .Click("console.log('clicked pw')")
            .Render("On click, log"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Password"),
        ui.div("text-gray-600")(
            "Common features and states for password inputs.",
        ),
        card("Basics & states", basics),
        card("Styling", styling),
        card("Behavior & attributes", behavior),
    )

