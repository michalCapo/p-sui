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
        .Class("rounded-l px-5")
        .Render("-"),
        ui.div("text-2xl")(str(counter["Count"])),
        ui.Button()
        .Click(ctx.Call(increment, counter).Replace(target))
        .Class("rounded-r px-5")
        .Render("+"),
    )


def Counter(ctx: Context, start: int = 3) -> str:
    return render(ctx, {"Count": start})

