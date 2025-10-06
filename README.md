# p-sui — Python Server‑Rendered UI

A tiny server-side UI toolkit in Python that renders HTML strings and ships a minimal HTTP server to wire routes and actions. It provides Tailwind-friendly primitives and ready-to-use components (inputs, selects, buttons, tables), plus simple AJAX‑style helpers for partial updates — no client framework required.

> Status: experimental. APIs may change while things settle.

- Minimal, dependency‑light server (`http.server`) with GET/POST routing
- HTML builder API with composable components and class utilities
- Tailwind‑compatible class strings out of the box
- Form helpers that serialize/deserialize values and post via `fetch`
- Partial updates (`Render`/`Replace`/`Append`/`Prepend`) targeting elements
- Dev autoreload via WebSocket
- Deferred fragments with skeleton placeholders (WS patches)
- Optional dark‑mode toggle (`ui.ThemeSwitcher`)

No third‑party Python dependencies are required; Tailwind is loaded via CDN in the demo shell.

## Quick Start

Prereqs: Python 3.10+

- Start the examples server:

```bash
python3 examples/main.py
```

- Open `http://127.0.0.1:1422` and try the routes:
  - `/` Showcase
  - `/button`, `/text`, `/password`, `/number`, `/date`, `/area`, `/select`, `/checkbox`, `/radio`, `/table`, `/append`, `/captcha`, `/clock`, `/collate`, `/counter`, `/deffered`, `/icons`, `/login`, `/others`

Notes:
- Default listen address: `0.0.0.0:1422` (reachable via `127.0.0.1:1422`).
- Change port by calling `run(<port>)` in `examples/main.py` (or run `python3 -c "import examples.main as m; m.run(3000)"`).
- The examples include a blue “UI” favicon embedded as a data URL. To change it, edit `examples/main.py:66` where `app.HTMLHead.append(...)` injects the SVG.

## How It Works

There are two main modules (plus optional helpers):

- `ui.py`: HTML builder and components. Exposes functions like `div`, `form`, `Button`, `IText`, `INumber`, `ISelect`, `SimpleTable`, `Skeleton`, `ThemeSwitcher`.
- `ui_server.py`: Minimal HTTP server + routing + client helpers. Provides `App`, `MakeApp`, and `Context` to register pages/actions and wire partial updates.
- `ui_data.py`: Optional data helpers (e.g., collation/paging patterns) used by examples.
- `ui_captcha.py`: Simple challenge/response CAPTCHA used by the demo.

### Sessions (Online Clients)

- The server assigns a session id and stores it in cookie `psui__sid` (`Path=/; HttpOnly; SameSite=Lax`).
- The client uses cookies only; no `sid` URL params or hidden fields are sent.
- WebSocket connects to `/_psui/ws` (no query). Browsers include cookies in the WS handshake.
- Patches are delivered over WS. When autoreload is enabled, a reload signal is also sent over WS to refresh pages on change.

Key ideas:

- Build HTML by composing functions that return strings. Use Tailwind-like class names for styling.
- Register pages with `app.Page(path, handler)` and start the server with `app.Listen(port)`.
- Use `Context` helpers to post forms or call actions and update a target element by swapping `innerHTML` (`Render`), `outerHTML` (`Replace`), or inserting (`Append`/`Prepend`).
- `AutoReload(True)` enables a WebSocket-based live-reload flag in development.
- `app.Debug(True)` enables verbose server logs (suppressed when `False`).

## Minimal Example

```python
# examples/minimal.py
from __future__ import annotations
import ui
from ui_server import MakeApp, Context

app = MakeApp("en")

def Home(_ctx: Context) -> str:
    body = ui.div("p-6 max-w-xl mx-auto bg-white rounded shadow")(
        ui.div("text-xl font-bold")("Hello from p-sui"),
        ui.div("text-gray-600")("Server-rendered UI without a client framework."),
    )
    return app.HTML("Home", "bg-gray-100 min-h-screen", body)

app.Page("/", Home)
app.AutoReload(True)
app.Listen(1422)
```

Run with `python3 examples/minimal.py` and open `http://127.0.0.1:1422`.

## Forms and Actions (Partial Updates)

