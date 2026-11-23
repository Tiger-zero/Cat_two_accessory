"""Codex stdio MCP server for Cat_two's JSON Streamable HTTP transport."""

import json
import subprocess
import sys
import threading
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from settings import NotConfigured, SettingsError, configure, load_settings
from setup_web import SetupWeb


SERVER_INFO = {"name": "cat-two-notes", "version": "1.2.0"}
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
NOTES_TOOLS = {
    "auth_get_current_user",
    "user_list_memo_views",
    "memo_list_memos",
    "memo_get_memo",
    "memo_search",
    "memo_batch_get",
    "tag_search",
    "tag_tree",
    "memo_create_memo",
    "memo_update_memo",
}
SETUP_HELP = "调用 cat_two_open_setup 获取本机配置页面，在浏览器中填写 Cat_two 地址和 MCP 令牌。"
STATUS_TOOL = {
    "name": "cat_two_connection_status",
    "description": "检查本地 Cat_two 配置和当前账号。首次连接时返回本机配置页链接。",
    "inputSchema": {"type": "object", "additionalProperties": False},
    "annotations": {"readOnlyHint": True, "openWorldHint": True},
}
SETUP_TOOL = {
    "name": "cat_two_open_setup",
    "title": "添加或修改服务端",
    "description": "应用户要求打开本机浏览器的 Cat_two 配置页，用于首次连接或更换地址和令牌。令牌仅在配置页填写。",
    "inputSchema": {"type": "object", "additionalProperties": False},
    "annotations": {"readOnlyHint": True, "openWorldHint": False},
}
SETTINGS_READ_TOOL = {
    "name": "cat_two_settings_read",
    "description": "读取 Cat_two 的设置界面定义。",
    "inputSchema": {"type": "object", "additionalProperties": False},
    "outputSchema": {
        "type": "object",
        "properties": {
            "schema": {"type": "object"},
            "values": {"type": "object"},
            "layout": {"type": "array", "items": {"type": "object"}},
        },
        "required": ["schema", "values"],
    },
    "annotations": {"readOnlyHint": True, "openWorldHint": False},
    "_meta": {"ui": {"visibility": ["app"]}},
}
SETTINGS_UPDATE_TOOL = {
    "name": "cat_two_settings_update",
    "description": "处理设置界面的空更新。连接信息在本机配置页更改。",
    "inputSchema": {
        "type": "object",
        "properties": {"set": {"type": "object", "additionalProperties": False}},
        "required": ["set"],
        "additionalProperties": False,
    },
    "outputSchema": {
        "type": "object",
        "properties": {"values": {"type": "object"}},
        "required": ["values"],
    },
    "annotations": {"readOnlyHint": True, "openWorldHint": False},
    "_meta": {"ui": {"visibility": ["app"]}},
}
SETTINGS_CAPABILITIES = {"openai/settings": {
    "readTool": SETTINGS_READ_TOOL["name"],
    "updateTool": SETTINGS_UPDATE_TOOL["name"],
}}


class CatTwoError(Exception):
    """An actionable connection failure that does not contain credentials."""


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib can carry the original Authorization header across origins.
        return None


