from __future__ import annotations

import ui
from ui_server import Context
from typing import TypedDict


class RadioData(TypedDict):
    Gender: str


def RadioContent(_ctx: Context) -> str:
    def card(title: str, body: str) -> str:
        return ui.div("bg-white p-4 rounded-lg shadow border border-gray-200 flex flex-col gap-3")(
            ui.div("text-sm font-bold text-gray-700")(title),
            body,
        )

    genders = [
        {"id": "male", "value": "Male"},
        {"id": "female", "value": "Female"},
        {"id": "other", "value": "Other"},
    ]

    selected: RadioData = {"Gender": "male"}

    single_radios = ui.div("flex flex-col gap-2")(
        ui.IRadio("Gender", selected).Value("male").Render("Male"),
        ui.IRadio("Gender", selected).Value("female").Render("Female"),
        ui.IRadio("Gender", selected).Value("other").Render("Other"),
    )

    radios_default = ui.IRadioButtons("Group").Options(genders).Render("Gender")
    
    group2: dict[str, str] = {"Group2": "female"}
    radios_with_selected = ui.IRadioButtons("Group2", group2).Options(genders).Render("Gender")

    validation = ui.div("flex flex-col gap-2")(
        ui.div("text-sm text-gray-700")("Required group (no selection)"),
        ui.IRadioButtons("ReqGroup")
        .Options(genders)
        .Required()
        .Render("Gender (required)"),
        ui.div("text-sm text-gray-700")(
            "Required standalone radios (no selection)",
        ),
        ui.div("flex flex-col gap-1")(
            ui.IRadio("ReqSingle").Required().Value("a").Render("Option A"),
            ui.IRadio("ReqSingle").Required().Value("b").Render("Option B"),
            ui.IRadio("ReqSingle").Required().Value("c").Render("Option C"),
        ),
    )

    sizes = ui.div("flex flex-col gap-2")(
        ui.IRadio("SizesA").Value("a").Render("Default"),
        ui.IRadio("SizesB")
        .Size(ui.SM)
        .ClassLabel("text-sm")
        .Value("b")
        .Render("Small (SM)"),
        ui.IRadio("SizesC")
        .Size(ui.XS)
        .ClassLabel("text-sm")
        .Value("c")
        .Render("Extra small (XS)"),
    )

    disabled = ui.div("flex flex-col gap-2")(
        ui.IRadio("DisA").Disabled().Value("a").Render("Disabled A"),
        ui.IRadio("DisB").Disabled().Value("b").Render("Disabled B"),
    )

    return ui.div("max-w-full sm:max-w-5xl mx-auto flex flex-col gap-6")(
        ui.div("text-3xl font-bold")("Radio"),
        ui.div("text-gray-600")(
            "Single radio inputs and grouped radio buttons with a selected state.",
        ),
        card("Standalone radios (with selection)", single_radios),
        card("Radio buttons group (no selection)", radios_default),
        card("Radio buttons group (with selection)", radios_with_selected),
        card("Sizes", sizes),
        card("Validation", validation),
        card("Disabled", disabled),
    )

