from __future__ import annotations

import ui
from ui_server import Context
import asyncio
from typing import Optional


async def LazyLoadData(_: Context, target: ui.Target) -> str:
    await asyncio.sleep(2.0)

    return ui.div( "space-y-4", target)(
        ui.div( "bg-gray-50 dark:bg-gray-900 p-4 rounded shadow border border-gray-200 rounded p-4")(
            ui.div("text-lg font-semibold")("Deferred content loaded"),
            ui.div("text-gray-600 text-sm")(
                "This block replaced the skeleton via WebSocket patch.",
            ),
        ),
    )


async def LazyMoreData(ctx: Context, target: ui.Target) -> str:
    await asyncio.sleep(2.1)

    return ui.div("grid grid-cols-5 gap-4")(
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded text-sm")
        .Click(ctx.Call(Deffered).Replace(target))
        .Render("Default skeleton"),
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded text-sm")
        .Click(ctx.Call(Deffered, {"as": "component"}).Replace(target))
        .Render("Component skeleton"),
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded text-sm")
        .Click(ctx.Call(Deffered, {"as": "list"}).Replace(target))
        .Render("List skeleton"),
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded text-sm")
        .Click(ctx.Call(Deffered, {"as": "page"}).Replace(target))
        .Render("Page skeleton"),
        ui.Button()
        .Color(ui.Blue)
        .Class("rounded text-sm")
        .Click(ctx.Call(Deffered, {"as": "form"}).Replace(target))
        .Render("Form skeleton"),
    )


# Deferred block (WS skeleton -> replace when ready)
def Deffered(ctx: Context) -> str:
    target = ui.Target()
    form: dict[str, Optional[str]] = {"as": None}

    # scans the body into form object
    ctx.Body(form)

    # replace the target when the data is loaded
    ctx.Patch(target.Replace, LazyLoadData(ctx, target))

    # append to the target when more data is loaded
    # ctx.Patch(target.Append, LazyMoreData(ctx, target))

    return target.Skeleton(form["as"])


def DefferedContent(ctx: Context) -> str:
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Deferred"),
        ui.div("text-gray-600")("Deferred component with server-side rendering. When the server is busy, the client will show a skeleton."),
        ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full flex gap-8")(
            Deffered(ctx)
        )
    )