class Remote:
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token
        self.opener = build_opener(NoRedirects())
        self.version = None
        self.session = None
        self.request_id = 0

    def send(self, method, params, notification=False):
        message = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            self.request_id += 1
            message["id"] = self.request_id
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.version:
            headers["MCP-Protocol-Version"] = self.version
        if self.session:
            headers["Mcp-Session-Id"] = self.session

        request = Request(self.endpoint, json.dumps(message).encode("utf-8"), headers)
        try:
            with self.opener.open(request, timeout=10) as response:
                if notification:
                    return None
                if response.headers.get_content_type() != "application/json":
                    raise CatTwoError("Cat_two 未返回 MCP JSON，请检查应用网址和服务版本。")
                if method == "initialize":
                    self.session = response.headers.get("Mcp-Session-Id")
                limit = 32 * 1024 * 1024
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise CatTwoError("Cat_two 响应超出 32 MiB，请缩小查询范围。")
                reply = json.loads(data)
        except HTTPError as error:
            error.close()
            if 300 <= error.code < 400:
                raise CatTwoError("Cat_two 地址发生重定向，请使用最终的 MCP 服务地址。") from None
            if error.code in (401, 403):
                raise CatTwoError("Cat_two 拒绝访问，请检查令牌和账号权限。") from None
            raise CatTwoError(f"Cat_two 请求失败（HTTP {error.code}）。") from None
        except (OSError, HTTPException):
            raise CatTwoError("无法连接 Cat_two，请检查地址、网络和 HTTPS 证书。") from None
        except ValueError:
            raise CatTwoError("Cat_two 返回了无效的 MCP JSON。") from None

        if (
            not isinstance(reply, dict)
            or reply.get("jsonrpc") != "2.0"
            or reply.get("id") != self.request_id
            or not isinstance(reply.get("result"), dict)
        ):
            raise CatTwoError(f"Cat_two 未能完成 MCP 请求 {method}。")
        return reply["result"]

    def connect(self):
        result = self.send("initialize", {
            "protocolVersion": PROTOCOLS[0],
            "capabilities": {},
            "clientInfo": SERVER_INFO,
        })
        version = result.get("protocolVersion")
        if version not in PROTOCOLS:
            raise CatTwoError("Cat_two 返回了不受支持的 MCP 协议版本。")
        self.version = version
        self.send("notifications/initialized", {}, notification=True)

    def list_tools(self):
        tools = []
        seen = set()
        params = {}
        while True:
            result = self.send("tools/list", params)
            entries = result.get("tools")
            if not isinstance(entries, list):
                raise CatTwoError("Cat_two 返回了无效的 MCP 工具清单。")
            tools.extend(
                tool for tool in entries
                if isinstance(tool, dict)
                and isinstance(tool.get("name"), str)
                and tool["name"] in NOTES_TOOLS
            )
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
            if not isinstance(cursor, str) or cursor in seen:
                raise CatTwoError("Cat_two 返回了无效的工具清单分页游标。")
            seen.add(cursor)
            params = {"cursor": cursor}

    def call(self, name, arguments):
        return self.send("tools/call", {"name": name, "arguments": arguments})

    def account(self):
        result = self.call("auth_get_current_user", {})
        data = result.get("structuredContent")
        user = data.get("user") if isinstance(data, dict) else None
        name = user.get("name") if isinstance(user, dict) else None
        if result.get("isError") or not isinstance(name, str) or not name.startswith("users/") or name == "users/":
            raise CatTwoError("Cat_two 未确认当前账号，请检查访问令牌。")
        return name


def verify(endpoint, token):
    remote = Remote(endpoint, token)
    remote.connect()
    return remote.account()


def verify_setup(endpoint, token):
    try:
        return verify(endpoint, token)
    except CatTwoError as error:
        raise SettingsError(str(error)) from None


def launch_browser(url):
    try:
        # A browser launcher may write to its inherited streams. Keep that output off MCP stdio.
        subprocess.run(
            [sys.executable, "-E", "-s", "-B", "-m", "webbrowser", "-t", url],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError):
        # The setup response includes the URL for manual use.
        pass


def setup_browser():
    plugin_parent = Path(__file__).resolve().parent.parent.parent
    marketplace = plugin_parent.parent / ".agents" / "plugins" / "marketplace.json"
    install_url = None
    if plugin_parent.name == "plugins" and marketplace.is_file():
        marketplace_path = quote(str(marketplace), safe="")
        install_url = f"codex://plugins/cat-two-notes?marketplacePath={marketplace_path}"
    setup = SetupWeb(verify_setup, install_url=install_url)
    url = setup.open()
    print("请在浏览器中填写 Cat_two 地址和 MCP 令牌。", flush=True)
    print("如果浏览器没有自动打开，请在本机浏览器中打开以下链接。", flush=True)
    print(url, flush=True)
    threading.Thread(target=launch_browser, args=(url,), daemon=True).start()
    if not setup.wait():
        raise SettingsError("配置页已失效，请重新运行配置程序。")
    print("已保存 Cat_two 连接。", flush=True)


def status_result(data, is_error=False, text=None):
    return {
        "content": [{"type": "text", "text": text if text is not None else json.dumps(data, ensure_ascii=False)}],
        "structuredContent": data,
        "isError": is_error,
    }


