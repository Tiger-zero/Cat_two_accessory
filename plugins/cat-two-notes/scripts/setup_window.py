"""Native connection form for the bundled Windows runtime."""

import os
import tkinter as tk
from tkinter import ttk

from settings import SettingsError, connection_form_state, save_connection_form


class SetupWindow:
    def __init__(self, root, install_url=None):
        self.install_url = install_url
        self.install_button = None
        status = ""
        try:
            state = connection_form_state()
        except SettingsError as error:
            state = {"endpoint": "", "configured": False}
            status = str(error)

        self.endpoint = tk.StringVar(root, value=state["endpoint"])
        self.token = tk.StringVar(root)
        self.allow_http = tk.BooleanVar(root)
        self.status = tk.StringVar(root, value=status)
        self.token_hint = tk.StringVar(root)
        self.set_token_hint(state["configured"])

        root.title("Cat_two 连接设置")
        root.minsize(490, 285)
        frame = ttk.Frame(root, padding=22)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        ttk.Label(frame, text="服务端地址（应用首页或完整 /mcp 地址）").grid(row=0, column=0, sticky="w")
        self.endpoint_entry = ttk.Entry(frame, textvariable=self.endpoint, width=55)
        self.endpoint_entry.grid(row=1, column=0, sticky="ew", pady=(4, 12))
        ttk.Label(frame, text="MCP 令牌").grid(row=2, column=0, sticky="w")
        self.token_entry = ttk.Entry(frame, textvariable=self.token, show="•")
        self.token_entry.grid(row=3, column=0, sticky="ew", pady=(4, 3))
        ttk.Label(frame, textvariable=self.token_hint, wraplength=440).grid(row=4, column=0, sticky="w")
        ttk.Checkbutton(
            frame,
            text="允许在可信网络中使用 HTTP（令牌以明文传输）",
            variable=self.allow_http,
        ).grid(row=5, column=0, sticky="w", pady=(12, 6))
        ttk.Label(frame, textvariable=self.status, wraplength=440).grid(row=6, column=0, sticky="w", pady=(0, 8))

        buttons = ttk.Frame(frame)
        buttons.grid(row=7, column=0, sticky="ew")
        self.save_button = ttk.Button(buttons, text="保存", command=self.save)
        self.save_button.pack(side="left")
        if install_url:
            self.install_button = ttk.Button(buttons, text="在 Codex 中安装本地插件", command=self.install)
            self.install_button.pack(side="left", padx=(8, 0))
            if not state["configured"]:
                self.install_button.state(["disabled"])
        ttk.Button(buttons, text="关闭", command=root.destroy).pack(side="right")

        self.endpoint_entry.bind("<Return>", self.save)
        self.token_entry.bind("<Return>", self.save)
        root.bind("<Escape>", lambda event: root.destroy())
        self.endpoint_entry.focus_set()

    def set_token_hint(self, configured):
        if configured:
            self.token_hint.set("地址保持不变时，可留空以保留已保存的令牌。")
        else:
            self.token_hint.set("在 Cat_two 的「设置 → MCP 和 API」中创建令牌。")

    def save(self, event=None):
        try:
            state = save_connection_form(self.endpoint.get(), self.token.get(), self.allow_http.get())
        except SettingsError as error:
            self.status.set(str(error))
            return
        self.endpoint.set(state["endpoint"])
        self.token.set("")
        self.status.set(state["message"])
        self.set_token_hint(state["configured"])
        if self.install_button:
            self.install_button.state(["!disabled"])

    def install(self):
        try:
            os.startfile(self.install_url)
        except (AttributeError, OSError):
            self.status.set("无法打开 Codex。请在桌面版中从本地插件市场安装。")


def run_setup_window(install_url=None) -> int:
    try:
        root = tk.Tk()
    except tk.TclError:
        raise SettingsError("无法打开本机设置窗口。请在 Windows 桌面上运行设置启动器。") from None
    SetupWindow(root, install_url)
    root.mainloop()
    return 0
