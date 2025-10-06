from __future__ import annotations

import ui
from ui_server import Context
from datetime import datetime
from typing import TypedDict


class DemoForm(TypedDict):
    Name: str
    Email: str
    Phone: str
    Password: str
    Age: int
    Price: float
    Bio: str
    Gender: str
    Country: str
    Agree: bool
    BirthDate: str
    AlarmTime: str
    Meeting: str


_demo_target = ui.Target()


def ShowcaseContent(ctx: Context) -> str:
    form: DemoForm = {
        "Name": "",
        "Email": "",
        "Phone": "",
        "Password": "",
        "Age": 0,
        "Price": 0.0,
        "Bio": "",
        "Gender": "",
        "Country": "",
        "Agree": False,
        "BirthDate": datetime.now().strftime("%Y-%m-%d"),
        "AlarmTime": datetime.now().strftime("%H:%M"),
        "Meeting": datetime.now().strftime("%Y-%m-%dT%H:%M"),
    }
    return ui.div("max-w-full sm:max-w-6xl mx-auto flex flex-col gap-6 w-full")(
        ui.div("text-3xl font-bold")("Component Showcase"),
        render(ctx, form, None),
    )


def render(ctx: Context, f: DemoForm, err: Exception | None) -> str:
    def action_submit(ctx: Context) -> str:
        ctx.Body(f)
        ctx.Success("Form submitted successfully")
        return render(ctx, f, None)

    raw_countries = ["", "USA", "Slovakia", "Germany", "Japan"]
    countries: list[dict[str, str]] = []
    for x in raw_countries:
        val = "Select..."
        if x != "":
            val = x
        countries.append({"id": x, "value": val})

    genders = [
        {"id": "male", "value": "Male"},
        {"id": "female", "value": "Female"},
        {"id": "other", "value": "Other"},
    ]

    error_message = ""
    if err:
        error_message = ui.div("text-red-600 p-4 rounded text-center border-4 border-red-600 bg-white")(err.args[0] if err.args else str(err))

    return ui.div("grid gap-4 sm:gap-6 items-start w-full", _demo_target)(
        ui.form("flex flex-col gap-4 bg-white p-6 rounded-lg shadow w-full", _demo_target, ctx.Submit(action_submit).Replace(_demo_target))(
            ui.div("text-xl font-bold")("Component Showcase Form"),
            error_message,
            ui.IText("Name", f).Required().Render("Name"),
            ui.IText("Email", f).Required().Render("Email"),
            ui.IText("Phone", f).Render("Phone"),
            ui.IPassword("Password").Required().Render("Password"),
            ui.INumber("Age", f).Numbers(0, 120, 1).Render("Age"),
            ui.INumber("Price", f).Format("%.2f").Render("Price (USD)"),
            ui.IArea("Bio", f).Rows(4).Render("Short Bio"),
            ui.div("block sm:hidden")(
                ui.div("text-sm font-bold")("Gender"),
                ui.IRadio("Gender", f).Value("male").Render("Male"),
                ui.IRadio("Gender", f).Value("female").Render("Female"),
                ui.IRadio("Gender", f).Value("other").Render("Other"),
            ),
            ui.div("hidden sm:block overflow-x-auto")(
                ui.IRadioButtons("Gender", f).Options(genders).Render("Gender"),
            ),
            ui.ISelect("Country", f).Options(countries).Placeholder("Select...").Render("Country"),
            ui.ICheckbox("Agree", f).Required().Render("I agree to the terms"),
            ui.IDate("BirthDate", f).Render("Birth Date"),
            ui.ITime("AlarmTime", f).Render("Alarm Time"),
            ui.IDateTime("Meeting", f).Render("Meeting (Local)"),
            ui.div("flex gap-2 mt-2")(
                ui.Button()
                .Submit()
                .Color(ui.Blue)
                .Class("rounded")
                .Render("Submit"),
                ui.Button()
                .Reset()
                .Color(ui.Gray)
                .Class("rounded")
                .Render("Reset"),
            ),
        ),
    )


__all__ = ["ShowcaseContent"]
