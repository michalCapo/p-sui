from __future__ import annotations

import ui
from ui_server import Context


def Icons(ctx: Context) -> str:
    icon = ui.div("flex items-center gap-3 border border-gray-200 rounded p-4 bg-white rounded-lg")

    return ui.div("w-full")(
        ui.div("flex flex-col gap-3")(
            icon(
                ui.IconStart(
                    "w-6 h-6 bg-gray-400 rounded",
                    "Start aligned icon",
                ),
            ),
            icon(
                ui.IconLeft(
                    "w-6 h-6 bg-blue-600 rounded",
                    "Centered with icon left",
                ),
            ),
            icon(
                ui.IconRight(
                    "w-6 h-6 bg-green-600 rounded",
                    "Centered with icon right",
                ),
            ),
            icon(
                ui.IconEnd("w-6 h-6 bg-purple-600 rounded", "End-aligned icon"),
            ),
        ),
    )
