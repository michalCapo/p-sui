from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List

import ui
from ui_data import Collate, LoadResult, NormalizeForSearch, TField, TFieldDates, TQuery, BOOL, DATES, SELECT
from ui_server import Context


@dataclass
class Row:
    ID: int
    Name: str
    Email: str
    City: str
    Role: str
    Active: bool
    CreatedAt: datetime


_DB: List[Row] = []
_SEEDED = False


def _seed() -> None:
    global _SEEDED
    if _SEEDED:
        return
    first_names = [
        "John",
        "Jane",
        "Alex",
        "Emily",
        "Michael",
        "Sarah",
        "David",
        "Laura",
        "Chris",
        "Anna",
        "Robert",
        "Julia",
        "Daniel",
        "Mia",
        "Peter",
        "Sophia",
    ]
    last_names = [
        "Smith",
        "Johnson",
        "Brown",
        "Williams",
        "Jones",
        "Garcia",
        "Miller",
        "Davis",
        "Martinez",
        "Lopez",
        "Taylor",
        "Anderson",
        "Thomas",
        "Harris",
        "Clark",
        "Lewis",
    ]
    cities = [
        "New York",
        "San Francisco",
        "London",
        "Berlin",
        "Paris",
        "Madrid",
        "Prague",
        "Tokyo",
        "Sydney",
        "Toronto",
        "Dublin",
        "Vienna",
        "Oslo",
        "Copenhagen",
        "Warsaw",
        "Lisbon",
    ]
    roles = ["user", "admin", "manager", "support"]
    domains = ["example.com", "mail.com", "corp.local", "dev.io"]

    now = datetime.utcnow()
    for idx in range(100):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        city = random.choice(cities)
        role = random.choice(roles)
        email = f"{fn.lower()}.{ln.lower()}@{random.choice(domains)}"
        created_at = now - timedelta(days=random.randint(0, 365))
        _DB.append(
            Row(
                ID=idx + 1,
                Name=f"{fn} {ln}",
                Email=email,
                City=city,
                Role=role,
                Active=random.random() < 0.62,
                CreatedAt=created_at,
            )
        )
    _SEEDED = True


_seed()


def _build_filters() -> List[TField]:
    return [
        TField(
            DB="Active",
            Field="Active",
            Text="Active",
            Value="",
            As=BOOL,
            Condition="",
            Options=[],
            Bool=False,
            Dates=TFieldDates(),
        ),
        TField(
            DB="CreatedAt",
            Field="CreatedAt",
            Text="Created",
            Value="",
            As=DATES,
            Condition="",
            Options=[],
            Bool=False,
            Dates=TFieldDates(),
        ),
        TField(
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
        ),
    ]


def _apply_query(query: TQuery) -> LoadResult[Row]:
    items = list(_DB)
    search = (query.Search or "").strip()
    if search:
        search_norm = NormalizeForSearch(search)
        filtered = []
        for row in items:
            hay = " ".join(
                [NormalizeForSearch(row.Name), NormalizeForSearch(row.Email), NormalizeForSearch(row.City)]
            )
            if search_norm in hay:
                filtered.append(row)
        items = filtered

    # Simple order by CreatedAt desc or asc
    reverse = True
    field = "createdat"
    if query.Order:
        parts = query.Order.lower().split()
        if parts:
            field = parts[0]
        if len(parts) > 1 and parts[1] == "asc":
            reverse = False
    if field == "name":
        items.sort(key=lambda r: r.Name.lower(), reverse=reverse)
    elif field == "email":
        items.sort(key=lambda r: r.Email.lower(), reverse=reverse)
    elif field == "city":
        items.sort(key=lambda r: r.City.lower(), reverse=reverse)
    else:
        items.sort(key=lambda r: r.CreatedAt, reverse=reverse)

    total = len(_DB)
    filtered = len(items)
    offset = min(max(query.Offset, 0), filtered)
    limit = max(query.Limit, 1)
    page = items[offset : offset + limit]

    return LoadResult(total=total, filtered=filtered, data=page)


def CollateContent(ctx: Context) -> str:
    query = TQuery(Limit=10, Offset=0, Order="createdat desc", Search="", Filter=[])
    collate = Collate(query, _apply_query)
    collate.setFilter(_build_filters())

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
