from __future__ import annotations

import ui
from ui_server import Context
from datetime import datetime


def Clock(ctx: Context) -> str:
    # Render into a stable target id so reloads keep the same element
    target = ui.Target()

    # Clock helpers
    def pad2(n: int) -> str:
        if n < 10:
            return "0" + str(n)
        else:
            return str(n)

    def fmt_time(d: datetime) -> str:
        h = pad2(d.hour)
        m = pad2(d.minute)
        s = pad2(d.second)
        return h + ":" + m + ":" + s

    def Render(d: datetime) -> str:
        return ui.div("flex items-baseline gap-3", target)(
            ui.div("text-4xl font-mono tracking-widest")(fmt_time(d)),
            ui.div("text-gray-500")("Live server time"),
        )

    def update_clock() -> None:
        ctx.Patch(target.Replace, Render(datetime.now()), stop)

    stop = ui.Interval(1000, update_clock)

    return Render(datetime.now())

