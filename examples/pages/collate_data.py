import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
from ui_data import LoadResult, NormalizeForSearch, TQuery

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


def Loader(query: TQuery) -> LoadResult[Row]:
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