---
name: cat-two-plugin-development
description: 在 Cat_two_accessory 仓库开发和维护 Cat_two 的 Codex 本地插件。修改 MCP 转发、首次连接、Codex @ 入口、笔记技能或 GitHub Release 时使用。
---

# 开发 Cat_two 的 Codex 插件

## 插件身份和目录

- `plugins/cat-two-notes/` 是插件根目录。`plugin.json` 和 `mcp.json` 是通用清单。`.codex-plugin/plugin.json` 和 `.mcp.json` 是 Codex 兼容清单。修改插件身份、版本、展示文案、图标或首次连接入口时，同步相应的两份清单。`mcp.json` 使用 `${PLUGIN_ROOT}` 定位运行目录，`.mcp.json` 使用相对于插件根目录的路径。
- `.agents/plugins/marketplace.json` 登记本地市场 `cat-two-accessory`，其中 `cat-two-notes` 指向 `./plugins/cat-two-notes`。安装标识为 `cat-two-notes@cat-two-accessory`，Codex 聊天框展示名为 `Cat_two 笔记`。安装后在桌面端本地会话输入 `@Cat_two` 检查搜索结果和图标。
- `extensions.com.openai.onboardingSkill` 指向插件的 `skills/cat-two-setup/SKILL.md`。连接、设置和笔记操作的用户流程分别写在插件的 `cat-two-setup` 和 `organize-notes` 技能里。改动工具名称或参数时同步检查这两个技能及 README。

## 本地配置和凭据

1. `scripts/server.py` 作为 `cat_two_local` 的 stdio MCP 进程运行，使用 Python 3.9 及以上的标准库。标准输出只写 MCP JSON 消息，诊断信息使用标准错误并省略令牌。
2. `cat_two_connection_status` 检查状态。`cat_two_open_setup` 启动 `scripts/setup_web.py` 的临时页面，绑定 `127.0.0.1`，在随机路径接收同源表单。令牌通过密码框和 POST 正文提交。首次配置和更换凭据都先调用上游 `auth_get_current_user`，验证成功才保存。检查失败后的重试和保存后监听关闭行为。
3. `scripts/settings.py` 处理 URL、令牌和连接文件。支持可达的 Docker 应用地址（默认映射端口 5230）或完整 MCP 地址，规范化时保留反代子路径。接受原始 MCP 令牌和复制的 `Authorization: Bearer …`。通过 HTTP 访问需要用户确认。
4. 用户从 Cat_two「设置 → MCP 和 API」签发 MCP 令牌。仓库、ZIP、日志和对话中都应避免记录真实令牌。当前设置用原子替换写入 `~/.cat-two-codex/connection.json`，在 POSIX 上检查文件所有者和访问权限。验证失败时保留之前的设置。终端备用入口和撤销令牌方式见 [README](../../../README.md#首次连接)。

## 上游 MCP 契约

- 插件连接 Cat_two 原生 `/mcp` 的 Streamable HTTP JSON 服务，每次请求使用 `Authorization: Bearer …`。本地转发依次执行 `initialize`、`notifications/initialized`，再使用 `tools/list` 和 `tools/call`。保持禁止重定向的行为，避免把令牌转发到其他地址。[Cat_two MCP 契约](https://github.com/Tiger-zero/Cat_two/blob/main/server/mcp/README.md#endpoint-transport--auth)
- 修改 `server.py` 中的 `NOTES_TOOLS` 前，核对上游工具的名称、输入 schema 和 `structuredContent`。转发上游实际公布的工具，保留工具注解及 `isError`。用只读令牌检查写入工具不出现在清单中，并用读写令牌验证获准的写入能力。[Cat_two 工具清单](https://github.com/Tiger-zero/Cat_two/blob/main/server/mcp/README.md#tool-surface)
- 根据上游契约选用 `memo_list_memos`、`memo_search`、`memo_get_memo`、`memo_batch_get`、`user_list_memo_views` 和标签工具。按对应分页字段传递游标并保留原筛选条件。创建或更新笔记前按 `organize-notes` 预览完整 Markdown 和目标，取得用户确认后调用 `memo_create_memo` 或 `memo_update_memo`。

## 开发验证

1. 在仓库根目录执行 `codex plugin marketplace add .` 和 `codex plugin add cat-two-notes@cat-two-accessory`。更新源目录后用 Codex 的重新安装流程刷新缓存。检查 `codex plugin list` 和桌面端 `@Cat_two` 入口。[Codex 插件文档](https://developers.openai.com/plugins/build/plugins)
2. 在隔离的本机配置和测试 Cat_two 实例中验证未配置状态、配置页成功和失败路径、已配置账号、工具发现，以及只读查询。使用测试令牌覆盖权限差异。页面验证至少覆盖 HTTP 确认、错误令牌重试、跨源 POST 拒绝、无令牌回显和保存后失效。若 Codex 会话仍使用初始工具列表，新建本地会话复验。
3. 用 `python3 -B scripts/build_release.py --platform all` 构建平台 ZIP 和 SHA-256 校验文件，或用 `--platform linux-x64` 等值构建单个平台。构建器按固定摘要校验 CPython 分发包，并为成品重写两份 MCP 清单，指向包内运行时。检查产物的市场清单、图标、MCP 启动文件和运行时许可。用解压后的实际产物安装，验证 Codex 能直接启动随包运行时。新增插件文件时检查打包清单。
4. 按 [README](../../../README.md#构建发布包) 和 [Release 工作流](../../../.github/workflows/release.yml) 核对两份插件清单、`server.py` 版本、标签与 ZIP 文件名。手动构建可从 Actions 获取制品，推送版本标签则发布到 GitHub Release。发布后核对 [GitHub Releases](https://github.com/Tiger-zero/Cat_two_accessory/releases) 上的 ZIP 和校验文件。
