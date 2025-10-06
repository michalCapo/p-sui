from __future__ import annotations

import ui
from ui_server import Context
from .hello import Hello
from .counter import Counter
from .login import Login
from .deffered import Deffered
from .icons import Icons
from .clock import Clock


def OthersContent(ctx: Context) -> str:
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Others"),
        ui.div("text-gray-600")(
            "Miscellaneous demos: Hello, Counter, Login, and icon helpers.",
        ),
        # clock (WS)
        ui.div("bg-white p-6 rounded-lg shadow w-full")(
            ui.div("text-lg font-bold")("Clock (WS)"),
            ui.div("text-gray-600 mb-3")(
                "Updates every second via server-sent patches.",
            ),
            Clock(ctx),
        ),
        # deferred (WS)
        ui.div("bg-white p-6 rounded-lg shadow w-full")(
            ui.div("text-lg font-bold")("Deferred (WS)"),
            ui.div("text-gray-600 mb-3")(
                "Shows a skeleton that is replaced when the server finishes rendering.",
            ),
            Deffered(ctx),
        ),
        ui.div("grid grid-cols-2 gap-4")(
            # hello
            ui.div("bg-white p-6 rounded-lg shadow w-full")(
                ui.div("text-lg font-bold mb-3")("Hello"),
                Hello(ctx),
            ),
            # counter
            ui.div("bg-white p-6 rounded-lg shadow w-full")(
                ui.div("text-lg font-bold mb-3")("Counter"),
                ui.div("flex gap-4 items-center p-4 border rounded")(
                    Counter(ctx, 4),
                    ui.Flex1,
                    Counter(ctx, 6),
                ),
            ),
            # login
            ui.div("bg-white p-6 rounded-lg shadow w-full")(
                ui.div("text-lg font-bold mb-3")("Login"),
                Login(ctx),
            ),
            # icons
            ui.div("bg-white p-6 rounded-lg shadow w-full")(
                ui.div("text-lg font-bold mb-3")("Icons"),
                Icons(),
            ),
        ),
    )

