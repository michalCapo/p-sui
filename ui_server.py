"""Python server helpers for psui.

The implementation keeps the public API surface area compatible with the
TypeScript original so the example application can be executed with the same
structure. The module intentionally avoids third-party dependencies.
"""

from __future__ import annotations

import json
import secrets
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from ui import (
    Target,
    Trim,
    Normalize,
    Classes,
    script as render_script,
)

ActionType = str
GET = "GET"
POST = "POST"


@dataclass
class BodyItem:
    name: str
    type: str
    value: str


_REQUEST_BODIES: Dict[int, List[BodyItem]] = {}


def RequestBody(req: BaseHTTPRequestHandler) -> Optional[List[BodyItem]]:  # type: ignore[override]
    return _REQUEST_BODIES.get(id(req))


def _normalize_method(method: str) -> ActionType:
    if method and method.upper() == POST:
        return POST
    return GET


def _normalize_path(path: str) -> str:
    value = (path or "/").strip()
    if not value.startswith("/"):
        value = "/" + value
    if not value:
        value = "/"
    return value.lower()


def _type_of(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float64"
    return "string"


def _value_to_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _coerce(value_type: str, value: str) -> Any:
    if value_type in {"date", "datetime-local", "time", "Time"}:
        return value
    if value_type in {"float64"}:
        try:
            return float(value)
        except ValueError:
            return 0.0
    if value_type in {"int", "int64", "number"}:
        try:
            return int(value, 10)
        except ValueError:
            return 0
    if value_type in {"bool", "checkbox"}:
        return value == "true"
    return value


def _set_path(obj: MutableMapping[str, Any], path: str, value: Any) -> None:
    parts = [p for p in path.split(".") if p]
    current: MutableMapping[str, Any] = obj
    for idx, part in enumerate(parts):
        if idx == len(parts) - 1:
            current[part] = value
            return
        next_value = current.get(part)
        if not isinstance(next_value, MutableMapping):
            next_value = {}
            current[part] = next_value
        current = next_value  # type: ignore[assignment]


def _display_message(ctx: "Context", message: str, color: str) -> None:
    script = Trim(
        """
        <script>(function(){
            var box=document.getElementById('__messages__');
            if(!box){
                box=document.createElement('div');
                box.id='__messages__';
                box.style.position='fixed';
                box.style.top='0';
                box.style.right='0';
                box.style.padding='8px';
                box.style.zIndex='9999';
                box.style.pointerEvents='none';
                document.body.appendChild(box);
            }
            var item=document.createElement('div');
            item.style.display='flex';
            item.style.alignItems='center';
            item.style.gap='10px';
            item.style.padding='12px 16px';
            item.style.margin='8px';
            item.style.borderRadius='12px';
            item.style.minHeight='44px';
            item.style.minWidth='320px';
            item.style.maxWidth='360px';
            item.style.boxShadow='0 6px 18px rgba(0,0,0,0.08)';
            item.style.border='1px solid';
            var text=document.createElement('span');
            text.textContent=%(message)s;
            var accent='%(color)s'.indexOf('green')>=0 ? '#16a34a' : ('%(color)s'.indexOf('red')>=0 ? '#dc2626' : '#4f46e5');
            if('%(color)s'.indexOf('green')>=0){
                item.style.background='#dcfce7';
                item.style.color='#166534';
                item.style.borderColor='#bbf7d0';
            } else if('%(color)s'.indexOf('red')>=0){
                item.style.background='#fee2e2';
                item.style.color='#991b1b';
                item.style.borderColor='#fecaca';
            } else {
                item.style.background='#eef2ff';
                item.style.color='#3730a3';
                item.style.borderColor='#e0e7ff';
            }
            item.style.borderLeft='4px solid ' + accent;
            var dot=document.createElement('span');
            dot.style.width='10px';
            dot.style.height='10px';
            dot.style.borderRadius='9999px';
            dot.style.background=accent;
            item.appendChild(dot);
            item.appendChild(text);
            box.appendChild(item);
            setTimeout(function(){ try { box.removeChild(item); } catch(_){} }, 5000);
        })();
        </script>
        """ % {"message": json.dumps(Normalize(message)), "color": color}
    )
    ctx.append.append(script)


def _target_dict(target: Any) -> Dict[str, Any]:
    if target is None:
        return {}
    if isinstance(target, Mapping):
        return dict(target)
    if hasattr(target, "id"):
        return {"id": getattr(target, "id")}
    return {}


class Context:
    def __init__(self, app: "App", handler: BaseHTTPRequestHandler, session_id: str) -> None:
        self.app = app
        self.req = handler
        self.res = handler
        self.sessionID = session_id
        self.append: List[str] = []

    def Body(self, output: MutableMapping[str, Any]) -> None:
        data = RequestBody(self.req)
        if not data:
            return
        for item in data:
            _set_path(output, item.name, _coerce(item.type, item.value))

    def Callable(self, method: Callable[["Context"], str]) -> Callable[["Context"], str]:
        return self.app.Callable(method)

    def Action(self, uid: str, action: Callable[["Context"], str]) -> Callable[["Context"], str]:
        return self.app.Action(uid, action)

    def Post(
        self,
        as_type: ActionType,
        swap: str,
        action: Dict[str, Any],
    ) -> str:
        callable_method = action.get("method")
        path = self.app.path_of(callable_method)
        if not path:
            raise ValueError("Function not registered")

        values = list(action.get("values") or [])
        body: List[BodyItem] = []

        def push_value(prefix: str, value: Any) -> None:
            if value is None:
                body.append(BodyItem(prefix, "string", ""))
                return
            if isinstance(value, (int, float, bool)):
                body.append(BodyItem(prefix, _type_of(value), _value_to_string(value)))
                return
            if isinstance(value, Mapping):
                for key, val in value.items():
                    push_value(f"{prefix}.{key}", val)
                return
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                for index, item in enumerate(value):
                    push_value(f"{prefix}.{index}", item)
                return
            body.append(BodyItem(prefix, "string", _value_to_string(value)))

        for item in values:
            if isinstance(item, Mapping):
                for key, val in item.items():
                    push_value(str(key), val)

        payload = "[]"
        if body:
            payload = json.dumps([item.__dict__ for item in body])

        target = _target_dict(action.get("target"))
        target_id = target.get("id", "")
        call = "__submit" if as_type == "FORM" else "__post"
        return Normalize(
            f"{call}(event, \"{swap}\", \"{target_id}\", \"{path}\", {payload})"
        )

    def Send(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> Any:
        callable_method = self.Callable(method)
        wrapper = {"method": callable_method, "values": list(values)}
        return _CallBuilder(self, "FORM", wrapper)

    def Call(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> Any:
        callable_method = self.Callable(method)
        wrapper = {"method": callable_method, "values": list(values)}
        return _CallBuilder(self, POST, wrapper)

    def Submit(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> Any:
        callable_method = self.Callable(method)
        wrapper = {"method": callable_method, "values": list(values)}
        return _SubmitBuilder(self, wrapper)

    def Load(self, href: str) -> Dict[str, str]:
        # Pass the DOM event so the client handler can safely prevent default
        return {"onclick": Normalize(f"return __load(event, \"{href}\")")}

    def Reload(self) -> str:
        return Normalize("<script>window.location.reload();</script>")

    def Redirect(self, href: str) -> str:
        return Normalize(f"<script>window.location.href = '{href}';</script>")

    def Success(self, message: str) -> None:
        _display_message(self, message, "bg-green-700 text-white")

    def Error(self, message: str) -> None:
        _display_message(self, message, "bg-red-700 text-white")

    def Info(self, message: str) -> None:
        _display_message(self, message, "bg-blue-700 text-white")

    def Patch(self, target: Mapping[str, str], html: Any, clear: Optional[Callable[[], None]] = None) -> None:
        if callable(html):
            html = html()
        if html is None:
            html = ""
        swap = target.get("swap", "inline")
        target_id = target.get("id", "")
        html_json = json.dumps(str(html))
        script = Trim(
            f"""
            <script>(function(){{
                try {{
                    var el=document.getElementById('{target_id}');
                    if(!el) return;
                    var html={html_json};
                    if('{swap}'==='inline') {{ el.innerHTML = html; }}
                    else if('{swap}'==='outline') {{ el.outerHTML = html; }}
                    else if('{swap}'==='append') {{ el.insertAdjacentHTML('beforeend', html); }}
                    else if('{swap}'==='prepend') {{ el.insertAdjacentHTML('afterbegin', html); }}
                }} catch(_){ { } }
            }})();</script>
            """
        )
        self.append.append(script)
        if clear:
            try:
                clear()
            except Exception:
                pass


class _CallBuilder:
    def __init__(self, ctx: Context, as_type: ActionType, payload: Dict[str, Any]) -> None:
        self._ctx = ctx
        self._as = as_type
        self._payload = payload

    def Render(self, target: Mapping[str, str]) -> str:
        return self._ctx.Post(self._as, "inline", {**self._payload, "target": _target_dict(target)})

    def Replace(self, target: Mapping[str, str]) -> str:
        return self._ctx.Post(self._as, "outline", {**self._payload, "target": _target_dict(target)})

    def Append(self, target: Mapping[str, str]) -> str:
        return self._ctx.Post(self._as, "append", {**self._payload, "target": _target_dict(target)})

    def Prepend(self, target: Mapping[str, str]) -> str:
        return self._ctx.Post(self._as, "prepend", {**self._payload, "target": _target_dict(target)})

    def NoSwap(self) -> str:
        return self._ctx.Post(self._as, "none", self._payload)


class _SubmitBuilder:
    def __init__(self, ctx: Context, payload: Dict[str, Any]) -> None:
        self._ctx = ctx
        self._payload = payload

    def _attr(self, swap: str, target: Optional[Mapping[str, str]]) -> Dict[str, str]:
        return {
            "onsubmit": self._ctx.Post("FORM", swap, {**self._payload, "target": _target_dict(target)})
        }

    def Render(self, target: Mapping[str, str]) -> Dict[str, str]:
        return self._attr("inline", target)

    def Replace(self, target: Mapping[str, str]) -> Dict[str, str]:
        return self._attr("outline", target)

    def Append(self, target: Mapping[str, str]) -> Dict[str, str]:
        return self._attr("append", target)

    def Prepend(self, target: Mapping[str, str]) -> Dict[str, str]:
        return self._attr("prepend", target)

    def NoSwap(self) -> Dict[str, str]:
        return self._attr("none", None)


class App:
    def __init__(self, default_language: str) -> None:
        self.contentId = Target()
        self.Language = default_language
        self.HTMLHead: List[str] = [
            '<meta charset="UTF-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
            '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/tailwindcss/2.2.19/tailwind.min.css" integrity="sha512-wnea99uKIC3TJF7v4eKk4Y+lMz2Mklv18+r4na2Gn1abDRPPOeef95xTzdwGD9e6zXJBteMIhZ1+68QC5byJZw==" crossorigin="anonymous" referrerpolicy="no-referrer" />',
        ]
        self.HTMLHead.append(script([
            _STRINGIFY,
            _LOADER,
            _ERROR,
            _POST,
            _SUBMIT,
            _LOAD,
            _THEME,
        ]))
        self._routes: Dict[Tuple[ActionType, str], Callable[[Context], str]] = {}
        self._debug = False

    def HTMLBody(self, css: str) -> str:
        css = Classes(css)
        return " ".join([
            "<!DOCTYPE html>",
            f'<html lang="{self.Language}" class="{css}">',
            "  <head>__head__</head>",
            f'  <body id="{self.contentId.id}" class="relative">__body__</body>',
            "</html>",
        ])

    def HTML(self, title: str, body_class: str, body: str) -> str:
        head = f"<title>{title}</title>" + "".join(self.HTMLHead)
        html = self.HTMLBody(body_class)
        html = html.replace("__head__", head)
        html = html.replace("__body__", body)
        return Trim(html)

    def Debug(self, enable: bool) -> None:
        self._debug = bool(enable)

    def AutoReload(self, enable: bool) -> None:
        # Auto reload requires WebSocket support in the original implementation.
        # The Python port keeps the method for API compatibility but acts as a no-op.
        if enable and self._debug:
            print("[p-sui] AutoReload is not implemented; skipping")

    def register(self, method: ActionType, path: str, callable_fn: Callable[[Context], str]) -> Callable[[Context], str]:
        key = (method, path)
        self._routes[key] = callable_fn
        setattr(callable_fn, "psui_url", path)
        return callable_fn

    def Page(self, path: str, component: Callable[[Context], str]) -> Callable[[Context], str]:
        normalized = _normalize_path(path)
        return self.register(GET, normalized, component)

    def Action(self, uid: str, action: Callable[[Context], str]) -> Callable[[Context], str]:
        if hasattr(action, "psui_url"):
            return action
        normalized = _normalize_path(uid)
        # Ensure uniqueness by appending random suffix if already registered
        while (POST, normalized) in self._routes:
            normalized = f"{normalized}-{secrets.token_hex(4)}"
        return self.register(POST, normalized, action)

    def Callable(self, callable_fn: Callable[[Context], str]) -> Callable[[Context], str]:
        existing = getattr(callable_fn, "psui_url", None)
        if existing:
            return callable_fn
        slug = callable_fn.__name__ or "anonymous"
        slug = slug.replace(" ", "-")
        slug = "".join(ch if ch.isalnum() or ch == '-' else '-' for ch in slug)
        path = f"/{slug}-{secrets.token_hex(4)}"
        return self.Action(path, callable_fn)

    def path_of(self, callable_fn: Callable[[Context], str]) -> Optional[str]:
        return getattr(callable_fn, "psui_url", None)

    def _dispatch(self, handler: BaseHTTPRequestHandler, method: ActionType, path: str) -> str:
        key = (method, path)
        callable_fn = self._routes.get(key)
        if callable_fn is None:
            handler.send_error(HTTPStatus.NOT_FOUND)
            return "Not found"

        # Build response body via page/component callable
        ctx = Context(self, handler, getattr(handler, "_psui_session_id", ""))
        result = callable_fn(ctx)
        if ctx.append:
            result += "".join(ctx.append)
        return result

    def Listen(self, port: int = 1422) -> None:
        app = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _handle(self, method: ActionType) -> None:
                parsed = urlparse(self.path)
                path = _normalize_path(parsed.path)
                body_items: Optional[List[BodyItem]] = None
                if method == POST:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                    payload = self.rfile.read(length) if length > 0 else b""
                    if payload:
                        try:
                            decoded = payload.decode("utf-8")
                            data = json.loads(decoded)
                            if isinstance(data, list):
                                items: List[BodyItem] = []
                                for entry in data:
                                    if not isinstance(entry, dict):
                                        continue
                                    name = str(entry.get("name", ""))
                                    typ = str(entry.get("type", ""))
                                    value = str(entry.get("value", ""))
                                    items.append(BodyItem(name, typ, value))
                                body_items = items
                        except Exception:
                            body_items = None
                if body_items is not None:
                    _REQUEST_BODIES[id(self)] = body_items
                try:
                    # Session cookie management (simplified)
                    cookies = SimpleCookie(self.headers.get("Cookie", ""))
                    sid = cookies.get("psui__sid")
                    set_cookie_header: str | None = None
                    if sid is None:
                        sid_value = "sess-" + secrets.token_hex(8)
                        set_cookie_header = f"psui__sid={sid_value}; Path=/; HttpOnly; SameSite=Lax"
                        self._psui_session_id = sid_value
                    else:
                        self._psui_session_id = sid.value

                    response = app._dispatch(self, method, path)
                    body = response.encode("utf-8")

                    self.send_response(HTTPStatus.OK)
                    if set_cookie_header:
                        self.send_header("Set-Cookie", set_cookie_header)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    try:
                        self.wfile.write(body)
                    except (BrokenPipeError, ConnectionResetError):
                        pass
                finally:
                    _REQUEST_BODIES.pop(id(self), None)

            def do_GET(self) -> None:  # noqa: N802
                self._handle(GET)

            def do_POST(self) -> None:  # noqa: N802
                self._handle(POST)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                if app._debug:
                    super().log_message(format, *args)

        server = HTTPServer(("0.0.0.0", port), _Handler)
        if self._debug:
            print(f"[p-sui] Listening on http://0.0.0.0:{port}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


def MakeApp(default_language: str) -> App:
    return App(default_language)


def script(sources: Iterable[str]) -> str:
    return render_script("".join(sources))


_STRINGIFY = Trim(
    """
    (function(){
        if ((window).__psuiStringify) return;
        (window).__psuiStringify = function stringify(value){
            try { return JSON.stringify(value); }
            catch (_) { return '[]'; }
        };
    })();
    """
)

_LOADER = Trim(
    """
    (function(){
        if ((window).__loader) return;
        (window).__loader = (function(){
            var overlay=null; var depth=0;
            function ensure(){
                if(!overlay){
                    overlay=document.createElement('div');
                    overlay.style.position='fixed';
                    overlay.style.inset='0';
                    overlay.style.display='flex';
                    overlay.style.alignItems='center';
                    overlay.style.justifyContent='center';
                    overlay.style.background='rgba(0,0,0,0.25)';
                    overlay.style.zIndex='9998';
                    overlay.style.pointerEvents='none';
                    overlay.innerHTML='<div class="bg-white dark:bg-gray-900 text-gray-800 dark:text-gray-200 px-4 py-2 rounded shadow">Loading…</div>';
                    document.body.appendChild(overlay);
                }
            }
            return {
                start: function(){ depth++; ensure(); return { stop: this.stop }; },
                stop: function(){ depth=Math.max(0, depth-1); if(depth===0 && overlay){ try { overlay.remove(); } catch(_){} overlay=null; } }
            };
        })();
    })();
    """
)

_ERROR = Trim(
    """
    (function(){
        if ((window).__error) return;
        (window).__error = function(message){
            var box=document.createElement('div');
            box.textContent=message || 'Error';
            box.style.position='fixed';
            box.style.bottom='20px';
            box.style.right='20px';
            box.style.padding='12px 16px';
            box.style.background='#fee2e2';
            box.style.color='#991b1b';
            box.style.border='1px solid #fecaca';
            box.style.borderRadius='12px';
            box.style.boxShadow='0 6px 18px rgba(0,0,0,0.08)';
            document.body.appendChild(box);
            setTimeout(function(){ try { box.remove(); } catch(_){} }, 4000);
        };
    })();
    """
)

_POST = Trim(
    """
    function __post(event, swap, target_id, path, body) {
        event.preventDefault();
        var L = __loader.start();
        try { body = body ? body.slice() : []; } catch (_) {}
        fetch(path, { method: 'POST', body: JSON.stringify(body) })
            .then(function(resp){ if(!resp.ok) throw new Error('HTTP '+resp.status); return resp.text(); })
            .then(function(html){
                var parser = new DOMParser();
                var doc = parser.parseFromString(html, 'text/html');
                var scripts = [].slice.call(doc.querySelectorAll('script'));
                for (var i=0;i<scripts.length;i++) {
                    var s=document.createElement('script');
                    s.textContent=scripts[i].textContent;
                    document.body.appendChild(s);
                }
                var target=document.getElementById(target_id);
                if(target){
                    if(swap==='inline'){ target.innerHTML = html; }
                    else if(swap==='outline'){ target.outerHTML = html; }
                    else if(swap==='append'){ target.insertAdjacentHTML('beforeend', html); }
                    else if(swap==='prepend'){ target.insertAdjacentHTML('afterbegin', html); }
                }
            })
            .catch(function(){ try { __error('Something went wrong ...'); } catch(_){} })
            .finally(function(){ L.stop(); });
    }
    """
)

_SUBMIT = Trim(
    """
    function __submit(event, swap, target_id, path, body) {
        event.preventDefault();
        var form = event.currentTarget || event.target;
        var data = [];
        if (form && form.elements) {
            for (var i=0;i<form.elements.length;i++) {
                var el=form.elements[i];
                if(!el.name) continue;
                var type=(el.type||'').toLowerCase();
                if(type==='checkbox') {
                    data.push({ name: el.name, type: 'checkbox', value: el.checked ? 'true' : 'false' });
                } else {
                    data.push({ name: el.name, type: type || 'string', value: el.value || '' });
                }
            }
        }
        try { body = body ? body.slice() : []; } catch(_){}
        Array.prototype.push.apply(data, body || []);
        return __post(event, swap, target_id, path, data);
    }
    """
)

_LOAD = Trim(
    """
    function __load(evt, href) {
        try { if (evt && evt.preventDefault) evt.preventDefault(); } catch(_) {}
        var L = __loader.start();
        fetch(href, { method: 'GET' })
            .then(function(resp){ if(!resp.ok) throw new Error('HTTP '+resp.status); return resp.text(); })
            .then(function(html){
                var doc = new DOMParser().parseFromString(html, 'text/html');
                document.title = doc.title;
                // Replace body content
                document.body.innerHTML = doc.body.innerHTML;
                // Execute any inline scripts contained in the response body
                try {
                    var scripts = [].slice.call(doc.querySelectorAll('script'));
                    for (var i=0;i<scripts.length;i++) {
                        var s=document.createElement('script');
                        s.textContent=scripts[i].textContent;
                        document.body.appendChild(s);
                    }
                } catch(_) {}
                // Optional: scroll to top after navigation
                try { window.scrollTo({ top: 0, left: 0, behavior: 'instant' }); } catch(_) {}
            })
            .catch(function(){ try { __error('Something went wrong ...'); } catch(_){} })
            .finally(function(){ L.stop(); });
        return false;
    }
    """
)

_THEME = Trim(
    """
    (function(){
        if ((window).__psuiThemeInit) return;
        (window).__psuiThemeInit = true;
        var doc = document.documentElement;
        function apply(mode){
            var m = mode;
            if(m==='system'){
                try {
                    m = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
                } catch(_) { m='light'; }
            }
            if(m==='dark'){ doc.classList.add('dark'); doc.style.colorScheme='dark'; }
            else { doc.classList.remove('dark'); doc.style.colorScheme='light'; }
        }
        function set(mode){ try { localStorage.setItem('theme', mode); } catch(_){} apply(mode); }
        window.setTheme = set;
        window.toggleTheme = function(){ var dark=doc.classList.contains('dark'); set(dark ? 'light' : 'dark'); };
        var init='system';
        try { init = localStorage.getItem('theme') || 'system'; } catch(_){}
        apply(init);
    })();
    """
)
