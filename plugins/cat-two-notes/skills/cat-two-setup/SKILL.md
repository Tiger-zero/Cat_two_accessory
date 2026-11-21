---
name: cat-two-setup
description: 首次连接 Cat_two 笔记插件，或更换实例网址和访问令牌。
---

# 连接 Cat_two

1. 使用 `cat_two_local` 的 `cat_two_connection_status` 检查连接。已连通时显示账号。用户明确要求更换连接时，也可继续执行下面的配置。
2. 请用户在能访问 Cat_two 的本机上打开 Cat_two「设置 → MCP 和 API」，创建访问令牌。请用户自行在终端中进入 `Cat_two_accessory` 仓库根目录，运行 `python3 -B plugins/cat-two-notes/scripts/server.py configure`，按提示填写应用网址和令牌。令牌输入会隐藏。请用户把令牌留在终端输入框里。
3. 配置程序会核对账号，再将连接设置保存在用户目录。完成后请用户新开 Codex 会话，再用 `cat_two_connection_status` 验证连接和账号。收到连接错误时，根据错误核对网址、网络或令牌。缺少连接工具时，先核对本地插件是否启用及 Codex 是否可以运行 `python3`。
