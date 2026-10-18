# GPT · 个人记忆数据库

把跨会话需要保留的信息，整理成可查询、可纠正、有日期与来源的记录。JSON 是权威数据，SQLite 是可重建索引，Markdown 是便于交接的阅读版。仅依赖 Python 3.10+ 标准库。

## 当前状态

仓库初始化时为公开状态，因此本仓库只含程序、规范和虚构示例，不含真实个人记忆。实际数据包另行提供。**导入个人数据前，请先将仓库改为 Private 并确认可访问成员。** Git 忽略规则不是加密，也不会移除已经提交的历史。

## 使用

在仓库根目录运行（Windows 可把 `python3` 替换为 `python`）：

```bash
python3 memory.py validate --source examples/memories.json
python3 memory.py search 考试 --source examples/memories.json
python3 memory.py build --source examples/memories.json --db /tmp/demo-memory.sqlite3
python3 -m unittest discover -s tests -v
```

收到实际数据包后，将其中 `private/` 放在仓库根目录。默认不会纳入 Git：

```bash
python3 memory.py validate
python3 memory.py search 考研
python3 memory.py search 水力学 --all
python3 memory.py context
python3 memory.py context --category education
python3 memory.py build
```

`search` 是 JSON 的中文子串检索，支持多个关键词（全部匹配）；默认只返回 active 记录。`--all` 同时检索历史和待确认记录。`context` 默认仅导出有效记忆；超出复核日期的记录会明确标记。`build` 用一次事务重建 SQLite 索引，不依赖网络或模型服务。

### 私有仓库中的版本管理

确认仓库已为 Private 后，可按需跟踪权威 JSON 与阅读版：

```bash
git add -f private/memories.json private/MEMORY.md
git commit -m "Update personal memory snapshot"
```

不要提交 SQLite、压缩包、密码、令牌、身份验证码、身份证号或完整原始聊天。不要开启 Pages 或把个人数据复制到公开 Issue / Actions 日志。将来更改仓库可见性前须检查全部 Git 历史。

## 维护

- 每条记录有稳定 ID、类别、内容、信息日期、来源、状态、敏感度和复核日期。
- 用户明确更正优先；动态进度不能覆盖成永久画像。保留旧记录时设为 historical，并用 `supersedes` 关联。
- 依据会话摘要录入的内容标为 `conversation_summary`，不冒充逐字原文；未确认的推断使用 inferred / needs_confirmation。
- `observed_on` 不知道则填 null，不用建库日期冒充；`review_on` 只是建议复核日期，不代表已经复核。
- 更新 JSON 后运行 validate，然后重新生成阅读版与索引。导出阅读版：`python3 memory.py context --all > private/MEMORY.md`。
- 需要删除时从 JSON 移除并重建索引；这不会清除先前 Git 提交或备份中的内容。

## 与助手协作

可在未来对话中说：“读取 GPT 仓库的记忆，再继续我的学习计划。”前提是当次会话具备仓库访问能力。此仓库**不会自动读取全部聊天、自动同步，或自动变成所有会话的系统记忆**。AGENTS.md 只指导在此仓库工作的工具，不能保证其他产品自动加载它。

文件：`memory.py`（校验/查询/交接/建索引）、`schema.sql`（索引结构）、`examples/memories.json`（虚构示例）、`AGENTS.md`（维护约定）。
