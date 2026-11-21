# Cat_two 笔记 · Codex 本地插件

在 Codex 中查询 Cat_two 笔记和保存的视图，按标签或项目整理待办，也可以预览并确认将本次任务归档为 Markdown 笔记。插件通过本机连接到 Cat_two 的 `/mcp` 接口。

## 安装

需要支持插件的 Codex、可访问的 Cat_two 实例，以及运行 Codex 时可通过 `PATH` 找到的 `python3` 命令（Python 3.9 或更高版本）。

在本仓库根目录运行以下命令。

```sh
codex plugin marketplace add .
codex plugin add cat-two-notes@cat-two-accessory
```

也可以在 Codex 桌面端打开本仓库，从本地插件目录的 **Cat_two Accessory** 来源安装 **Cat_two 笔记**。更新本仓库后，可重新安装以更新插件。[Codex 插件文档](https://developers.openai.com/codex/plugins/build)

## 首次连接

1. 登录 Cat_two，打开「设置 → MCP 和 API」，复制「MCP 服务地址」，并在「访问令牌」中创建一个新令牌。
2. 在运行 Codex 的电脑上打开终端，从本仓库根目录运行配置命令。

   ```sh
   python3 -B plugins/cat-two-notes/scripts/server.py configure
   ```

   在 Windows 上，也可用 `py -3 -B plugins/cat-two-notes/scripts/server.py configure` 运行配置程序。Codex 启动插件时仍需要能执行 `python3`。

3. 输入 Cat_two 应用网址或完整的 `/mcp` 服务地址，再粘贴令牌。终端会隐藏令牌输入。优先使用 HTTPS，只有在信任的局域网中才确认使用 HTTP。请在终端输入令牌，避免将令牌发到 Codex 对话。
4. 配置程序会通过当前账号接口验证连接。验证成功后，网址和令牌会保存在当前用户目录的 `~/.cat-two-codex/connection.json`，供后续会话读取。令牌以明文保存在该本地文件中，避免将文件提交或分享。新建 Codex 本地会话以加载笔记工具。若会话仍只显示连接检查工具，请重启 Codex。

更换实例或令牌时，再运行一次配置命令。要撤销令牌，请在 Cat_two 的「MCP 和 API」设置中撤销，并可删除本地连接文件以清除这台电脑上的配置。[Cat_two MCP 连接说明](https://github.com/Tiger-zero/Cat_two/blob/main/server/mcp/README.md#connecting-a-client)

## 使用

在 Codex 中选择 **Cat_two 笔记**，或调用 `$cat-two-notes:organize-notes`。可通过 `$cat-two-notes:cat-two-setup` 查看连接配置步骤。可以这样提问。

- 检查 Cat_two 连接，并显示当前账号和最近三条笔记。
- 按已有标签汇总 Cat_two 过去七天的未完成待办，保留来源链接。
- 把本次任务整理成 Cat_two 归档草稿，先给我确认。

创建或更新笔记前，技能会展示目标和完整正文，等你确认后再写入。NAS 地址仅在局域网可达时，请在能够访问该地址的电脑上使用 Codex 的本地会话。
