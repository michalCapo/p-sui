from __future__ import annotations

import ui
from ui_server import Context


def ShowcaseContent(_ctx: Context) -> str:
    cards = []
    cards.append(
        ui.div("bg-white p-6 rounded-lg shadow flex flex-col gap-3")(
            ui.div("text-xl font-semibold")("Interactive Components"),
            ui.div("text-gray-600")("Navigate using the menu to explore each component demo."),
            ui.div("flex gap-2 flex-wrap")(
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/button"})("Buttons"),
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/text"})("Text inputs"),
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/number"})("Number inputs"),
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/login"})("Form"),
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/collate"})("Collate"),
                ui.a("px-3 py-2 rounded bg-blue-600 text-white", {"href": "/captcha"})("Captcha"),
            ),
        )
    )

    cards.append(
        ui.div("bg-white p-6 rounded-lg shadow flex flex-col gap-3")(
            ui.div("text-xl font-semibold")("Get Started"),
            ui.div("text-gray-600")(
                "Use the navigation bar to switch between demos. Each page showcases the same server-side primitives provided by psui.",
            ),
        )
    )

    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6")(
        ui.div("text-4xl font-bold")("psui Showcase"),
        ui.div("text-gray-600")(
            "Reusable helpers for rendering Tailwind-flavoured HTML from Python. This showcase mirrors a subset of the original TypeScript examples.",
        ),
        "".join(cards),
    )


__all__ = ["ShowcaseContent"]
