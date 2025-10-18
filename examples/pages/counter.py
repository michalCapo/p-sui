from __future__ import annotations

import ui
from ui_server import Context
from typing import TypedDict


class Model(TypedDict):
    Count: int


def decrement(ctx: Context) -> str:
    counter: Model = {"Count": 0}
    ctx.Body(counter)

    counter["Count"] -= 1

    if counter["Count"] < 0:
        counter["Count"] = 0

    return render(ctx, counter)


def increment(ctx: Context) -> str:
    counter: Model = {"Count": 0}
    ctx.Body(counter)

    counter["Count"] += 1

    return render(ctx, counter)


def render(ctx: Context, counter: Model) -> str:
    target = ui.Target()

    return ui.div("flex gap-2 items-center bg-purple-500 rounded text-white p-px", target)(
        ui.Button()
            .Click(ctx.Call(decrement, counter).Replace(target))
            .Color(ui.Purple)
            .Class("rounded-l px-5")
            .Render("-"),

        ui.div("text-2xl")(str(counter["Count"])),

        ui.Button()
            .Click(ctx.Call(increment, counter).Replace(target))
            .Color(ui.Purple)
            .Class("rounded-r px-5")
            .Render("+"),
    )


def Counter(ctx: Context, start: int = 3) -> str:
    return render(ctx, {"Count": start})


def CounterContent(ctx: Context) -> str:
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Counter"),
        ui.div("text-gray-600")("Counter component with server-side rendering."),
        ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full flex gap-8")(
            Counter(ctx, 2),
            Counter(ctx, 8)
        )
    )
