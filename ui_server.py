"""Python server helpers for psui.

The implementation keeps the public API surface area compatible with the
TypeScript original so the example application can be executed with the same
structure. The module intentionally avoids third-party dependencies.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import inspect
import json
import os
import secrets
import socket
import struct
import threading
import time
from dataclasses import dataclass
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

from socketserver import ThreadingMixIn

from ui import (
    Target,
    Trim,
    Normalize,
    Classes,
    script as render_script,
)


_GLOBAL_STYLE = Trim(
    """
    <style>
      .psui-required-indicator { font-weight: normal; }
      .invalid,
      select:invalid,
      textarea:invalid,
      input:invalid {
        border-bottom-width: 2px;
        border-bottom-color: #dc2626;
        border-bottom-style: dotted;
      }
      .invalid-if:has(input:invalid),
      .invalid-if:has(select:invalid),
      .invalid-if:has(textarea:invalid) {
        border-bottom-width: 2px;
        border-bottom-color: #dc2626;
        border-bottom-style: dotted;
      }
    </style>
    """
)

_DARK_STYLE = Trim(
    r"""
    <style id="psui-dark-overrides">
      html.dark { color-scheme: dark; }
      /* Override backgrounds commonly used by components and examples.
         Do not override bg-gray-200 so skeleton placeholders remain visible. */
      html.dark.bg-white, html.dark.bg-gray-100 { background-color:#111827 !important; }
      .dark .bg-white, .dark .bg-gray-100, .dark .bg-gray-50 { background-color:#111827 !important; }
      /* Text color overrides */
      .dark .text-black, .dark .text-gray-800, .dark .text-gray-700 { color:#e5e7eb !important; }
      /* Borders and placeholders for form controls */
      .dark .border-gray-300 { border-color:#374151 !important; }
      .dark input, .dark select, .dark textarea { color:#e5e7eb !important; background-color:#1f2937 !important; }
      .dark input::placeholder, .dark textarea::placeholder { color:#9ca3af !important; }
      /* Common hover bg used in nav/examples */
      .dark .hover\:bg-gray-200:hover { background-color:#374151 !important; }
    </style>
    """
)

_ERROR_PAGE = Trim(
    """
    <!DOCTYPE html>
    <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Something went wrong…</title>
        <style>
          html,body{height:100%;}
          body{margin:0;display:flex;align-items:center;justify-content:center;background:#f3f4f6;font-family:system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#111827;}
          .card{background:#fff;box-shadow:0 10px 25px rgba(0,0,0,.08);border-radius:14px;padding:28px 32px;border:1px solid rgba(0,0,0,.06);text-align:center;max-width:360px;}
          .title{font-size:20px;font-weight:600;margin-bottom:6px;}
          .sub{font-size:14px;color:#6b7280;}
        </style>
      </head>
      <body>
        <div class="card">
          <div class="title">Something went wrong…</div>
          <div class="sub">Please retry once the server finishes processing.</div>
        </div>
      </body>
    </html>
    """
)


def _resolve_awaitable(value: Any) -> Any:
    if not inspect.isawaitable(value):
        return value
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(value)
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(value)
    finally:
        new_loop.close()


def _ensure_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "ignore")
    return str(value)

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


_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_AUTORELOAD_EXTENSIONS = {".py", ".html", ".htm", ".js", ".ts", ".css", ".json"}
_AUTORELOAD_IGNORED_PARTS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


class _WebSocketConnection:
    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock
        self._lock = threading.Lock()
        self._closed = False
        try:
            self._socket.settimeout(1.0)
        except OSError:
            pass

    def send_text(self, message: str) -> bool:
        if self._closed:
            return False
        payload = message.encode("utf-8")
        return self._send_frame(0x1, payload)

    def send_json(self, message: Mapping[str, Any]) -> bool:
        try:
            text = json.dumps(message, separators=(",", ":"))
        except Exception:
            return False
        return self.send_text(text)

    def run(self) -> None:
        while not self._closed:
            try:
                frame = self._recv_frame()
            except socket.timeout:
                continue
            except OSError:
                break
            if frame is None:
                break
            opcode, payload = frame
            if opcode == 0x8:  # Close
                break
            if opcode == 0x9:  # Ping
                self._send_frame(0xA, payload)
        self._close_socket()

    def _recv_exact(self, size: int) -> bytes:
        data = b""
        while len(data) < size:
            chunk = self._socket.recv(size - len(data))
            if not chunk:
                raise OSError("Socket closed")
            data += chunk
        return data

    def _recv_frame(self) -> Optional[Tuple[int, bytes]]:
        header = self._socket.recv(2)
        if not header or len(header) < 2:
            return None
        first, second = header
        opcode = first & 0x0F
        masked = (second & 0x80) == 0x80
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask_key = b""
        if masked:
            mask_key = self._recv_exact(4)
        payload = self._recv_exact(length) if length else b""
        if masked and mask_key:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        return opcode, payload

    def _send_frame(self, opcode: int, payload: bytes) -> bool:
        if self._closed:
            return False
        header = bytearray()
        header.append(0x80 | (opcode & 0x0F))
        length = len(payload)
        if length < 126:
            header.append(length)
        elif length < (1 << 16):
            header.append(126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(127)
            header.extend(struct.pack("!Q", length))
        frame = bytes(header) + payload
        with self._lock:
            try:
                self._socket.sendall(frame)
                return True
            except OSError:
                self._close_socket()
                return False

    def _close_socket(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._socket.close()
        except OSError:
            pass


class _WebSocketManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: Dict[str, List[_WebSocketConnection]] = {}

    def register(self, session_id: str, conn: _WebSocketConnection) -> None:
        if not session_id:
            return
        with self._lock:
            self._sessions.setdefault(session_id, []).append(conn)

    def unregister(self, session_id: str, conn: _WebSocketConnection) -> None:
        if not session_id:
            return
        with self._lock:
            connections = self._sessions.get(session_id)
            if not connections:
                return
            try:
                connections.remove(conn)
            except ValueError:
                pass
            if not connections:
                self._sessions.pop(session_id, None)

    def send_patches(self, session_id: str, patches: Sequence[Dict[str, str]]) -> bool:
        if not session_id or not patches:
            return False
        with self._lock:
            targets = list(self._sessions.get(session_id, []))
        if not targets:
            return False
        message = {"type": "patch", "patches": list(patches)}
        delivered = False
        for conn in targets:
            if conn.send_json(message):
                delivered = True
            else:
                self.unregister(session_id, conn)
        return delivered

    def broadcast_reload(self) -> None:
        message = {"type": "reload"}
        with self._lock:
            sessions = {sid: list(conns) for sid, conns in self._sessions.items()}
        for session_id, connections in sessions.items():
            for conn in connections:
                if not conn.send_json(message):
                    self.unregister(session_id, conn)


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

    def Send(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> _CallBuilder:
        callable_method = self.Callable(method)
        wrapper = {"method": callable_method, "values": list(values)}
        return _CallBuilder(self, "FORM", wrapper)

    def Call(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> _CallBuilder:
        callable_method = self.Callable(method)
        wrapper = {"method": callable_method, "values": list(values)}
        return _CallBuilder(self, POST, wrapper)

    def Submit(self, method: Callable[["Context"], str], *values: Mapping[str, Any]) -> _SubmitBuilder:
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
        target_id = str(target.get("id", "") or "")
        swap = str(target.get("swap", "inline") or "inline")

        try:
            resolved = html() if callable(html) else html
        except Exception:
            resolved = None

        try:
            resolved = _resolve_awaitable(resolved)
        except Exception:
            resolved = None

        html_text = _ensure_text(resolved)
        html_json = json.dumps(html_text)

        script = Trim(
            f"""
            <script>(function(){{
                try {{
                    var el=document.getElementById('{target_id}');
                    if(!el) {{ try {{ if(window.__psuiPatch&&window.__psuiPatch.notifyInvalid){{ window.__psuiPatch.notifyInvalid('{target_id}'); }} }} catch(_{{}}){{}}; return; }}
                    var html={html_json};
                    if('{swap}'==='inline') {{ el.innerHTML = html; }}
                    else if('{swap}'==='outline') {{ el.outerHTML = html; }}
                    else if('{swap}'==='append') {{ el.insertAdjacentHTML('beforeend', html); }}
                    else if('{swap}'==='prepend') {{ el.insertAdjacentHTML('afterbegin', html); }}
                }} catch(_{{}}){{}}
            }})();</script>
            """
        )
        self.append.append(script)

        session_id = str(self.sessionID or "")
        if target_id and session_id:
            self.app._queue_patch(
                session_id,
                {"id": target_id, "swap": swap, "html": html_text},
                clear,
            )
        elif clear:
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

    def Stop(self) -> str:
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

    def Stop(self) -> Dict[str, str]:
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
        self.HTMLHead.append(_GLOBAL_STYLE)
        self.HTMLHead.append(script([
            _STRINGIFY,
            _LOADER,
            _OFFLINE,
            _ERROR,
            _POST,
            _SUBMIT,
            _LOAD,
            _PATCH,
            _THEME,
        ]))
        self.HTMLHead.append(_DARK_STYLE)
        self._routes: Dict[Tuple[ActionType, str], Callable[[Context], str]] = {}
        self._debug = False
        self._patch_lock = threading.Lock()
        self._pending_patches: Dict[str, List[Dict[str, str]]] = {}
        self._patch_clear: Dict[Tuple[str, str], Callable[[], None]] = {}
        self._ws_manager = _WebSocketManager()
        self._autoreload_enabled = False
        self._autoreload_thread: Optional[threading.Thread] = None
        self._autoreload_event = threading.Event()
        self._autoreload_watch: List[Path] = [Path.cwd()]
        self._autoreload_last_signal = 0.0

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
        enable = bool(enable)
        self._autoreload_enabled = enable
        if enable:
            if self._autoreload_thread and self._autoreload_thread.is_alive():
                return
            self._autoreload_event.clear()
            self._autoreload_thread = threading.Thread(
                target=self._autoreload_worker,
                name="psui-autoreload",
                daemon=True,
            )
            self._autoreload_thread.start()
            if self._debug:
                print("[p-sui] AutoReload enabled (watching for changes)")
        else:
            self._autoreload_event.set()
            thread = self._autoreload_thread
            if thread and thread.is_alive():
                thread.join(timeout=0.5)
            self._autoreload_thread = None
            if self._debug:
                print("[p-sui] AutoReload disabled")

    def _autoreload_worker(self) -> None:
        try:
            previous = self._snapshot_files()
        except Exception:
            previous = {}
        while not self._autoreload_event.wait(1.0):
            try:
                current = self._snapshot_files()
            except Exception:
                continue
            if self._files_changed(previous, current):
                previous = current
                self._trigger_reload()

    def _snapshot_files(self) -> Dict[str, float]:
        snapshot: Dict[str, float] = {}
        for root in self._autoreload_watch:
            try:
                base = Path(root)
            except Exception:
                continue
            if not base.exists():
                continue
            try:
                iterator = base.rglob("*")
            except Exception:
                continue
            for path in iterator:
                try:
                    if path.is_dir():
                        continue
                except OSError:
                    continue
                if any(part in _AUTORELOAD_IGNORED_PARTS for part in path.parts):
                    continue
                suffix = path.suffix.lower()
                if suffix and suffix not in _AUTORELOAD_EXTENSIONS:
                    continue
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                snapshot[str(path)] = mtime
        return snapshot

    @staticmethod
    def _files_changed(previous: Mapping[str, float], current: Mapping[str, float]) -> bool:
        if len(previous) != len(current):
            return True
        for key, value in current.items():
            if previous.get(key) != value:
                return True
        return False

    def _trigger_reload(self) -> None:
        now = time.time()
        if now - self._autoreload_last_signal < 0.5:
            return
        self._autoreload_last_signal = now
        if self._debug:
            print("[p-sui] Reloading connected clients")
        self._ws_manager.broadcast_reload()

    def _register_ws(self, session_id: str, conn: _WebSocketConnection) -> None:
        self._ws_manager.register(session_id, conn)

    def _unregister_ws(self, session_id: str, conn: _WebSocketConnection) -> None:
        self._ws_manager.unregister(session_id, conn)

    def _push_pending_patches(self, session_id: str) -> None:
        if not session_id:
            return
        with self._patch_lock:
            queued = list(self._pending_patches.get(session_id, []))
        if not queued:
            return
        if self._ws_manager.send_patches(session_id, queued):
            with self._patch_lock:
                self._pending_patches.pop(session_id, None)

    def _queue_patch(
        self,
        session_id: str,
        patch: Dict[str, str],
        clear: Optional[Callable[[], None]],
    ) -> None:
        if not session_id:
            if clear:
                try:
                    clear()
                except Exception:
                    pass
            return
        target_id = str(patch.get("id", "") or "")
        if not target_id:
            if clear:
                try:
                    clear()
                except Exception:
                    pass
            return
        with self._patch_lock:
            queue = self._pending_patches.setdefault(session_id, [])
            queue.append(
                {
                    "id": target_id,
                    "swap": str(patch.get("swap", "inline") or "inline"),
                    "html": patch.get("html", ""),
                }
            )
            if clear:
                self._patch_clear[(session_id, target_id)] = clear
        self._push_pending_patches(session_id)

    def _drain_patches(self, session_id: str) -> List[Dict[str, str]]:
        if not session_id:
            return []
        with self._patch_lock:
            return list(self._pending_patches.pop(session_id, []))

    def _clear_patch_target(self, session_id: str, target_id: str) -> None:
        if not session_id or not target_id:
            return
        key = (session_id, target_id)
        callback: Optional[Callable[[], None]]
        with self._patch_lock:
            callback = self._patch_clear.pop(key, None)
        if callback:
            try:
                callback()
            except Exception:
                pass

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
        result = _resolve_awaitable(callable_fn(ctx))
        text = _ensure_text(result)
        if ctx.append:
            text += "".join(ctx.append)
        return text

    def Listen(self, port: int = 1422) -> None:
        app = self

        class _Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _handle(self, method: ActionType) -> None:
                parsed = urlparse(self.path)
                path = _normalize_path(parsed.path)
                body_items: Optional[List[BodyItem]] = None
                payload = b""
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
                if body_items is not None and path not in {"/_psui/invalid"}:
                    _REQUEST_BODIES[id(self)] = body_items
                set_cookie_header: str | None = None
                try:
                    # Session cookie management (simplified)
                    cookies = SimpleCookie(self.headers.get("Cookie", ""))
                    sid = cookies.get("psui__sid")
                    if sid is None:
                        sid_value = "sess-" + secrets.token_hex(8)
                        set_cookie_header = f"psui__sid={sid_value}; Path=/; HttpOnly; SameSite=Lax"
                        self._psui_session_id = sid_value
                    else:
                        self._psui_session_id = sid.value

                    upgrade_header = (self.headers.get("Upgrade", "") or "").lower()

                    if path == "/_psui/ws" and upgrade_header == "websocket":
                        if method != GET:
                            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
                            return
                        key = self.headers.get("Sec-WebSocket-Key", "")
                        if not key:
                            self.send_error(HTTPStatus.BAD_REQUEST)
                            return
                        accept_src = (key + _WS_GUID).encode("utf-8")
                        accept_token = base64.b64encode(hashlib.sha1(accept_src).digest()).decode("utf-8")
                        self.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
                        if set_cookie_header:
                            self.send_header("Set-Cookie", set_cookie_header)
                        self.send_header("Upgrade", "websocket")
                        self.send_header("Connection", "Upgrade")
                        self.send_header("Sec-WebSocket-Accept", accept_token)
                        self.end_headers()
                        try:
                            self.wfile.flush()
                        except Exception:
                            pass
                        session = getattr(self, "_psui_session_id", "")
                        connection = _WebSocketConnection(self.connection)
                        app._register_ws(session, connection)
                        try:
                            app._push_pending_patches(session)
                            connection.run()
                        finally:
                            app._unregister_ws(session, connection)
                            self.close_connection = True
                        return

                    if path == "/_psui/patch":
                        if method != GET:
                            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
                            return
                        patches = app._drain_patches(getattr(self, "_psui_session_id", ""))
                        body = json.dumps({"patches": patches}).encode("utf-8")
                        self.send_response(HTTPStatus.OK)
                        if set_cookie_header:
                            self.send_header("Set-Cookie", set_cookie_header)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self.send_header("Cache-Control", "no-store")
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        try:
                            self.wfile.write(body)
                        except (BrokenPipeError, ConnectionResetError):
                            pass
                        return

                    if path == "/_psui/invalid":
                        if method != POST:
                            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)
                            return
                        target_id = ""
                        if payload:
                            try:
                                data = json.loads(payload.decode("utf-8"))
                                if isinstance(data, Mapping):
                                    target_id = str(data.get("id", "") or "")
                            except Exception:
                                target_id = ""
                        if target_id:
                            app._clear_patch_target(getattr(self, "_psui_session_id", ""), target_id)
                        self.send_response(HTTPStatus.NO_CONTENT)
                        if set_cookie_header:
                            self.send_header("Set-Cookie", set_cookie_header)
                        self.send_header("Content-Length", "0")
                        self.end_headers()
                        return

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
                except Exception as exc:  # pragma: no cover - defensive server handler
                    if app._debug:
                        try:
                            print("[p-sui] Handler error:", exc)
                        except Exception:
                            pass
                    error_body = _ERROR_PAGE.encode("utf-8")
                    self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                    if set_cookie_header:
                        self.send_header("Set-Cookie", set_cookie_header)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(error_body)))
                    self.end_headers()
                    try:
                        self.wfile.write(error_body)
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

        class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        server = _ThreadingHTTPServer(("0.0.0.0", port), _Handler)
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
            var S = { count: 0, t: 0, el: null };
            function build() {
                var overlay = document.createElement('div');
                overlay.className = 'fixed inset-0 z-50 flex items-center justify-center transition-opacity opacity-0';
                try { overlay.style.backdropFilter = 'blur(3px)'; } catch(_){ }
                try { overlay.style.webkitBackdropFilter = 'blur(3px)'; } catch(_){ }
                try { overlay.style.background = 'rgba(255,255,255,0.28)'; } catch(_){ }
                try { overlay.style.pointerEvents = 'auto'; } catch(_){ }

                var badge = document.createElement('div');
                badge.className = 'absolute top-3 left-3 flex items-center gap-2 rounded-full px-3 py-1 text-white shadow-lg ring-1 ring-white/30';
                badge.style.background = 'linear-gradient(135deg, #6366f1, #22d3ee)';
                badge.style.pointerEvents = 'auto';

                var dot = document.createElement('span');
                dot.className = 'inline-block h-2.5 w-2.5 rounded-full bg-white/95 animate-pulse';

                var label = document.createElement('span');
                label.className = 'font-semibold tracking-wide';
                label.textContent = 'Loading…';

                var sub = document.createElement('span');
                sub.className = 'ml-1 text-white/85 text-xs';
                sub.textContent = 'Please wait';
                sub.style.color = 'rgba(255,255,255,0.9)';

                badge.appendChild(dot);
                badge.appendChild(label);
                badge.appendChild(sub);

                overlay.appendChild(badge);
                document.body.appendChild(overlay);

                try { requestAnimationFrame(function(){ overlay.style.opacity = '1'; }); } catch(_){ }
                return overlay;
            }
            function start() {
                S.count = S.count + 1;
                if (S.el != null) { return { stop: stop }; }
                if (S.t) { return { stop: stop }; }
                S.t = setTimeout(function(){ S.t = 0; if (S.el == null) { S.el = build(); } }, 120);
                return { stop: stop };
            }
            function stop() {
                if (S.count > 0) { S.count = S.count - 1; }
                if (S.count !== 0) { return; }
                if (S.t) { try { clearTimeout(S.t); } catch(_){ } S.t = 0; }
                if (S.el) {
                    var el = S.el; S.el = null;
                    try { el.style.opacity = '0'; } catch(_){ }
                    setTimeout(function(){ try { if (el && el.parentNode) { el.parentNode.removeChild(el); } } catch(_){ } }, 160);
                }
            }
            return { start: start };
        })();
    })();
    """
)

_OFFLINE = Trim(
    """
    (function(){
        if ((window).__offline) return;
        var __offline = (function(){
            var el = null;
            function show(){
                var existing = document.getElementById('__offline__');
                if (existing) { el = existing; return; }
                try { document.body.classList.add('pointer-events-none'); } catch(_){ }
                var overlay = document.createElement('div');
                overlay.id = '__offline__';
                overlay.style.position = 'fixed';
                overlay.style.inset = '0';
                overlay.style.zIndex = '60';
                overlay.style.pointerEvents = 'none';
                overlay.style.opacity = '0';
                overlay.style.transition = 'opacity 160ms ease-out';
                try { overlay.style.backdropFilter = 'blur(2px)'; } catch(_){ }
                try { overlay.style.webkitBackdropFilter = 'blur(2px)'; } catch(_){ }
                try { overlay.style.background = 'rgba(255,255,255,0.18)'; } catch(_){ }

                var badge = document.createElement('div');
                badge.className = 'absolute top-3 left-3 flex items-center gap-2 rounded-full px-3 py-1 text-white shadow-lg ring-1 ring-white/30';
                badge.style.background = 'linear-gradient(135deg, #ef4444, #ec4899)';
                badge.style.pointerEvents = 'auto';

                var dot = document.createElement('span');
                dot.className = 'inline-block h-2.5 w-2.5 rounded-full bg-white/95 animate-pulse';

                var label = document.createElement('span');
                label.className = 'font-semibold tracking-wide';
                label.textContent = 'Offline';
                label.style.color = '#fff';

                var sub = document.createElement('span');
                sub.className = 'ml-1 text-white/85 text-xs';
                sub.textContent = 'Trying to reconnect…';
                sub.style.color = 'rgba(255,255,255,0.9)';

                badge.appendChild(dot);
                badge.appendChild(label);
                badge.appendChild(sub);

                overlay.appendChild(badge);
                document.body.appendChild(overlay);

                try { requestAnimationFrame(function(){ overlay.style.opacity = '1'; }); } catch(_){ }
                el = overlay;
            }
            function hide(){
                try { document.body.classList.remove('pointer-events-none'); } catch(_){ }
                var o = document.getElementById('__offline__');
                if (!o) { el = null; return; }
                try { o.style.opacity = '0'; } catch(_){ }
                setTimeout(function(){ try { if (o && o.parentNode) { o.parentNode.removeChild(o); } } catch(_){ } }, 150);
                el = null;
            }
            return { show: show, hide: hide };
        })();
        (window).__offline = __offline;
        try { window.addEventListener('online', function(){ try { __offline.hide(); } catch(_){ } }); } catch(_){ }
        try { window.addEventListener('offline', function(){ try { __offline.show(); } catch(_){ } }); } catch(_){ }
        try { if (typeof navigator !== 'undefined' && navigator.onLine === false) { __offline.show(); } } catch(_){ }
    })();
    """
)

_ERROR = Trim(
    """
    (function(){
        if ((window).__error) return;
        (window).__error = function(message){
            (function(){
                try {
                    var box = document.getElementById('__messages__');
                    if (box == null) {
                        box = document.createElement('div');
                        box.id = '__messages__';
                        box.style.position = 'fixed';
                        box.style.top = '0';
                        box.style.right = '0';
                        box.style.padding = '8px';
                        box.style.zIndex = '9999';
                        box.style.pointerEvents = 'none';
                        document.body.appendChild(box);
                    }
                    var n = document.getElementById('__error_toast__');
                    if (!n) {
                        n = document.createElement('div');
                        n.id = '__error_toast__';
                        n.style.display = 'flex';
                        n.style.alignItems = 'center';
                        n.style.gap = '10px';
                        n.style.padding = '12px 16px';
                        n.style.margin = '8px';
                        n.style.borderRadius = '12px';
                        n.style.minHeight = '44px';
                        n.style.minWidth = '340px';
                        n.style.maxWidth = '340px';
                        n.style.background = '#fee2e2';
                        n.style.color = '#991b1b';
                        n.style.border = '1px solid #fecaca';
                        n.style.borderLeft = '4px solid #dc2626';
                        n.style.boxShadow = '0 6px 18px rgba(0,0,0,0.08)';
                        n.style.fontWeight = '600';
                        n.style.pointerEvents = 'auto';
                        var dot = document.createElement('span');
                        dot.style.width = '10px'; dot.style.height = '10px'; dot.style.borderRadius = '9999px'; dot.style.background = '#dc2626';
                        n.appendChild(dot);
                        var span = document.createElement('span');
                        span.id = '__error_text__';
                        n.appendChild(span);
                        var btn = document.createElement('button');
                        btn.textContent = 'Reload';
                        btn.style.background = '#991b1b';
                        btn.style.color = '#fff';
                        btn.style.border = 'none';
                        btn.style.padding = '6px 10px';
                        btn.style.borderRadius = '8px';
                        btn.style.cursor = 'pointer';
                        btn.style.fontWeight = '700';
                        btn.onclick = function(){ try { window.location.reload(); } catch(_){} };
                        n.appendChild(btn);
                        box.appendChild(n);
                    }
                    var spanText = document.getElementById('__error_text__');
                    if (spanText) { spanText.textContent = message || 'Something went wrong ...'; }
                } catch (_) { try { alert(message || 'Something went wrong ...'); } catch(__){} }
            })();
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
                try { __offline.hide(); } catch(_){ }
            })
            .catch(function(){
                try { if (typeof navigator !== 'undefined' && navigator.onLine === false) { __offline.show(); } } catch(_){ }
                try { __error('Something went wrong ...'); } catch(_){}
            })
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
                try { window.history.pushState({}, doc.title, href); } catch(_) {}
                // Optional: scroll to top after navigation
                try { window.scrollTo({ top: 0, left: 0, behavior: 'instant' }); } catch(_) {}
                try { __offline.hide(); } catch(_){ }
            })
            .catch(function(){
                try { if (typeof navigator !== 'undefined' && navigator.onLine === false) { __offline.show(); } } catch(_){ }
                try { __error('Something went wrong ...'); } catch(_){}
            })
            .finally(function(){ L.stop(); });
        return false;
    }
    """
)

_PATCH = Trim(
    """
    (function(){
        if ((window).__psuiPatch) return;
        (window).__psuiPatch = (function(){
            var httpEndpoint = '/_psui/patch';
            var invalidEndpoint = '/_psui/invalid';
            var wsPath = '/_psui/ws';
            var socket = null;
            var reconnectTimer = 0;
            var retry = 0;
            var pollTimer = 0;
            var pollInterval = 1500;
            function applyPatch(patch){
                if (!patch) { return; }
                var id = String(patch.id || '');
                if (!id) { return; }
                var swap = String(patch.swap || 'inline');
                var html = String(patch.html || '');
                var el = document.getElementById(id);
                if (!el) {
                    notifyInvalid(id);
                    return;
                }
                try {
                    if (swap === 'inline') { el.innerHTML = html; }
                    else if (swap === 'outline') { el.outerHTML = html; }
                    else if (swap === 'append') { el.insertAdjacentHTML('beforeend', html); }
                    else if (swap === 'prepend') { el.insertAdjacentHTML('afterbegin', html); }
                } catch(_) { }
            }
            function applyPatches(list){
                if (!Array.isArray(list)) { return; }
                for (var i=0;i<list.length;i++) {
                    applyPatch(list[i]);
                }
            }
            function notifyInvalid(id){
                if (!id) { return; }
                try {
                    fetch(invalidEndpoint, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ id: id })
                    });
                } catch(_) { }
            }
            function handleMessage(event){
                if (!event || !event.data) { return; }
                var data = null;
                try { data = JSON.parse(event.data); }
                catch(_) { return; }
                if (!data) { return; }
                var type = String(data.type || '');
                if (type === 'patch') {
                    applyPatches(data.patches || []);
                    return;
                }
                if (type === 'reload') {
                    try { window.location.reload(); } catch(_){}
                }
            }
            function poll(){
                try {
                    fetch(httpEndpoint, { method: 'GET', headers: { 'Accept': 'application/json' } })
                        .then(function(resp){ if(!resp.ok) throw new Error('HTTP '+resp.status); return resp.json(); })
                        .then(function(data){
                            if (!data) { return; }
                            applyPatches(data.patches || []);
                        })
                        .catch(function(){});
                } catch(_) { }
            }
            function startPolling(){
                if (pollTimer) { return; }
                poll();
                pollTimer = setInterval(poll, pollInterval);
            }
            function stopPolling(){
                if (!pollTimer) { return; }
                try { clearInterval(pollTimer); } catch(_){}
                pollTimer = 0;
            }
            function cleanupSocket(){
                if (!socket) { return; }
                try {
                    socket.onopen = null;
                    socket.onmessage = null;
                    socket.onclose = null;
                    socket.onerror = null;
                } catch(_) { }
                socket = null;
            }
            function scheduleReconnect(){
                if (reconnectTimer) { return; }
                var attempt = retry;
                retry = Math.min(retry + 1, 6);
                var delay = Math.min(1200 * Math.pow(2, attempt), 10000);
                reconnectTimer = setTimeout(function(){
                    reconnectTimer = 0;
                    connect();
                }, delay);
            }
            function connect(){
                var proto = 'ws';
                try { proto = window.location.protocol === 'https:' ? 'wss' : 'ws'; } catch(_){}
                var host = '';
                try { host = window.location.host || ''; } catch(_){}
                if (!host) {
                    startPolling();
                    return;
                }
                var url = proto + '://' + host + wsPath;
                try {
                    var ws = new WebSocket(url);
                    socket = ws;
                    ws.onopen = function(){
                        retry = 0;
                        stopPolling();
                        poll();
                    };
                    ws.onmessage = handleMessage;
                    ws.onerror = function(){
                        cleanupSocket();
                        scheduleReconnect();
                        startPolling();
                    };
                    ws.onclose = function(){
                        cleanupSocket();
                        scheduleReconnect();
                        startPolling();
                    };
                } catch(_) {
                    scheduleReconnect();
                    startPolling();
                }
            }
            connect();
            startPolling();
            return { notifyInvalid: notifyInvalid, poll: poll };
        })();
    })();
    """
)

_THEME = Trim(
    """
    (function(){
        try {
            if ((window).__psuiThemeInit) { return; }
            (window).__psuiThemeInit = true;
            var doc = document.documentElement;
            function apply(mode){
                var m = mode;
                if (m === 'system') {
                    try {
                        m = (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) ? 'dark' : 'light';
                    } catch(_) { m = 'light'; }
                }
                if (m === 'dark') { try { doc.classList.add('dark'); doc.style.colorScheme = 'dark'; } catch(_){} }
                else { try { doc.classList.remove('dark'); doc.style.colorScheme = 'light'; } catch(_){} }
            }
            function set(mode){ try { localStorage.setItem('theme', mode); } catch(_){} apply(mode); }
            try { window.setTheme = set; } catch(_){ }
            try { window.toggleTheme = function(){ var dark = !!doc.classList.contains('dark'); set(dark ? 'light' : 'dark'); }; } catch(_){ }
            var init = 'system';
            try { init = localStorage.getItem('theme') || 'system'; } catch(_){ }
            apply(init);
            try {
                if (window.matchMedia) {
                    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(){
                        var stored = '';
                        try { stored = localStorage.getItem('theme') || ''; } catch(_){ }
                        if (!stored || stored === 'system') { apply('system'); }
                    });
                }
            } catch(_){ }
        } catch(_){ }
    })();
    """
)