class LocalServer:
    def __init__(self):
        self.remote = None
        self.setup = SetupWeb(verify_setup)

    def get_remote(self):
        endpoint, token = load_settings()
        if self.remote is None or (self.remote.endpoint, self.remote.token) != (endpoint, token):
            remote = Remote(endpoint, token)
            remote.connect()
            self.remote = remote
        return self.remote

    def list_tools(self):
        tools = [STATUS_TOOL, SETUP_TOOL, SETTINGS_READ_TOOL, SETTINGS_UPDATE_TOOL]
        try:
            tools.extend(self.get_remote().list_tools())
        except (SettingsError, CatTwoError):
            self.remote = None
        return {"tools": tools}

    def open_setup(self, open_browser=False, **status):
        try:
            url = self.setup.open()
        except SettingsError as error:
            return status_result({**status, "message": str(error)}, is_error=True, text=str(error))
        message = "请在运行 Codex 的同一台电脑上打开此链接，在网页中填写 Cat_two 地址和 MCP 令牌。"
        if open_browser:
            threading.Thread(target=launch_browser, args=(url,), daemon=True).start()
            message = "正在打开本机配置页。如果浏览器没有打开，请手动访问以下地址。"
        return status_result({
            **status,
            "setupUrl": url,
            "message": message,
        }, text=f"{message}\n{url}" if open_browser else None)

    def call(self, params):
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return status_result({"message": "MCP 工具参数须为对象。"}, is_error=True)
        if name == SETUP_TOOL["name"]:
            if arguments:
                return status_result({"message": "本机配置工具无需参数。"}, is_error=True)
            return self.open_setup(open_browser=True)
        if name == SETTINGS_READ_TOOL["name"]:
            if arguments:
                return status_result({"message": "读取连接设置无需参数。"}, is_error=True)
            return {"content": [], "structuredContent": {
                "schema": {"type": "object", "properties": {}},
                "values": {},
                "layout": [{
                    "kind": "group",
                    "title": "服务端连接",
                    "items": [{
                        "kind": "tool",
                        "tool": SETUP_TOOL["name"],
                        "description": "在本机浏览器填写服务端地址和 MCP 令牌。",
                    }],
                }],
            }}
        if name == SETTINGS_UPDATE_TOOL["name"]:
            if arguments != {"set": {}}:
                return status_result({"message": "请使用「添加或修改服务端」打开本机配置页。"}, is_error=True)
            return {"content": [], "structuredContent": {"values": {}}}
        if not isinstance(name, str) or (name != STATUS_TOOL["name"] and name not in NOTES_TOOLS):
            return status_result({"message": "此工具不在插件提供的笔记工具中。"}, is_error=True)
        try:
            remote = self.get_remote()
            if name == STATUS_TOOL["name"]:
                return status_result({
                    "configured": True,
                    "connected": True,
                    "account": remote.account(),
                    "baseUrl": remote.endpoint.removesuffix("/mcp"),
                })
            return remote.call(name, arguments)
        except NotConfigured:
            if name == STATUS_TOOL["name"]:
                return self.open_setup(configured=False, connected=False)
            return status_result({
                "configured": False, "connected": False, "message": SETUP_HELP,
            }, is_error=True)
        except (SettingsError, CatTwoError) as error:
            self.remote = None
            return status_result({
                "connected": False, "message": str(error),
            }, is_error=True)

    def respond(self, request):
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return {"id": None, "error": {"code": -32600, "message": "Invalid Request"}}
        if "id" not in request:
            return None
        request_id = request["id"]
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return {"id": request_id, "error": {"code": -32602, "message": "Invalid params"}}
        if method == "initialize":
            version = params.get("protocolVersion")
            result = {
                "protocolVersion": version if version in PROTOCOLS else PROTOCOLS[0],
                "capabilities": {
                    "tools": {},
                    "extensions": SETTINGS_CAPABILITIES,
                    "experimental": SETTINGS_CAPABILITIES,
                },
                "serverInfo": SERVER_INFO,
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = self.list_tools()
        elif method == "tools/call":
            result = self.call(params)
        else:
            return {"id": request_id, "error": {"code": -32601, "message": "Method not found"}}
        return {"id": request_id, "result": result}

    def run(self):
        for line in sys.stdin.buffer:
            try:
                request = json.loads(line)
            except ValueError:
                response = {"id": None, "error": {"code": -32700, "message": "Parse error"}}
            else:
                response = self.respond(request)
            if response is not None:
                print(json.dumps({"jsonrpc": "2.0", **response}), flush=True)


def main():
    args = sys.argv[1:]
    if not args:
        LocalServer().run()
        return 0
    try:
        if args == ["configure"]:
            configure(verify)
        elif args == ["setup-browser"]:
            setup_browser()
        else:
            print("Usage: python3 -B server.py [configure | setup-browser]", file=sys.stderr)
            return 2
        return 0
    except (SettingsError, CatTwoError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n已取消配置。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
