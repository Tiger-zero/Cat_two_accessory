---
name: cat-two-setup
description: 首次连接 Cat_two 笔记插件，或更换 Docker 应用地址和 MCP 令牌。
---

# 连接 Cat_two

1. 查找并调用 `cat_two_local` 的 `cat_two_connection_status`。已连通时显示账号。首次连接时如果状态返回 `setupUrl`，直接把该地址作为链接提供给用户。需要更换地址或令牌、链接已过期、或者当前已连不上时，调用无参工具 `cat_two_open_setup` 生成链接。
2. 请用户在运行 Codex 的同一台电脑上打开链接。若链接无法点击，请复制到本机浏览器。请用户在 Cat_two「设置 → MCP 和 API」创建 MCP 令牌，然后在配置页输入 Docker 应用地址和令牌。令牌只在配置页输入。
3. 页面会验证账号并保存设置。用户确认完成后，调用 `cat_two_connection_status` 核对账号。如果当前会话仍未加载笔记工具，请用户在桌面版新建会话，将工作位置设为「此电脑」。
4. 如果会话找不到两个连接工具，只说明当前会话没有加载 MCP 工具。请用户在桌面版新建会话并选择「此电脑」。Windows 用户可以直接下载同平台市场包，解压后双击 `setup-cat-two.cmd`，先在浏览器配置，再点击「在 Codex 中安装本地插件」。发布包内置运行时。其他平台按 README 使用随包配置入口。[安装与首次连接](https://github.com/Tiger-zero/Cat_two_accessory#首次连接)
