"""Interactive Cat_two connection settings for the local user."""

import getpass
import json
import os
import re
import stat
import sys
import tempfile
import warnings
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit, urlunsplit


class SettingsError(Exception):
    """A connection setting could not be read, validated, or saved."""


class NotConfigured(SettingsError):
    """The local user has not configured a Cat_two connection."""


def _settings_path() -> Path:
    return Path.home() / ".cat-two-codex" / "connection.json"


def _normalize_endpoint(value: str) -> str:
    invalid_url = "请输入完整的 Cat_two HTTP 或 HTTPS 网址，可包含 /mcp。"
    if (
        not isinstance(value, str)
        or not value.isascii()
        or any(ord(character) <= 32 or ord(character) == 127 for character in value)
        or any(character in value for character in "\\?#")
    ):
        raise SettingsError(invalid_url)
    try:
        url = urlsplit(value)
        hostname = url.hostname
        port = url.port
    except ValueError:
        raise SettingsError(invalid_url) from None

    host_pattern = r"\[[^\]]+\]" if url.netloc.startswith("[") else r"[A-Za-z0-9._-]+"
    if (
        url.scheme not in {"http", "https"}
        or not hostname
        or port == 0
        or not re.fullmatch(host_pattern + r"(?::[0-9]+)?", url.netloc)
    ):
        raise SettingsError(invalid_url)

    path = url.path.rstrip("/")
    if not path.endswith("/mcp"):
        path += "/mcp"
    return urlunsplit((url.scheme, url.netloc, path, "", ""))


def _validate_token(token: str) -> str:
    if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9._~+/\-]+=*", token):
        raise SettingsError("访问令牌为空或格式无效，请从 Cat_two 设置中重新复制。")
    return token


def parse_token(value: str) -> str:
    """Accept a Cat_two MCP token or its copied Bearer value."""
    token = re.sub(r"^(?:Authorization:[ \t]*)?Bearer[ \t]+", "", value.strip(), flags=re.IGNORECASE)
    if token.startswith("memos_pat_"):
        raise SettingsError("请在 Cat_two「MCP 和 API」中创建 MCP 令牌。")
    return _validate_token(token)


def load_settings() -> tuple[str, str]:
    """Read the saved MCP endpoint and access token without displaying them."""
    path = _settings_path()
    try:
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        with os.fdopen(os.open(path, flags), encoding="utf-8") as config:
            info = os.fstat(config.fileno())
            if not stat.S_ISREG(info.st_mode):
                raise SettingsError("Cat_two 连接配置必须是普通文件。")
            if os.name == "posix" and (info.st_uid != os.getuid() or info.st_mode & 0o077):
                raise SettingsError("Cat_two 连接配置需要由当前用户持有，且仅当前用户可访问。请重新配置。")
            values = json.load(config)
        if not isinstance(values, dict):
            raise SettingsError("Cat_two 连接配置格式有误，请重新配置。")
        return _normalize_endpoint(values.get("endpoint")), _validate_token(values.get("token"))
    except FileNotFoundError:
        raise NotConfigured("尚未配置 Cat_two 连接，请在本机终端运行首次配置命令。") from None
    except (OSError, ValueError):
        raise SettingsError("无法读取 Cat_two 连接配置，请重新配置。") from None


def _save_settings(endpoint: str, token: str) -> None:
    path = _settings_path()
    try:
        path.parent.mkdir(mode=0o700, exist_ok=True)
        if path.parent.is_symlink():
            raise SettingsError("Cat_two 配置目录必须位于当前用户目录内。")
        if os.name == "posix":
            info = path.parent.stat()
            if info.st_uid != os.getuid() or info.st_mode & 0o022:
                raise SettingsError("Cat_two 配置目录需要由当前用户持有，且仅当前用户可写。")
        fd, filename = tempfile.mkstemp(prefix=".connection-", dir=path.parent)
        temporary_path = Path(filename)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as config:
                json.dump({"endpoint": endpoint, "token": token}, config)
                config.write("\n")
                config.flush()
                os.fsync(config.fileno())
            temporary_path.replace(path)
        finally:
            temporary_path.unlink(missing_ok=True)
    except OSError:
        raise SettingsError("无法保存 Cat_two 连接配置，请检查用户目录的写入权限。") from None


def configure(verify: Callable[[str, str], str]) -> None:
    """Prompt for a connection, verify the account, and then save it."""
    if not sys.stdin.isatty():
        raise SettingsError("请在本机交互式终端运行配置命令。")

    endpoint = _normalize_endpoint(input("Cat_two 应用网址或 MCP 服务地址: ").strip())
    if endpoint.startswith("http://"):
        print("HTTP 会在网络上传输未加密的令牌。能通过 HTTPS 访问时，请使用 HTTPS。")
        if input("确认在可信网络中使用 HTTP？[y/N] ").strip().lower() not in {"y", "yes"}:
            raise SettingsError("已取消连接配置。")

    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            token = parse_token(getpass.getpass("Cat_two MCP 令牌（输入不会显示）: "))
        except getpass.GetPassWarning:
            raise SettingsError("此终端无法隐藏输入。请换用本机交互式终端。") from None

    account = verify(endpoint, token)
    _save_settings(endpoint, token)
    display_account = json.dumps(account.replace(token, "[已隐藏]"), ensure_ascii=False)
    print(f"已连接 Cat_two 账号 {display_account}，并保存本机配置。")
