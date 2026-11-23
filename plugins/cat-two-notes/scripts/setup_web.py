"""A short-lived loopback form for setting up the local Cat_two connection."""

import html
import re
import secrets
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

from settings import SettingsError, _normalize_endpoint, _save_settings, parse_token


SETUP_LIFETIME = 10 * 60
SOCKET_TIMEOUT = 3
MAX_BODY_BYTES = 8192

STYLE = """
  :root { color-scheme: light dark; font: 16px/1.55 system-ui, sans-serif; }
  body { margin: 0; background: light-dark(#f3f7f5, #151d1a); color: light-dark(#193029, #e1ede6); }
  main { box-sizing: border-box; max-width: 33rem; margin: clamp(1.5rem, 10vh, 6rem) auto;
    padding: clamp(1.25rem, 5vw, 2.5rem); background: light-dark(#fff, #1c2823);
    border: 1px solid light-dark(#d8e4de, #3a4c43); border-radius: 1rem; }
  h1 { margin: 0 0 0.5rem; color: inherit; font-size: 1.6rem; }
  p { margin: 0 0 1.25rem; }
  p:last-child { margin-bottom: 0; }
  label { display: block; margin-top: 1rem; font-weight: 600; }
  input, button { font: inherit; }
  input[type="url"], input[type="password"] { box-sizing: border-box; width: 100%;
    padding: 0.55rem 0.65rem; border: 1px solid light-dark(#829a8c, #8da498);
    color: inherit; background: light-dark(#fff, #151d1a); border-radius: 0.4rem; }
  input[type="checkbox"] { margin: 0.2rem 0 0; }
  label.check { display: flex; align-items: flex-start; gap: 0.5rem; font-size: 0.9rem; font-weight: 400; }
  button { margin-top: 1.25rem; padding: 0.6rem 1rem; border: 1px solid transparent;
    border-radius: 0.4rem; color: light-dark(#fff, #101e17); background: light-dark(#21664b, #9be0ba);
    cursor: pointer; font-weight: 600; }
  a { color: light-dark(#21664b, #9be0ba); }
  :focus-visible { outline: 2px solid light-dark(#21664b, #9be0ba); outline-offset: 2px; }
  .error { color: light-dark(#912e29, #ffc1b9); }
  .account { overflow-wrap: anywhere; }
"""

FORM = """
  <p>在 Cat_two 的「设置 → MCP 和 API」中创建 MCP 访问令牌。</p>
  <form method="post" autocomplete="off">
    <label for="url">Cat_two 应用网址或 MCP 地址</label>
    <input id="url" name="url" type="url" placeholder="http://localhost:5230" required maxlength="2048">
    <label for="token">MCP 访问令牌</label>
    <input id="token" name="token" type="password" required maxlength="1024" spellcheck="false">
    <label class="check"><input type="checkbox" name="allow_http" value="yes">
      <span>仅在可信网络中使用 HTTP。HTTP 会以明文传输令牌。</span></label>
    <button type="submit">验证并保存连接</button>
  </form>
"""


class SetupWeb:
    """Open or reuse a private setup URL on the current user's machine."""

    def __init__(self, verify, install_url=None):
        self.verify = verify
        self.install_url = install_url
        self._lock = threading.Lock()
        self._server = None

    def open(self) -> str:
        with self._lock:
            if self._server is not None and self._server.active():
                return self._server.url
            try:
                server = _SetupServer(self)
            except OSError:
                raise SettingsError("无法打开本机配置页，请使用终端配置。") from None
            self._server = server
            try:
                threading.Thread(target=server.run, daemon=True, name="cat-two-setup").start()
            except RuntimeError:
                server.server_close()
                self._server = None
                raise SettingsError("无法启动本机配置页，请使用终端配置。") from None
            return server.url

    def wait(self) -> bool:
        """Wait for the current page to save its settings or expire."""
        with self._lock:
            server = self._server
        if server is None:
            return False
        # Leave time to send the final response if a save finishes just before expiry.
        server.finished.wait(max(0, server.deadline - time.monotonic()) + SOCKET_TIMEOUT)
        with self._lock:
            return server.saved

    def _save(self, server, endpoint, token):
        account = self.verify(endpoint, token)
        with self._lock:
            if self._server is not server or not server.active():
                raise SettingsError("配置页已过期，请重新打开配置页。")
            _save_settings(endpoint, token)
            server.saved = True
        return account


