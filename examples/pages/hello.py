from __future__ import annotations

import ui
from ui_server import Context
import asyncio


def say_hello(ctx: Context) -> str:
    ctx.Success("Hello")
    return ""


async def say_delay(ctx: Context) -> str:
    await asyncio.sleep(2.0)
    ctx.Info("Information")
    return ""


def say_error(ctx: Context) -> str:
    ctx.Error("Hello error")
    return ""


def say_hello_again(_: Context) -> str:
    raise Exception("Hello again")


buttons = "rounded whitespace-nowrap bg-white"


def Hello(ctx: Context) -> str:
    return ui.div("gap-4 border rounded p-4")(
        ui.div("grid grid-cols-2 justify-start gap-4 items-center")(
            ui.Button()
            .Color(ui.GreenOutline)
            .Class(buttons)
            .Click(ctx.Call(say_hello).Replace(ui.Target()))
            .Render("with ok"),

            ui.Button()
            .Color(ui.RedOutline)
            .Class(buttons)
            .Click(ctx.Call(say_error).Replace(ui.Target()))
            .Render("with error"),

            ui.Button()
            .Color(ui.BlueOutline)
            .Class(buttons)
            .Click(ctx.Call(say_delay).Replace(ui.Target()))
            .Render("with delay"),

            ui.Button()
            .Color(ui.YellowOutline)
            .Class(buttons)
            .Click(ctx.Call(say_hello_again).Replace(ui.Target()))
            .Render("with crash"),
        ),
    )

