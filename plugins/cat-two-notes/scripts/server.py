"""Codex stdio MCP server for Cat_two's JSON Streamable HTTP transport."""

import json
import sys
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from settings import NotConfigured, SettingsError, configure, load_settings


SERVER_INFO = {"name": "cat-two-notes", "version": "0.1.0"}
PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
NOTES_TOOLS = {
    "auth_get_current_user",
    "user_list_memo_views",
    "memo_list_memos",
    "memo_get_memo",
    "memo_create_memo",
    "memo_update_memo",
}
SETUP_HELP = (
    "请在 Cat_two_accessory 仓库根目录运行 "
    "python3 -B plugins/cat-two-notes/scripts/server.py configure，"
    "完成后新开 Codex 会话。"
)
STATUS_TOOL = {
    "name": "cat_two_connection_status",
    "description": "检查本地 Cat_two 配置和当前账号。首次使用时会提示如何配置。",
    "inputSchema": {"type": "object", "additionalProperties": False},
    "annotations": {"readOnlyHint": True, "openWorldHint": True},
}


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


def status_result(data, is_error=False):
    return {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
        "structuredContent": data,
        "isError": is_error,
    }


class LocalServer:
    def __init__(self):
        self.remote = None

    def get_remote(self):
        endpoint, token = load_settings()
        if self.remote is None or (self.remote.endpoint, self.remote.token) != (endpoint, token):
            remote = Remote(endpoint, token)
            remote.connect()
            self.remote = remote
        return self.remote

    def list_tools(self):
        try:
            return {"tools": [STATUS_TOOL, *self.get_remote().list_tools()]}
        except (SettingsError, CatTwoError):
            self.remote = None
            return {"tools": [STATUS_TOOL]}

    def call(self, params):
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(arguments, dict):
            return status_result({"message": "MCP 工具参数须为对象。"}, is_error=True)
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
            return status_result({
                "configured": False, "connected": False, "message": SETUP_HELP,
            }, is_error=name != STATUS_TOOL["name"])
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
                "capabilities": {"tools": {}},
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
    if len(sys.argv) == 1:
        LocalServer().run()
        return 0
    if sys.argv[1:] != ["configure"]:
        print("Usage: python3 -B server.py [configure]", file=sys.stderr)
        return 2
    try:
        configure(verify)
        return 0
    except (SettingsError, CatTwoError) as error:
        print(str(error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n已取消配置。", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
