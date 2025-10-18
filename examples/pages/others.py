from __future__ import annotations

import ui
from ui_server import Context
from pages.hello import Hello
from pages.login import Login
from pages.icons import Icons


def OthersContent(ctx: Context) -> str:
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Others"),
        ui.div("text-gray-600")(
            "Miscellaneous demos: Hello, Counter, Login, and icon helpers.",
        ),
        ui.div("grid grid-cols-2 gap-4")(
            # login
            ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full")(
                ui.div("text-lg font-bold mb-3")("Login"),
                Login(ctx),
            ),
            # icons
            ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full")(
                ui.div("text-lg font-bold mb-3")("Icons"),
                Icons(ctx),
            ),
            # hello
            ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full")(
                ui.div("text-lg font-bold mb-3")("Hello"),
                Hello(ctx),
            ),
        ),
    )

