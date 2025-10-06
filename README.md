# p-sui

Python server-side UI helpers (psui). The
port keeps the familiar API for building Tailwind-flavoured HTML strings
programmatically and ships with a small demo application.

## Layout

```
p-sui/
├── pyproject.toml
├── README.md
├── p-sui/
│   ├── start.py
│   ├── ui.py
│   ├── ui_server.py
│   ├── ui_data.py
│   ├── ui_captcha.py
│   └── examples/
│       ├── __init__.py
│       ├── main.py
│       └── pages/
│           ├── __init__.py
│           ├── button.py
│           ├── captcha.py
│           ├── collate.py
│           ├── login.py
│           ├── number.py
│           ├── showcase.py
│           └── text.py
```

## Getting started

Run the example server directly:

```bash
cd p-sui
python3 examples/main.py
```

The demo listens on `http://127.0.0.1:1422` by default.

## Status

- Core UI primitives (`ui.py`) implement a builder-style API.
- `ui_server.py` provides minimal HTTP handling to register pages, actions,
  and helpers such as `ctx.Call`, `ctx.Submit`, and `ctx.Load`.
- `ui_data.Collate` currently renders a static summary instead of the full
  interactive tooling. Extending it to match feature parity can build on the
  provided scaffolding.
- `ui_captcha` implements a simplified challenge/response CAPTCHA without
  the drag-and-drop interface.

The examples cover a representative subset of the original showcase while
keeping the Python code approachable.
