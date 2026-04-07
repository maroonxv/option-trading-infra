## DDD Guardrail

For any work touching `src/strategy/**`, use `.codex/skills/ddd-coding-guard` before implementation.
For hotspot cleanup or boundary repair in existing code, use `.codex/skills/ddd-refactor-coach`.

Redlines for `src/strategy/**` work:
- Domain code must not import infrastructure modules, framework types, or vendor payloads.
- Business rules must not be added to gateway, persistence, web, bootstrap, or runtime-entry layers.
- Cross-context handoffs must use explicit ports, DTOs, or value objects instead of mutable entities or raw vendor payloads.
- Do not add new facade or coordinator layers that flatten existing boundaries.

Read the full doctrine in:
- `docs/architecture/ddd-constitution.md`
- `docs/architecture/context-map.md`
- `docs/architecture/refactor-catalog.md`

# Agent 行为规范

## 自动 Git 提交规则

当你完成以下任何一类操作后，必须自动执行 `git add {修改的文件}`、`git commit -m "<message>"`、`git push`：

1. 修复 bug 或错误（如导入路径修复、运行时报错修复）
2. 新增功能或文件
3. 重构代码（如重命名、移动文件、调整结构）
4. 修改配置文件（如 Dockerfile、pytest.ini、requirements.txt 等）
5. 更新或新增测试
6. 更新文档（如 README、需求文档、AGENTS.md 等）

## Commit 消息格式

使用中文，遵循 Conventional Commits 风格：

```
<type>: <简要描述>

<可选的详细说明>
```

type 取值：
- `fix`: 修复 bug
- `feat`: 新功能
- `refactor`: 重构
- `docs`: 文档变更
- `chore`: 构建/配置/工具变更
- `test`: 测试相关
- `style`: 格式调整（不影响逻辑）

## 注意事项

- 每次操作完成后立即提交，不要积攒多个不相关的变更到一个 commit
- commit 消息要准确描述本次变更内容
- 如果一次用户请求涉及多个不相关的改动，拆分为多个 commit
- 如果检测到 `.codex` 的 skill 有增加，也请顺手进行 commit 并推送，commit 消息类似 `chore: 增加{skill名} skill`

## 编码约定

- 本仓库内所有文本文件统一使用 UTF-8 编码，默认使用 UTF-8（无 BOM）
- 禁止提交 GBK、ANSI、UTF-16 等其他编码的文本文件
- 修改现有文件时不得引入乱码；如发现编码异常，优先从 Git 历史恢复正确内容后再编辑

此项目未部署，请不要考虑任何向后兼容性，直接大胆放心改接口、改 schema 等。

针对领域服务或者基础设施，不要写 facade、coordinator 一类的代码，直接让上层调用具体服务或基础设施即可。

## Co-author 规则

When creating a git commit message:

If the agent is Codex, append exactly: `Co-authored-by: codex <codex@users.noreply.github.com>`

If the agent is Claude, append a GitHub-compatible co-author trailer only if the configured attribution email is verified to map correctly on GitHub; otherwise do not add a Claude co-author line.
