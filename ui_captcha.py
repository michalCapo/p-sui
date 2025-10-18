"""Simplified CAPTCHA helper for psui."""

from __future__ import annotations

import secrets
import time
from typing import Callable, Dict, Optional, TypedDict

import ui
from ui_server import Context


# Constants
DEFAULT_CAPTCHA_LENGTH = 6
DEFAULT_CAPTCHA_LIFETIME = 5 * 60 * 1000  # milliseconds
CLEANUP_GRACE_PERIOD = 10 * 60 * 1000  # milliseconds
DEFAULT_CAPTCHA_ATTEMPTS = 3


class CaptchaSession(TypedDict):
    """Represents a CAPTCHA session."""
    text: str
    created_at: int
    attempts: int
    solved: bool
    expires_at: int
    max_attempts: int


class CaptchaValidationResult(TypedDict):
    """Result of CAPTCHA validation."""
    ok: bool
    error: Optional[str]


# Global session store
_CAPTCHA_SESSIONS: Dict[str, CaptchaSession] = {}


def _render_captcha_error(message: str) -> str:
    """Render a CAPTCHA error message."""
    return ui.div("text-red-600 bg-red-50 border border-red-200 rounded p-3")(
        ui.span("font-semibold block mb-1")("CAPTCHA Error"),
        ui.span("text-sm")("" + message),
    )


def _escape_js(value: str) -> str:
    """Escape a string for safe use in JavaScript."""
    out = str(value or "")
    out = out.replace("\\", "\\\\")
    out = out.replace("'", "\\'")
    out = out.replace("\r", "\\r")
    out = out.replace("\n", "\\n")
    out = out.replace("\u2028", "\\u2028")
    out = out.replace("\u2029", "\\u2029")
    out = out.replace("</", "<\\/")
    return out


def _generate_secure_id(prefix: str) -> str:
    """Generate a secure random ID with a prefix."""
    random_bytes = secrets.token_hex(8)
    return prefix + random_bytes


def _generate_secure_captcha_text(length: int) -> str:
    """Generate a secure random CAPTCHA text."""
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    safe_length = length if length > 0 else DEFAULT_CAPTCHA_LENGTH
    random_bytes = secrets.token_bytes(safe_length)
    result = ""
    for i in range(safe_length):
        idx = random_bytes[i] % len(chars)
        result += chars[idx]
    return result


def _cleanup_expired_captcha_sessions() -> None:
    """Clean up expired CAPTCHA sessions."""
    now = int(time.time() * 1000)
    keys_to_delete = []
    for key, session in _CAPTCHA_SESSIONS.items():
        if session is None:
            keys_to_delete.append(key)
            continue
        if _session_expired(session, now) or (now - session["created_at"] > CLEANUP_GRACE_PERIOD):
            keys_to_delete.append(key)
    for key in keys_to_delete:
        _CAPTCHA_SESSIONS.pop(key, None)


def _create_captcha_session(
    session_id: str,
    length: int,
    lifetime: int,
    attempt_limit: int,
) -> CaptchaSession:
    """Create a new CAPTCHA session."""
    _cleanup_expired_captcha_sessions()
    captcha_text = _generate_secure_captcha_text(length)
    lifetime_value = lifetime if lifetime > 0 else DEFAULT_CAPTCHA_LIFETIME
    attempt_value = attempt_limit if attempt_limit > 0 else DEFAULT_CAPTCHA_ATTEMPTS
    now = int(time.time() * 1000)
    session: CaptchaSession = {
        "text": captcha_text,
        "created_at": now,
        "attempts": 0,
        "solved": False,
        "expires_at": now + lifetime_value,
        "max_attempts": attempt_value,
    }
    _CAPTCHA_SESSIONS[session_id] = session
    return session


def _session_expired(session: CaptchaSession, now: int) -> bool:
    """Check if a session has expired."""
    if not session:
        return True
    if session["expires_at"] > 0:
        return now > session["expires_at"]
    return now - session["created_at"] > DEFAULT_CAPTCHA_LIFETIME


def _validate_captcha(session_id: str, arrangement: str) -> CaptchaValidationResult:
    """Validate a CAPTCHA answer."""
    if not session_id:
        return {"ok": False, "error": "CAPTCHA session missing"}
    session = _CAPTCHA_SESSIONS.get(session_id)
    if not session:
        return {"ok": False, "error": "CAPTCHA session not found"}
    now = int(time.time() * 1000)
    if _session_expired(session, now):
        _CAPTCHA_SESSIONS.pop(session_id, None)
        return {"ok": False, "error": "CAPTCHA session expired"}
    limit = session["max_attempts"] if session["max_attempts"] > 0 else DEFAULT_CAPTCHA_ATTEMPTS
    session["attempts"] += 1
    if session["attempts"] > limit:
        _CAPTCHA_SESSIONS.pop(session_id, None)
        return {"ok": False, "error": "too many CAPTCHA attempts"}
    if session["solved"]:
        return {"ok": True}
    if str(arrangement or "") == session["text"]:
        session["solved"] = True
        return {"ok": True}
    return {"ok": False}