- Create a target with `target = ui.Target()` and add it to an element to mark where updates go.
- Use `ctx.Submit(handler).Render(target)` or `.Replace(target)` on forms to control the swap.
- Trigger POSTs from buttons/links with `ctx.Call(handler).Render(target)` or `.Replace(target)`.

Example:

```python
import ui
from ui_server import Context

def Save(ctx: Context) -> str:
    data: dict[str, str] = {}
    ctx.Body(data)  # fills nested keys from dot paths
    ctx.Success("Saved")
    return ui.div("text-sm text-gray-600")(str(data))

def FormPage(ctx: Context) -> str:
    target = ui.Target()
    form = ui.form("flex flex-col gap-3", ctx.Submit(Save).Render(target))(
        ui.IText("User.Name").Placeholder("Your name").Render("Name"),
        ui.INumber("User.Age").Numbers(0, 120, 1).Render("Age"),
        ui.Button().Color(ui.Blue).Class("rounded").Render("Submit"),
    )
    return ui.div("max-w-md", target)(form, target.Skeleton("component"))
```

Notes:

- When passing `ui.Target()` into an element helper (e.g., `ui.div('...', target)(...)`), only the `id` renders as an attribute. Internal fields `Skeleton`, `Replace`, `Append`, `Prepend`, and `Render` are helpers for swaps.
- Swap semantics: `Render` swaps `innerHTML`, `Replace` swaps `outerHTML`, `Append` inserts at the end, and `Prepend` inserts at the beginning of the target element.
- Demo route `/append` mirrors Append/Prepend swaps and shows inserting items at either end of a container.

## Deferred Fragments (Skeletons + WS)

The `Others` page includes a deferred block that first renders a skeleton, then replaces/appends content via server patches when data is ready. Pattern (see `examples/pages/deffered.py`):

```python
def Deffered(ctx: Context) -> str:
    target = ui.Target()
    form: dict[str, str | None] = {"as": None}
    ctx.Body(form)
    ctx.Patch(target.Replace, LazyLoadData(ctx, target))   # replace skeleton
    ctx.Patch(target.Append,  LazyMoreData(ctx, target))   # append buttons
    return target.Skeleton(form["as"])                    # 'default' | 'component' | 'list' | 'page' | 'form'
```

Use the `target.Skeleton(kind)` helpers to choose a placeholder style.

## Live Updates Example (WS Clock)

The `Clock` page re-renders every second via WS patches (see `examples/pages/clock.py`).

```python
from datetime import datetime
import ui
from ui_server import Context

def Clock(ctx: Context) -> str:
    target = ui.Target()

    def fmt(d: datetime) -> str:
        return d.strftime("%H:%M:%S")

    def render(d: datetime) -> str:
        return ui.div("font-mono text-3xl", target)(fmt(d))

    def tick() -> None:
        ctx.Patch(target.Replace, render(datetime.now()), stop)

    stop = ui.Interval(1000, tick)
    return render(datetime.now())
```

Notes:

- Prefer a fresh `ui.Target()` per render so previous timers stop automatically when the old id disappears from the DOM (the `clear` callback runs via invalid-target reports).
- Use `.Stop()` on `ctx.Call(...)` when you only need side‑effects and not an immediate swap.

### Patch Cancellation (Invalid Targets)

- When the server sends a patch for a target id that no longer exists in the DOM, the client reports it to `/_psui/invalid`.
- The server calls the `clear` callback you pass as the third argument to `ctx.Patch(...)` and unregisters that id for the session. Typical usage: stop a timer that was driving updates.

## Repo Layout

```
p-sui/
├── README.md
├── LICENSE
├── ui.py           # Core builder-style UI primitives
├── ui_server.py    # Minimal HTTP server + actions/patching + WS
├── ui_data.py      # Helpers for examples
├── ui_captcha.py   # Simple CAPTCHA component
└── examples/
    ├── main.py     # Demo app entrypoint (routes, layout)
    └── pages/      # Example pages/components
        ├── hello.py, icons.py, number.py, text.py, password.py, select.py, checkbox.py, radio.py
        ├── table.py, area.py, append.py, date.py, collate.py, captcha.py
        ├── counter.py, clock.py, deffered.py, others.py, showcase.py
        └── ...
```

## Debug Logging

Enable with `app.Debug(True)` to print server logs. When disabled (default), server logs stay minimal.

## License

MIT — see `LICENSE`.