class _SetupServer(HTTPServer):
    timeout = 1

    def __init__(self, owner):
        self.owner = owner
        self.path = "/setup/" + secrets.token_urlsafe(32)
        self.deadline = time.monotonic() + SETUP_LIFETIME
        self.saved = False
        self.finished = threading.Event()
        super().__init__(("127.0.0.1", 0), _SetupHandler)
        self.host = f"127.0.0.1:{self.server_port}"
        self.origin = f"http://{self.host}"
        self.url = self.origin + self.path

    def active(self):
        return not self.saved and not self.finished.is_set() and time.monotonic() < self.deadline

    def run(self):
        try:
            while self.active():
                self.handle_request()
        finally:
            self.server_close()
            self.finished.set()

    def get_request(self):
        connection, address = super().get_request()
        connection.settimeout(SOCKET_TIMEOUT)
        return connection, address

    def handle_error(self, request, client_address):
        # Keep local setup requests and exceptions out of MCP process logs.
        pass


class _SetupHandler(BaseHTTPRequestHandler):
    server_version = "CatTwoSetup"
    sys_version = ""

    def log_message(self, format, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self._page(code, "本机配置页不可用", "<p>请重新打开配置页。</p>")

    def _page(self, status, title, body):
        nonce = secrets.token_urlsafe(18)
        page = (
            '<!doctype html><html lang="zh-CN"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title><style nonce="{nonce}">{STYLE}</style>'
            f'<body><main><h1>{title}</h1>{body}</main></body></html>'
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(page)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", (
            f"default-src 'none'; style-src 'nonce-{nonce}'; form-action 'self'; "
            "base-uri 'none'; frame-ancestors 'none'"
        ))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(page)

    def _check_route(self):
        if self.path != self.server.path or self.headers.get_all("Host") != [self.server.host]:
            self.send_error(HTTPStatus.NOT_FOUND)
            return False
        if not self.server.active():
            self.send_error(HTTPStatus.GONE)
            return False
        return True

    def do_GET(self):
        if self._check_route():
            self._page(HTTPStatus.OK, "连接 Cat_two", FORM)

    def do_POST(self):
        if not self._check_route():
            return
        if self.headers.get_all("Origin") != [self.server.origin]:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        length = self.headers.get_all("Content-Length", [])
        if (
            self.headers.get("Transfer-Encoding") is not None
            or self.headers.get_content_type() != "application/x-www-form-urlencoded"
            or len(length) != 1
            or not re.fullmatch(r"[0-9]{1,4}", length[0])
            or not 0 < int(length[0]) <= MAX_BODY_BYTES
        ):
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        token = ""
        try:
            body = self.rfile.read(int(length[0]))
            if len(body) != int(length[0]):
                raise ValueError("Incomplete request body")
            fields = parse_qs(
                body.decode("ascii"), keep_blank_values=True,
                strict_parsing=True, errors="strict", max_num_fields=3,
            )
            address, = fields["url"]
            value, = fields["token"]
            endpoint = _normalize_endpoint(address.strip())
            token = parse_token(value.strip())
            if endpoint.startswith("http://") and fields.get("allow_http") != ["yes"]:
                raise SettingsError("请选择 HTTPS 地址，或确认在可信网络中使用 HTTP。")
            account = self.server.owner._save(self.server, endpoint, token)
        except (KeyError, ValueError, OSError):
            self._form_error("无法读取连接设置，请重新输入。")
        except SettingsError as error:
            self._form_error(str(error).replace(token, "[已隐藏]") if token else str(error))
        else:
            account = html.escape(account.replace(token, "[已隐藏]")[:512])
            install_url = self.server.owner.install_url
            install_link = (
                f'<p><a href="{html.escape(install_url)}">在 Codex 中安装本地插件</a></p>'
                if install_url else ""
            )
            self._page(HTTPStatus.OK, "已连接 Cat_two", (
                f'<p class="account">当前账号 <strong>{account}</strong></p>'
                '<p>连接已保存在本机。请新开一个 Codex 会话来加载笔记工具。</p>' + install_link
            ))

    def _form_error(self, message):
        self._page(HTTPStatus.BAD_REQUEST, "连接 Cat_two", (
            f'<p class="error" role="alert">{html.escape(message)}</p>' + FORM
        ))