def _shuffle_string_secure(input_str: str) -> str:
    """Shuffle a string securely using a Fisher-Yates shuffle."""
    runes = list(str(input_str or ""))
    length = len(runes)
    if length <= 1:
        return input_str
    
    for i in range(length - 1, 0, -1):
        j = _secure_random_index(i + 1)
        runes[i], runes[j] = runes[j], runes[i]
    
    shuffled = "".join(runes)
    if shuffled == input_str and _has_multiple_unique_runes(runes):
        last = length - 1
        runes[0], runes[last] = runes[last], runes[0]
        if "".join(runes) == input_str and length > 3:
            runes[1], runes[length - 2] = runes[length - 2], runes[1]
    
    return "".join(runes)


def _secure_random_index(bound: int) -> int:
    """Generate a secure random index between 0 and bound-1."""
    if bound <= 0:
        return 0
    return secrets.randbelow(bound)


def _has_multiple_unique_runes(runes: list) -> bool:
    """Check if there are multiple unique characters in the list."""
    if not runes or len(runes) <= 1:
        return False
    seen = set()
    for rune in runes:
        seen.add(rune)
        if len(seen) > 1:
            return True
    return False


class CaptchaComponent:
    """CAPTCHA component with drag-and-drop interface."""

    def __init__(self, on_validated: Callable[[Context], str]) -> None:
        """Initialize the CAPTCHA component."""
        self._on_validated = on_validated
        self._session_field_name = "captcha_session"
        self._arrangement_field_name = "captcha_arrangement"
        self._client_verified_field_name = "captcha_client_verified"
        self._character_count = 4
        self._session_lifetime = DEFAULT_CAPTCHA_LIFETIME
        self._attempt_limit = DEFAULT_CAPTCHA_ATTEMPTS

    def SessionField(self, name: str) -> "CaptchaComponent":
        """Set the session field name."""
        if name:
            self._session_field_name = name
        return self

    def ArrangementField(self, name: str) -> "CaptchaComponent":
        """Set the arrangement field name."""
        if name:
            self._arrangement_field_name = name
        return self

    def ClientVerifiedField(self, name: str) -> "CaptchaComponent":
        """Set the client verified field name."""
        if name:
            self._client_verified_field_name = name
        return self

    def Count(self, n: int) -> "CaptchaComponent":
        """Set the number of characters in the CAPTCHA."""
        if n > 0:
            self._character_count = n
        return self

    def Lifetime(self, ms: int) -> "CaptchaComponent":
        """Set the session lifetime in milliseconds."""
        if ms > 0:
            self._session_lifetime = ms
        return self

    def Attempts(self, limit: int) -> "CaptchaComponent":
        """Set the maximum number of attempts."""
        if limit > 0:
            self._attempt_limit = limit
        return self

    def SessionFieldName(self) -> str:
        """Get the session field name."""
        return self._session_field_name or "captcha_session"

    def ArrangementFieldName(self) -> str:
        """Get the arrangement field name."""
        return self._arrangement_field_name or "captcha_arrangement"

    def ClientVerifiedFieldName(self) -> str:
        """Get the client verified field name."""
        return self._client_verified_field_name or "captcha_client_verified"

    def _character_count_value(self) -> int:
        """Get the character count value."""
        if self._character_count <= 0:
            return 5
        return self._character_count

    def _lifetime_value(self) -> int:
        """Get the lifetime value."""
        if self._session_lifetime <= 0:
            return DEFAULT_CAPTCHA_LIFETIME
        return self._session_lifetime

    def _attempt_limit_value(self) -> int:
        """Get the attempt limit value."""
        if self._attempt_limit <= 0:
            return DEFAULT_CAPTCHA_ATTEMPTS
        return self._attempt_limit

    def Render(self, ctx: Optional[Context] = None) -> str:
        """Render the CAPTCHA component."""
        try:
            session_id = _generate_secure_id("captcha_session_")
        except Exception:
            return _render_captcha_error("Error generating CAPTCHA IDs")

        try:
            session = _create_captcha_session(
                session_id,
                self._character_count_value(),
                self._lifetime_value(),
                self._attempt_limit_value(),
            )
        except Exception:
            return _render_captcha_error("Error generating CAPTCHA. Please refresh the page and try again.")

        try:
            root_id = _generate_secure_id("captcha3Root_")
            tiles_id = _generate_secure_id("captcha3Tiles_")
            target_id = _generate_secure_id("captcha3Target_")
        except Exception:
            return _render_captcha_error("Error generating CAPTCHA IDs")

        success_path = ""
        try:
            if ctx and self._on_validated:
                callable_obj = ctx.Callable(self._on_validated)
                if callable_obj and hasattr(callable_obj, "url"):
                    success_path = callable_obj.url
        except Exception:
            pass

        scrambled = _shuffle_string_secure(session["text"])
        default_success = ui.div("text-green-600")("Captcha validated successfully!")
        
        script_source = f"""setTimeout(function () {{
				var root = document.getElementById('{root_id}');
				var tilesContainer = document.getElementById('{tiles_id}');
				var targetContainer = document.getElementById('{target_id}');
				var arrangementInput = root ? root.querySelector('input[name="{_escape_js(self.ArrangementFieldName())}"]') : null;
				var verifiedInput = root ? root.querySelector('input[name="{_escape_js(self.ClientVerifiedFieldName())}"]') : null;
				if (!root || !tilesContainer) {{ return; }}

				var captchaText = '{_escape_js(session["text"])}';
				var scrambled = '{_escape_js(scrambled)}';
				var successPath = '{_escape_js(success_path)}';
				var defaultSuccess = '{_escape_js(str(default_success))}';

				var solved = false;
				var tiles = scrambled ? scrambled.split('') : [];
				if (!tiles.length) {{ tiles = captchaText.split(''); }}

				var uniqueChars = Object.create(null);
				captchaText.split('').forEach(function (c) {{ uniqueChars[c] = true; }});
				if (tiles.join('') === captchaText && Object.keys(uniqueChars).length > 1) {{
					tiles = captchaText.split('').reverse();
				}}

				function renderTarget() {{
					if (!targetContainer) {{ return; }}
					// Clear container safely
					while (targetContainer.firstChild) {{
						targetContainer.removeChild(targetContainer.firstChild);
					}}
					captchaText.split('').forEach(function (char) {{
						var item = document.createElement('div');
						item.className = 'inline-flex items-center justify-center px-3 py-2 rounded border text-sm font-semibold tracking-wide uppercase';
						item.textContent = char;
						targetContainer.appendChild(item);
					}});
					targetContainer.setAttribute('aria-hidden', 'false');
				}}

				function syncHidden() {{
					if (arrangementInput) {{ arrangementInput.value = tiles.join(''); }}
					if (!solved && verifiedInput) {{ verifiedInput.value = 'false'; }}
				}}

				function updateContainerAppearance() {{
					if (!tilesContainer) {{ return; }}
					tilesContainer.classList.toggle('border-slate-300', !solved);
					tilesContainer.classList.toggle('bg-white', !solved);
					tilesContainer.classList.toggle('border-green-500', solved);
					tilesContainer.classList.toggle('bg-emerald-50', solved);
				}}

				var baseTileClass = 'cursor-move select-none inline-flex items-center justify-center w-12 px-3 py-2 rounded border border-dashed border-gray-400 bg-white text-lg font-semibold shadow-sm transition-all duration-150';
				var solvedTileClass = ' bg-green-600 text-white border-green-600 shadow-none cursor-default';

				function renderTiles() {{
					if (!tilesContainer) {{ return; }}
					// Clear container safely
					while (tilesContainer.firstChild) {{
						tilesContainer.removeChild(tilesContainer.firstChild);
					}}
					updateContainerAppearance();
					for (var i = 0; i < tiles.length; i++) {{
						var tile = document.createElement('div');
						tile.className = baseTileClass;
						tile.textContent = tiles[i];
						tile.setAttribute('data-index', String(i));
						tile.setAttribute('draggable', solved ? 'false' : 'true');
						tile.setAttribute('aria-grabbed', 'false');
						tilesContainer.appendChild(tile);
					}}
					tilesContainer.setAttribute('tabindex', '0');
					tilesContainer.setAttribute('aria-live', 'polite');
					tilesContainer.setAttribute('aria-label', 'Captcha character tiles');
					syncHidden();
				}}

				function injectSuccess(html) {{
					if (!root) {{ return; }}
					var output = (html && html.trim()) ? html : defaultSuccess;
					// Use DOMParser for safer HTML parsing if available
					try {{
						if (typeof DOMParser !== 'undefined') {{
							var parser = new DOMParser();
							var doc = parser.parseFromString(output, 'text/html');
							// Clear root safely
							while (root.firstChild) {{
								root.removeChild(root.firstChild);
							}}
							// Append parsed nodes
							while (doc.body.firstChild) {{
								root.appendChild(doc.body.firstChild);
							}}
						}} else {{
							// Fallback to innerHTML if DOMParser not available (with risk noted)
							root.innerHTML = output;
						}}
					}} catch (e) {{
						// Final fallback to text content
						root.textContent = 'CAPTCHA completed successfully!';
					}}
				}}

				function markSolved() {{
					if (solved) {{ return; }}
					solved = true;
					if (verifiedInput) {{ verifiedInput.value = 'true'; }}
					if (arrangementInput) {{ arrangementInput.value = captchaText; }}

					if (tilesContainer) {{
						var nodes = tilesContainer.children;
						for (var i = 0; i < nodes.length; i++) {{
							var node = nodes[i];
							node.className = baseTileClass + solvedTileClass;
							node.setAttribute('draggable', 'false');
						}}
					}}

					updateContainerAppearance();

					if (successPath) {{
						fetch(successPath, {{
							method: 'POST',
							credentials: 'same-origin',
							headers: {{ 'Content-Type': 'application/json' }},
							body: '[]'
						}})
							.then(function (resp) {{ if (!resp.ok) {{ throw new Error('HTTP ' + resp.status); }} return resp.text(); }})
							.then(injectSuccess)
							.catch(function () {{ injectSuccess(defaultSuccess); }});
					}} else {{
						injectSuccess(defaultSuccess);
					}}
				}}

				function checkSolved() {{
					if (tiles.join('') === captchaText) {{
						markSolved();
					}}
				}}

				tilesContainer.addEventListener('dragstart', function (event) {{
					if (solved) {{ event.preventDefault(); return; }}
					var tile = event.target && event.target.closest('[data-index]');
					if (!tile) {{ return; }}
					tile.setAttribute('aria-grabbed', 'true');
					tile.classList.add('ring-2', 'ring-blue-300');
					event.dataTransfer.effectAllowed = 'move';
					event.dataTransfer.setData('text/plain', tile.getAttribute('data-index') || '0');
				}});

				tilesContainer.addEventListener('dragover', function (event) {{
					if (solved) {{ return; }}
					event.preventDefault();
					event.dataTransfer.dropEffect = 'move';
				}});

				tilesContainer.addEventListener('drop', function (event) {{
					if (solved) {{ return; }}
					event.preventDefault();
					var payload = event.dataTransfer.getData('text/plain');
					var from = parseInt(payload, 10);
					if (isNaN(from) || from < 0 || from >= tiles.length) {{ return; }}

					var target = event.target && event.target.closest('[data-index]');
					var to = target ? parseInt(target.getAttribute('data-index') || '0', 10) : tiles.length;
					if (isNaN(to)) {{ to = tiles.length; }}
					if (to > tiles.length) {{ to = tiles.length; }}

					var char = tiles.splice(from, 1)[0];
					if (from < to) {{ to -= 1; }}
					tiles.splice(to, 0, char);

					renderTiles();
					checkSolved();
				}});

				tilesContainer.addEventListener('dragend', function (event) {{
					var tile = event.target && event.target.closest('[data-index]');
					if (tile) {{
						tile.setAttribute('aria-grabbed', 'false');
						tile.classList.remove('ring-2', 'ring-blue-300');
					}}
				}});

				tilesContainer.addEventListener('dragleave', function (event) {{
					var tile = event.target && event.target.closest('[data-index]');
					if (tile) {{
						tile.classList.remove('ring-2', 'ring-blue-300');
					}}
				}});

				renderTarget();
				renderTiles();
				checkSolved();
			}}, 250);
		"""

        return ui.div("flex flex-col items-start gap-3 w-full", {"id": root_id})(
            ui.div("")(
                ui.span("text-sm text-gray-600 mb-2")(
                    "Drag and drop the characters on the canvas until they match the sequence below.",
                ),
            ),
            ui.div("flex flex-col w-full border border-gray-300 rounded-lg")(
                ui.div("flex flex-wrap gap-2 justify-center items-center m-4", {"id": target_id})(),
                ui.div(
                    "flex flex-wrap gap-3 justify-center items-center rounded-b-lg border bg-gray-200 shadow-sm p-4 min-h-[7.5rem] transition-colors duration-300",
                    {"id": tiles_id},
                )(),
            ),
            ui.Hidden(self.SessionFieldName(), "string", session_id),
            ui.Hidden(self.ArrangementFieldName(), "string", scrambled),
            ui.Hidden(self.ClientVerifiedFieldName(), "bool", "false"),
            ui.script(script_source),
        )

    def ValidateValues(self, session_id: str, arrangement: str) -> CaptchaValidationResult:
        """Validate CAPTCHA values."""
        return _validate_captcha(session_id, arrangement)

    def Validate(self, session_id: str, arrangement: str) -> CaptchaValidationResult:
        """Validate CAPTCHA (alias for ValidateValues)."""
        return self.ValidateValues(session_id, arrangement)


def Captcha(on_validated: Callable[[Context], str]) -> CaptchaComponent:
    """Create a new CAPTCHA component."""
    return CaptchaComponent(on_validated)


__all__ = ["Captcha"]
