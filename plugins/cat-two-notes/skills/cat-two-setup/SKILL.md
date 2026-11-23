---
name: cat-two-setup
description: 首次连接 Cat_two 笔记插件，或更换 Docker 应用地址和 MCP 令牌。
---

# 连接 Cat_two

1. 调用 `cat_two_local` 的 `cat_two_connection_status`。已连通时显示账号。首次连接、连接失败或用户要求更换地址或令牌时，继续下一步。
2. 调用无参工具 `cat_two_open_setup`。把返回的 `setupUrl` 原样作为链接提供给用户，请用户在运行 Codex 的同一台电脑上打开。如无法点击，请复制到本机系统浏览器。请用户在 Cat_two「设置 → MCP 和 API」创建 MCP 令牌，然后在本机配置页填写 Docker 应用地址和令牌。令牌只在配置页输入。
3. 页面会验证账号并保存设置。用户告知完成后，再调用 `cat_two_connection_status` 确认账号。当前会话如果还没加载笔记工具，请用户新开 Codex 本地会话。
4. 如果链接过期，可再次调用 `cat_two_open_setup`。如果本机页面无法打开，请按仓库 README 使用终端配置方式。缺少连接工具时，核对本地插件是否启用、会话是否在本机运行，以及 Codex 是否可执行 `python3`。[安装与首次连接](https://github.com/Tiger-zero/Cat_two_accessory#首次连接)
