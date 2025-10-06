"""Simplified CAPTCHA helper for psui."""

from __future__ import annotations

import secrets
from typing import Callable, Dict, Optional

import ui
from ui_server import Context


_CAPTCHA_STORE: Dict[str, int] = {}


class CaptchaComponent:
    def __init__(self, on_validated: Callable[[Context], str]) -> None:
        self._on_validated = on_validated
        self._session_field = "captcha_session"
        self._answer_field = "captcha_answer"

    def SessionField(self, name: str) -> "CaptchaComponent":
        if name:
            self._session_field = name
        return self

    def AnswerField(self, name: str) -> "CaptchaComponent":
        if name:
            self._answer_field = name
        return self

    ArrangementField = AnswerField  # Backwards compatibility alias

    def Render(self, ctx: Context) -> str:
        target = ui.Target()
        a = secrets.randbelow(8) + 2
        b = secrets.randbelow(8) + 2
        answer = a + b
        session_id = secrets.token_hex(8)
        _CAPTCHA_STORE[session_id] = answer

        def handle_submit(sub_ctx: Context) -> str:
            data: Dict[str, object] = {}
            sub_ctx.Body(data)
            session = str(data.get(self._session_field, ""))
            value = str(data.get(self._answer_field, ""))
            expected = _CAPTCHA_STORE.get(session)
            message = ui.div("text-red-600 font-semibold")("Incorrect answer. Please try again.")
            if expected is None:
                return message
            try:
                if int(value) == expected:
                    _CAPTCHA_STORE.pop(session, None)
                    success = self._on_validated(sub_ctx)
                    return ui.div("flex flex-col gap-2", target.Replace)(
                        ui.div("text-green-600 font-semibold")("CAPTCHA passed."),
                        success,
                    )
            except ValueError:
                pass
            return ui.div("", target.Replace)(
                ui.div("text-red-600 font-semibold")("Incorrect answer. Please try again."),
            )

        form_attrs = ctx.Submit(handle_submit).Replace(target)
        return ui.div("flex flex-col gap-3")(
            ui.form("flex flex-col gap-3", form_attrs)(
                ui.div("flex items-center gap-2")(
                    ui.span("font-semibold")("Solve the challenge:"),
                    ui.span("")(f"{a} + {b} = ?"),
                ),
                ui.Hidden(self._session_field, "hidden", session_id),
                ui.IText(self._answer_field)
                    .Placeholder("Enter answer")
                    .Render("Answer"),
                ui.Button()
                    .Color(ui.Blue)
                    .Class("rounded")
                    .Render("Verify"),
            ),
            ui.div("", target)(""),
        )


def Captcha(on_validated: Callable[[Context], str]) -> CaptchaComponent:
    return CaptchaComponent(on_validated)


__all__ = ["Captcha"]
