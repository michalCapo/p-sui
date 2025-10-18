from __future__ import annotations

import ui
from ui_server import Context


def ButtonContent(_ctx: Context) -> str:
    def row(title: str, content: str) -> str:
        return ui.div("bg-white p-4 rounded-lg shadow border border-gray-200 flex flex-col gap-3")(
            ui.div("text-sm font-bold text-gray-700")(title),
            content,
        )

    def example(label: str, button_html: str) -> str:
        return ui.div("flex items-center justify-between gap-4 w-full")(
            ui.div("text-sm text-gray-600")(label),
            button_html,
        )

    sizes = [
        {"k": ui.XS, "t": "Extra small"},
        {"k": ui.SM, "t": "Small"},
        {"k": ui.MD, "t": "Medium (default)"},
        {"k": ui.ST, "t": "Standard"},
        {"k": ui.LG, "t": "Large"},
        {"k": ui.XL, "t": "Extra large"},
    ]

    solid = [
        {"c": ui.Blue, "t": "Blue"},
        {"c": ui.Green, "t": "Green"},
        {"c": ui.Red, "t": "Red"},
        {"c": ui.Purple, "t": "Purple"},
        {"c": ui.Yellow, "t": "Yellow"},
        {"c": ui.Gray, "t": "Gray"},
        {"c": ui.White, "t": "White"},
    ]

    outline = [
        {"c": ui.BlueOutline, "t": "Blue (outline)"},
        {"c": ui.GreenOutline, "t": "Green (outline)"},
        {"c": ui.RedOutline, "t": "Red (outline)"},
        {"c": ui.PurpleOutline, "t": "Purple (outline)"},
        {"c": ui.YellowOutline, "t": "Yellow (outline)"},
        {"c": ui.GrayOutline, "t": "Gray (outline)"},
        {"c": ui.WhiteOutline, "t": "White (outline)"},
    ]

    colors_grid = []
    for item in solid + outline:
        colors_grid.append(
            ui.Button()
            .Color(item["c"])
            .Class("rounded w-full")
            .Render(item["t"])
        )
    colors_html = ui.div(
        "grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2",
    )("\n".join(colors_grid))

    size_rows = []
    for item in sizes:
        size_rows.append(
            example(
                item["t"],
                ui.Button().Size(item["k"]).Class("rounded").Color(ui.Blue).Render("Click me"),
            )
        )
    sizes_html = ui.div("flex flex-col gap-2")("".join(size_rows))

    basics = ui.div("flex flex-col gap-2")(
        example("Button", ui.Button().Class("rounded").Color(ui.Blue).Render("Click me")),
        example(
            "Button — disabled",
            ui.Button().Disabled(True).Class("rounded").Color(ui.Blue).Render("Unavailable"),
        ),
        example(
            "Button as link",
            ui.Button().Href("https://example.com").Class("rounded").Color(ui.Blue).Render("Visit example.com"),
        ),
        example(
            "Submit button (visual)",
            ui.Button().Submit().Class("rounded").Color(ui.Green).Render("Submit"),
        ),
        example(
            "Reset button (visual)",
            ui.Button().Reset().Class("rounded").Color(ui.Gray).Render("Reset"),
        ),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Button"),
        ui.div("text-gray-600")("Common button states and variations."),
        row("Basics", basics),
        row("Colors (solid and outline)", colors_html),
        row("Sizes", sizes_html),
    )

