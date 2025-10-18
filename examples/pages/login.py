from __future__ import annotations

import ui
from ui_server import Context

_form_target = ui.Target()


def Login(ctx: Context) -> str:
    form_data = {"Name": "", "Password": ""}
    return _render(ctx, form_data, None)


def _action_login(ctx: Context) -> str:
    form_data = {"Name": "", "Password": ""}
    ctx.Body(form_data)
    if form_data.get("Name") != "user" or form_data.get("Password") != "password":
        return _render(ctx, form_data, "Invalid credentials")
    return ui.div(
        "text-green-600 max-w-md p-8 text-center font-bold rounded-lg bg-white shadow-xl border border-gray-200",
    )("Success")


def _render(ctx: Context, data: dict, error: str | None) -> str:
    error_html = ""
    if error:
        error_html = ui.div(
            "text-red-600 p-4 rounded text-center border-4 border-red-600 bg-white",
        )(error)

    form_attrs = ctx.Submit(_action_login).Replace(_form_target)

    return ui.form(
        "border border-gray-200 flex flex-col gap-4 max-w-md bg-white p-8 rounded-lg shadow-xl",
        _form_target,
        form_attrs,
    )(
        error_html,
        ui.IText("Name", data).Required().Render("Name"),
        ui.IPassword("Password", data).Required().Render("Password"),
        ui.Button().Submit().Color(ui.Blue).Class("rounded").Render("Login"),
    )


__all__ = ["Login"]
