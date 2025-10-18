from __future__ import annotations

from typing import Callable, List, Tuple
import sys
from pathlib import Path

# Ensure we can import sibling modules in examples/pages when run as a script
_EXAMPLES_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _EXAMPLES_DIR.parent  # the p-sui folder
if str(_EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES_DIR))
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(1, str(_PROJECT_DIR))

import ui
from ui_server import Context, MakeApp
from pages.append import AppendContent
from pages.area import AreaContent
from pages.button import ButtonContent
from pages.captcha import CaptchaContent
from pages.checkbox import CheckboxContent
from pages.clock import ClockContent
from pages.collate import CollateContent
from pages.counter import CounterContent
from pages.date import DateContent
from pages.deffered import Deffered
from pages.hello import Hello
from pages.icons import Icons
from pages.login import Login
from pages.number import NumberContent
from pages.others import OthersContent
from pages.password import PasswordContent
from pages.radio import RadioContent
from pages.select import SelectContent
from pages.showcase import ShowcaseContent
from pages.table import TableContent
from pages.text import TextContent

Route = Tuple[str, str, Callable[[Context], str]]


routes: List[Route] = [
    ("/", "Showcase", ShowcaseContent),
    ("/area", "Area", AreaContent),
    ("/button", "Button", ButtonContent),
    ("/checkbox", "Checkbox", CheckboxContent),
    ("/date", "Date", DateContent),
    ("/hello", "Hello", Hello),
    ("/icons", "Icons", Icons),
    ("/login", "Login", Login),
    ("/number", "Number", NumberContent),
    ("/password", "Password", PasswordContent),
    ("/radio", "Radio", RadioContent),
    ("/select", "Select", SelectContent),
    ("/table", "Table", TableContent),
    ("/text", "Text", TextContent),
    ("/append", "Append", AppendContent),
    ("/captcha", "Captcha", CaptchaContent),
    ("/clock", "Clock", ClockContent),
    ("/collate", "Collate", CollateContent),
    ("/counter", "Counter", CounterContent),
    ("/deffered", "Deferred", Deffered),
    ("/others", "Others", OthersContent),
]

app = MakeApp("en")
app.HTMLHead.append(
    '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,'
    + ui.Normalize(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">'
        '<rect width="128" height="128" rx="24" ry="24" fill="#2563eb" stroke="#1e40af" stroke-width="6"/>'
        '<text x="50%" y="56%" dominant-baseline="middle" text-anchor="middle" font-size="80" font-weight="700" font-family="Arial, Helvetica, sans-serif" fill="#ffffff">UI</text>'
        "</svg>"
    )
    + '" />'
)


def _layout(title: str, body_fn: Callable[[Context], str]) -> Callable[[Context], str]:
    def render(ctx: Context) -> str:
        req_path = getattr(ctx.req, "path", "/") or "/"
        current_path = req_path.split("?")[0].lower()
        links = []
        for path, label, _ in routes:
            base_cls = "px-2 py-1 rounded text-sm whitespace-nowrap transition-colors"
            is_active = path == current_path
            if is_active:
                cls = (
                    base_cls
                    + " bg-blue-700 text-white hover:bg-blue-600 dark:bg-blue-600 dark:hover:bg-blue-500"
                )
            else:
                cls = base_cls + " text-gray-700 hover:bg-gray-200 dark:text-gray-200 dark:hover:bg-gray-700"
            links.append(ui.a(cls, {"href": path}, ctx.Load(path))(label))

        nav = ui.div("bg-white dark:bg-gray-900 shadow mb-6 fixed top-0 left-0 right-0 z-10")(
            ui.div("max-w-5xl mx-auto px-4 py-2 flex items-center gap-2")(
                ui.div("flex flex-wrap gap-1 overflow-auto")(" ".join(links)),
                ui.div("flex-1")(),
                ui.ThemeSwitcher("ml-auto"),
            )
        )

        content = body_fn(ctx)
        return app.HTML(
            title,
            "bg-gray-200 dark:bg-gray-900 min-h-screen",
            nav + ui.div("pt-24 max-w-5xl mx-auto px-2 py-8")(content),
        )

    return render


for path, title, handler in routes:
    app.Page(path, _layout(title, handler))

app.Debug(True)

def run(port: int = 1422) -> None:
    app.Listen(port)


if __name__ == "__main__":
    run()
