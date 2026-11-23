# Cat_two 笔记 · Codex 本地插件

通过 MCP 连接自建的 [Cat_two](https://github.com/Tiger-zero/Cat_two)，在 Codex 中查询笔记、按标签整理待办，或在预览确认后把当前任务归档为 Markdown 笔记。

## 安装

需要支持本地插件的 Codex，以及一台能访问 Cat_two 的电脑。发布 ZIP 已包含运行时，由 Codex 自动启动。安装时无需另外安装 Python、构建代码或启动 MCP 服务。

从 [GitHub Releases](https://github.com/Tiger-zero/Cat_two_accessory/releases) 下载与系统和架构对应的 ZIP。

| 系统 | x64（Intel 或 AMD） | ARM64 |
| --- | --- | --- |
| Windows | `windows-x64` | `windows-arm64` |
| macOS | `macos-x64` | `macos-arm64`（Apple 芯片） |
| Linux（glibc） | `linux-x64` | `linux-arm64` |

### Windows 本机设置与安装

1. 下载 Windows 市场包，例如 `cat-two-notes-1.1.2-windows-x64.zip`。解压整个 ZIP，双击解压目录中的 `setup-cat-two.cmd`。
2. 启动器会在默认浏览器打开临时本机配置页。填写 Docker 应用地址和 MCP 令牌，再点「验证并保存连接」。如果浏览器没有自动打开，把启动器显示的地址复制到本机浏览器。
3. 保存成功后，点「在 Codex 中安装本地插件」，在桌面版确认安装 **Cat_two 笔记**。如果系统询问是否打开 ChatGPT 或 Codex，选择打开。若链接无法打开，可以按下文从本地市场安装。
4. 在 Codex 桌面版新建会话，发送前把「工作位置」选为「此电脑」。输入 `@Cat_two`，选择 **Cat_two Accessory** 来源中的 **Cat_two 笔记**。保留解压目录，供 Codex 读取本地市场。[Codex 工作位置说明](https://learn.chatgpt.com/docs/environments/modes)

### 在 Codex「创建插件」中上传

选择文件名以 `-plugin.zip` 结尾的单插件包。例如 Windows x64 使用 `cat-two-notes-1.1.2-windows-x64-plugin.zip`。在 Codex 打开「插件 → 添加 → 创建插件」，选择该 ZIP 后点「添加插件」。上传时直接选择 ZIP 文件。

单插件包的 `plugin.json` 位于 ZIP 根目录。如果上传提示 `Expected a single plugin archive`，检查文件名末尾是否为 `-plugin.zip`。上传后看到 `@Cat_two` 表示 Codex 已加载插件信息。连接工具需要桌面版「此电脑」会话。会话里仍缺少工具时，按上面的 Windows 本机步骤或以下市场步骤安装。

### 从本地插件市场安装

选择文件名为 `cat-two-notes-版本-平台.zip` 的市场包，例如 `cat-two-notes-1.1.2-windows-x64.zip`。

解压 ZIP，进入包含 `.agents` 和 `plugins` 的目录。Codex 的本地插件入口接收该目录。在终端运行以下命令注册目录和安装插件。

```sh
codex plugin marketplace add .
codex plugin add cat-two-notes@cat-two-accessory
```

在 Codex 桌面端打开或重新加载一个**本地会话**。在聊天框中输入 `@Cat_two`，选择 **Cat_two 笔记**。已装有旧版的用户可以更新原插件目录后重新安装。如果使用新解压目录，先移除旧的目录登记 `codex plugin marketplace remove cat-two-accessory`，再从新目录运行上述两条命令。[Codex 插件文档](https://developers.openai.com/plugins/build/plugins)

## 首次连接

1. 在桌面版「此电脑」会话中选择 `@Cat_two 笔记`，发送「检查 Cat_two 连接」。首次连接检查会直接返回临时的本机配置页链接。若会话尚未加载连接工具，Windows 用户可运行上面的启动器打开同一个配置页。
2. 在 Cat_two 打开「设置 → MCP 和 API」，创建 **MCP 令牌**。查询笔记可用只读令牌。创建或更新笔记需要读写令牌。[Cat_two MCP 文档](https://github.com/Tiger-zero/Cat_two/blob/main/server/mcp/README.md#endpoint-transport--auth)
3. 在运行 Codex 的同一台电脑上打开配置页，填写 Docker 应用地址（如 `http://192.168.1.10:5230`）或完整的 `/mcp` 地址，再粘贴 MCP 令牌。表单接受原始令牌和 `Bearer …`。通过可信局域网使用 HTTP 时，需要在表单确认后提交。
4. 页面验证账号并保存后，回到 Codex 继续。如果当前会话仍只显示连接工具，新建一个本地会话即可加载笔记工具。

更换地址或令牌时，可以在聊天中选择插件并发送「重新配置 Cat_two」。配置保存在当前用户目录下的 `~/.cat-two-codex/connection.json`。该文件在 macOS 和 Linux 上仅当前用户可读写，令牌以明文保存在文件中，避免提交或分享该文件。撤销令牌请在 Cat_two 的「MCP 和 API」中操作。

macOS 和 Linux 也可以在解压目录用包内运行时打开浏览器配置页。

```sh
./plugins/cat-two-notes/runtime/bin/python3 -B plugins/cat-two-notes/scripts/server.py setup-browser
```

如果需要在终端配置，可以把同一命令的最后一个参数改为 `configure`。该方式会隐藏令牌输入。

## 在 Codex 中使用

- `@Cat_two 笔记` 检查连接并显示最近三条笔记。
- `@Cat_two 笔记` 按已有标签汇总过去七天的未完成待办，保留来源链接。
- `@Cat_two 笔记` 把本次任务整理成 Markdown 归档草稿，先给我确认。

如果客户端使用技能命令，也可以选 `$cat-two-notes:cat-two-setup` 或 `$cat-two-notes:organize-notes`。插件在新建或修改笔记前会展示目标和完整正文，等你确认后才写入。

## 构建发布包

- 从 GitHub **Actions → Build Codex plugin ZIPs → Run workflow** 手动构建。运行成功后，在该次运行的 **Artifacts** 中下载 `cat-two-notes-platform-packages`，从其中取出对应平台和安装方式的 ZIP。
- 发布时同步更新两份插件清单和 `server.py` 的版本号，再推送同版本标签（如 `v1.1.2`）。工作流构建并校验所有平台的单插件包和市场包，验证 Windows x64 启动器后将 ZIP 和 SHA-256 文件发布到该标签的 Release。[构建与发布工作流](.github/workflows/release.yml)
- 开发者可以从仓库目录安装源码版，Codex 会使用系统的 `python3`（3.9 或更新版本）。运行 `python3 -B scripts/build_release.py --platform all --format both` 可在 `dist/` 复现两种发布包。用 `--platform windows-x64 --format plugin` 可只构建 Windows x64 单插件包。[开发 Skill](.agents/skills/cat-two-plugin-development/SKILL.md)
