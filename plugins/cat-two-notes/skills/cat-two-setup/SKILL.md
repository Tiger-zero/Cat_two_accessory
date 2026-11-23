---
name: cat-two-setup
description: 首次连接 Cat_two 笔记插件，或更换 Docker 应用地址和 MCP 令牌。
---

# 连接 Cat_two

1. 用户点击「设置 Cat_two」进入首次引导，或明确要求修改连接时，直接调用 `cat_two_local` 的无参工具 `cat_two_open_setup`，显示 Codex 内嵌表单。用户也可在插件设置页点击「服务端连接 → 添加或修改服务端」。
2. 请用户在表单里填写 Docker 应用地址，以及在 Cat_two「设置 → MCP 和 API」创建的 MCP 令牌。更改时表单会带出已保存地址。请把令牌留在表单的密码框里。
3. 表单保存本机配置。用户首次查看或查询笔记时再连接服务端。用户若明确要求测试连接，可调用 `cat_two_connection_status`。保存后如果当前会话尚未加载笔记工具，请在桌面版「此电脑」新建会话。
4. 如果没有加载工具或表单未显示，请用户使用桌面版「此电脑」会话。Windows 用户可以解压市场包后双击 `setup-cat-two.cmd`，用独立本机窗口填写，再点击「在 Codex 中安装本地插件」。[安装与首次连接](https://github.com/Tiger-zero/Cat_two_accessory#首次连接)
