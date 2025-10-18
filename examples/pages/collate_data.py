import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, List, Mapping, Optional, Sequence

from ui_data import BOOL, DATES, SELECT, LoadResult, NormalizeForSearch, TField, TQuery

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


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    for pattern in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    return None


def _resolve_field_value(row: Any, key: str) -> Any:
    if not key:
        return None

    # Direct attribute lookup first (dataclasses / objects).
    if hasattr(row, key):
        return getattr(row, key)

    # Try case-insensitive attribute lookups.
    lower_key = key.lower()
    upper_key = key.upper()
    camel_key = key[:1].lower() + key[1:]
    for candidate in {lower_key, upper_key, camel_key}:
        if hasattr(row, candidate):
            return getattr(row, candidate)

    # Mapping support.
    if isinstance(row, Mapping):
        if key in row:
            return row[key]
        for candidate in {lower_key, upper_key, camel_key}:
            if candidate in row:
                return row[candidate]
        for map_key, value in row.items():
            try:
                if str(map_key).lower() == lower_key:
                    return value
            except Exception:
                continue

    # Fallback to __dict__ for objects without direct attributes (dataclasses).
    data = getattr(row, "__dict__", None)
    if isinstance(data, Mapping):
        if key in data:
            return data[key]
        for attr_key, attr_value in data.items():
            try:
                if str(attr_key).lower() == lower_key:
                    return attr_value
            except Exception:
                continue
    return None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return None
    # Fallback for truthy / falsy values.
    boolean = bool(value)
    return boolean


def _apply_filters(items: Sequence[Row], filters: Sequence[TField]) -> List[Row]:
    # Only apply filters that have user-provided values.
    filtered: List[Row] = list(items)
    if not filters:
        return filtered

    for field in filters:
        key = (getattr(field, "DB", "") or getattr(field, "Field", "")).strip()
        if not key:
            continue

        if field.As == BOOL:
            desired: Optional[bool] = None
            value = (field.Value or "").strip().lower()
            if value in {"1", "true", "yes", "on"}:
                desired = True
            elif value in {"0", "false", "no", "off"}:
                desired = False
            elif getattr(field, "Bool", False):
                desired = True

            if desired is None:
                continue

            snapshot = list(filtered)
            next_rows: List[Row] = []
            for row in snapshot:
                value = _resolve_field_value(row, key)
                bool_value = _as_bool(value)
                if bool_value is not None and bool_value == desired:
                    next_rows.append(row)
            filtered = next_rows
            continue

        if field.As == SELECT:
            value = (field.Value or "").strip()
            if not value:
                continue

            filtered = [
                row
                for row in filtered
                if str(_resolve_field_value(row, key) or "").strip().lower() == value.lower()
            ]
            continue

        if field.As == DATES:
            dates = getattr(field, "Dates", None)
            date_from = _parse_date(getattr(dates, "From", None) if dates else None)
            date_to = _parse_date(getattr(dates, "To", None) if dates else None)
            if date_from is None and date_to is None:
                continue

            def within_range(row: Row) -> bool:
                value = _resolve_field_value(row, key)
                current: Optional[date]
                if isinstance(value, datetime):
                    current = value.date()
                elif isinstance(value, date):
                    current = value
                elif isinstance(value, str):
                    current = _parse_date(value)
                else:
                    current = None
                if current is None:
                    return False
                if date_from is not None and current < date_from:
                    return False
                if date_to is not None and current > date_to:
                    return False
                return True

            filtered = [row for row in filtered if within_range(row)]
            continue

    return filtered


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

    items = _apply_filters(items, query.Filter)

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
