from __future__ import annotations

import ui
from ui_data import Collate, TField, TFieldDates, TQuery, BOOL, DATES, SELECT
from ui_server import Context
from pages.collate_data import Row, Loader

active =  TField(
    DB="Active",
    Field="Active",
    Text="Active",
    Value="",
    As=BOOL,
    Condition="",
    Options=[],
    Bool=False,
    Dates=TFieldDates(),
)

created_at = TField(
        DB="CreatedAt",
        Field="CreatedAt",
        Text="Created",
        Value="",
        As=DATES,
        Condition="",
        Options=[],
        Bool=False,
        Dates=TFieldDates(),
    )

role = TField(
        DB="Role",
        Field="Role",
        Text="Role",
        Value="",
        As=SELECT,
        Condition="",
        Options=[
            {"id": "", "value": "All"},
            {"id": "user", "value": "User"},
            {"id": "admin", "value": "Admin"},
            {"id": "manager", "value": "Manager"},
            {"id": "support", "value": "Support"},
        ],
        Bool=False,
        Dates=TFieldDates(),
    )

def CollateContent(ctx: Context) -> str:
    query = TQuery(Limit=10, Offset=0, Order="createdat desc", Search="", Filter=[])
    collate = Collate(query, Loader)
    collate.setSort([created_at])
    collate.setFilter([active, created_at, role])

    def render_row(row: Row, _index: int) -> str:
        return ui.div("bg-white rounded border border-gray-200 p-3 flex items-center gap-3")(
            ui.div("w-12 text-right font-mono text-gray-500")(f"#{row.ID}"),
            ui.div("flex-1")(
                ui.div("font-semibold")(
                    row.Name + ui.space + ui.div("inline text-gray-500 text-sm")(f"({row.Role})"),
                ),
                ui.div("text-gray-600 text-sm")(f"{row.Email} · {row.City}"),
            ),
            ui.div("text-gray-500 text-sm")(row.CreatedAt.strftime("%Y-%m-%d")),
            ui.div("ml-2")(
                ui.Button()
                .Class("w-20 text-center px-2 py-1 rounded")
                .Color(ui.Green if row.Active else ui.Gray)
                .Render("Active" if row.Active else "Inactive"),
            ),
        )

    collate.Row(render_row)

    card = ui.div("flex flex-col gap-4 mb-4")(
        ui.div("text-3xl font-bold")("Data Collation"),
        ui.div("text-gray-600 mb-2")("Static preview demonstrating the collate layout."),
        collate.Render(ctx),
    )

    return ui.div("flex flex-col gap-4")(card)


__all__ = ["CollateContent"]
