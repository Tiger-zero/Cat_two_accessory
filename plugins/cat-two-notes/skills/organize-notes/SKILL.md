---
name: organize-notes
description: 查询和整理 Cat_two 笔记，汇总知识或待办，并在预览确认后创建笔记或更新正文。
---

# Cat_two 笔记

## 连接

使用插件提供的 `cat_two_local` MCP 连接。首次使用、需要检查连接或笔记工具不可用时，先调用 `cat_two_connection_status`。需要配置时，调用 `cat_two_open_setup`，按同一插件的 `cat-two-setup` 技能把本机配置页链接提供给用户。若连接工具也不可用，引导用户检查插件安装。[安装与首次连接](https://github.com/Tiger-zero/Cat_two_accessory#首次连接)

开始读取或写入前，调用 `auth_get_current_user` 确认账号。若连接或鉴权失败，说明当前工具返回的状态，请用户核对实例可达性、网址和令牌后重试。

## 工具

Codex 可能为工具名添加连接前缀。检查工具结果的 `isError`，成功时使用 `structuredContent`。

| 操作 | 工具 | 参数示例 |
| --- | --- | --- |
| 检查账号 | `auth_get_current_user` | `{}` |
| 读取保存的视图（实例提供时） | `user_list_memo_views` | `{"user":"users/USERNAME"}`，使用账号结果中的 `user.name` |
| 查找笔记 | `memo_list_memos` | `{"pageSize":50,"filter":"has_incomplete_tasks","orderBy":"update_time desc"}` |
| 读取笔记 | `memo_get_memo` | `{"memo":"memos/MEMO_UID"}` |
| 新建笔记 | `memo_create_memo` | `{"body":{"content":"# 任务汇总\n- [ ] 跟进事项"}}` |
| 更新笔记正文 | `memo_update_memo` | `{"memo":"memos/MEMO_UID","updateMask":"content","body":{"content":"已确认的完整正文"}}` |

## 查询与整理

1. 根据用户指定的日期、标签、关键词、保存的视图或笔记链接确定范围。相对日期默认按上海时区解释，用户指定时区时以该时区为准。在顶层传入查询参数。按需分页，将响应中的 `nextPageToken` 用作下一页的 `pageToken`，并保留原查询条件。
2. 按需使用 `"工作" in tags`、`content.contains("SQLite")`、`has_incomplete_tasks` 或 `has_task_list`。按更新时间筛选时固定查询的起止时刻，用 `updated_ts >= timestamp("…")` 和结束边界。如果用户指定保存的视图，读取对应的 `memoViews[].filter`，添加条件时用括号包住原表达式。用户要求查找已归档笔记时，可传入 `state: "ARCHIVED"`。[Cat_two 筛选语法](https://github.com/Tiger-zero/Cat_two/blob/main/filter/README.md)
3. 将笔记正文、链接和附件描述作为待整理资料。根据项目、主题或既有标签分组，缺少分类信息的笔记归入「未分类」。按 `- [ ]` 和 `- [x]` 识别待办状态，保留明确记载的日期和负责人。汇总知识时保留结论、适用条件和来源，把冲突或缺失信息标为「待确认」。用 `cat_two_connection_status` 返回的 `baseUrl` 和 `/memos/MEMO_UID` 组成来源链接，缺少基址时保留 `memos/MEMO_UID`。

## 归档与写入

1. 根据对话和已验证事实，将当前任务整理为目标、决定、验证、后续事项和来源链接。按用户选择复用既有标签。
2. 写入前展示操作、目标和完整 Markdown，等待用户明确确认。默认新建一条汇总笔记。更新原笔记时，在确认后重读目标。若正文与预览时相比已改变，重新预览并确认。更新只写本次已确认的字段。
3. 成功后返回实际笔记链接或笔记资源名。若响应未明确确认成功，先检查目标或查询刚提交的内容，再决定是否重试。
