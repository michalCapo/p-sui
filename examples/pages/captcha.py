from __future__ import annotations

import ui
from ui_server import Context
from ui_captcha import Captcha


def _on_validated(ctx: Context) -> str:
    return ui.div("text-green-600")("Captcha validated successfully!")


def CaptchaContent(ctx: Context) -> str:
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Captcha"),
        ui.div("text-gray-600")("CAPTCHA component with server-side validation."),
        ui.div("bg-white p-6 rounded-lg shadow border border-gray-200 w-full")(Captcha(_on_validated).Render(ctx)),
    )


__all__ = ["CaptchaContent"]
