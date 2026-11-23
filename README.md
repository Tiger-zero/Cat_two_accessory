# Cat_two 笔记 · Codex 本地插件

通过 MCP 连接自建的 [Cat_two](https://github.com/Tiger-zero/Cat_two)，在 Codex 中查询笔记、按标签整理待办，或在预览确认后把当前任务归档为 Markdown 笔记。

## 安装

需要支持本地插件的 Codex、Python 3.9 或更高版本，以及一台能访问 Cat_two 的电脑。请确认在该电脑上运行 `python3 --version` 和 `codex --version` 都有输出。

从 [GitHub Releases](https://github.com/Tiger-zero/Cat_two_accessory/releases) 下载 `cat-two-notes-1.0.0.zip` 并解压。进入解压出的 `cat-two-notes-1.0.0` 目录，在终端运行以下命令。用 Git 克隆仓库的用户也可以在仓库根目录运行相同命令。

```sh
codex plugin marketplace add .
codex plugin add cat-two-notes@cat-two-accessory
```

在 Codex 桌面端打开或重新加载一个**本地会话**。在聊天框中输入 `@Cat_two`，选择 **Cat_two 笔记**。已装有旧版的用户可以更新原插件目录后重新安装。如果使用新解压目录，先移除旧的目录登记 `codex plugin marketplace remove cat-two-accessory`，再从新目录运行上述两条命令。[Codex 插件文档](https://developers.openai.com/plugins/build/plugins)

## 首次连接

1. 在插件界面选择 **Set up**，或在聊天中选择 `@Cat_two 笔记` 后发送「检查 Cat_two 连接」。首次使用时，插件会提供一个临时的本机配置页链接。
2. 在 Cat_two 打开「设置 → MCP 和 API」，创建 **MCP 令牌**。查询笔记可用只读令牌。创建或更新笔记需要读写令牌。[Cat_two MCP 文档](https://github.com/Tiger-zero/Cat_two/blob/main/server/mcp/README.md#endpoint-transport--auth)
3. 在运行 Codex 的同一台电脑上打开配置页，填写 Docker 应用地址（如 `http://192.168.1.10:5230`）或完整的 `/mcp` 地址，再粘贴 MCP 令牌。表单接受原始令牌和 `Bearer …`。通过可信局域网使用 HTTP 时，需要在表单确认后提交。
4. 页面验证账号并保存后，回到 Codex 继续。如果当前会话仍只显示连接工具，新建一个本地会话即可加载笔记工具。

更换地址或令牌时，可以在聊天中选择插件并发送「重新配置 Cat_two」。配置保存在当前用户目录下的 `~/.cat-two-codex/connection.json`。该文件在 macOS 和 Linux 上仅当前用户可读写，令牌以明文保存在文件中，避免提交或分享该文件。撤销令牌请在 Cat_two 的「MCP 和 API」中操作。

如果本机配置页无法打开，请在已解压的发布目录或仓库根目录运行终端配置命令。该命令会隐藏令牌输入。

```sh
python3 -B plugins/cat-two-notes/scripts/server.py configure
```

## 在 Codex 中使用

- `@Cat_two 笔记` 检查连接并显示最近三条笔记。
- `@Cat_two 笔记` 按已有标签汇总过去七天的未完成待办，保留来源链接。
- `@Cat_two 笔记` 把本次任务整理成 Markdown 归档草稿，先给我确认。

如果客户端使用技能命令，也可以选 `$cat-two-notes:cat-two-setup` 或 `$cat-two-notes:organize-notes`。插件在新建或修改笔记前会展示目标和完整正文，等你确认后才写入。

## 构建发布包

在源码仓库根目录运行 `python3 -B scripts/build_release.py`。`dist/` 会生成可直接解压安装的 ZIP 和对应的 SHA-256 校验文件。
