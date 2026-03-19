---
name: visualizing-strategy-workflows
description: Turn Python application-layer workflow files into visual markdown documentation with PlantUML sources and rendered SVG charts. Use when Codex needs to analyze `*_workflow.py` files, map collaborators, data flow, and call order, and generate `docs/workflows/*` plus `docs/plantuml/*` for option-strategy repositories or similar Python projects.
---

# Visualizing Strategy Workflows

## Overview

Use this skill to convert Python workflow orchestration code into visual-first markdown. Favor clear diagrams and short explanations over long prose.

硬性要求：所有生成的 Markdown 文档、章节标题、图注、摘要和说明文字都必须使用中文；仅文件路径、源码符号、类名、函数名以及 PlantUML 中的技术标识可以保留英文。

## Workflow

1. Resolve the application directory.
   - Use an explicit override first.
   - Otherwise check `src/application`.
   - Otherwise check `src/strategy/application`.
2. Scan only Python files matching `*_workflow.py`.
3. Run `scripts/generate_workflow_docs.py` to scaffold markdown, PlantUML source files, and SVG output paths.
4. Read the workflow source and replace scaffold placeholders with real architecture, data-flow, and sequence diagrams.
5. Add a state diagram only when the code shows meaningful state or mode transitions.

## Script

Run:

```bash
python .codex/skills/visualizing-strategy-workflows/scripts/generate_workflow_docs.py \
  --project-root <repo> \
  --application-dir <optional-app-dir> \
  --docs-root docs \
  --render
```

The script does deterministic work only:

- Discover workflow files.
- Derive slugs and output file names.
- Create missing markdown and `.puml` skeletons.
- Render existing `.puml` files into `docs/plantuml/chart/`.

It does not infer final diagram semantics for you. Fill those in after reading the workflow code.

## Output Rules

- Keep one markdown file per workflow at `docs/workflows/<workflow-slug>.md`.
- Keep PlantUML sources at `docs/plantuml/code/`.
- Keep rendered charts at `docs/plantuml/chart/`.
- Embed images directly in the markdown using relative paths.
- All generated documentation content, section titles, captions, summaries, and explanatory text must be written in Chinese. Keep English only for file paths, code symbols, and technical identifiers when needed.
- Keep prose short:
  - one responsibility summary
  - source file path
  - primary entrypoint
  - brief notes on collaborators, inputs, and outputs

## References

- Read `references/markdown-template.md` before editing workflow markdown.
- Read `references/diagram-conventions.md` before writing PlantUML.
- Read `references/diagram-selection.md` when deciding whether a state diagram is justified.

## Repo Notes

- Treat the current repo's workflows as examples, not hardcoded assumptions.
- Do not couple the skill to specific workflow names from this repository.
- Ignore non-workflow application files such as bridges, handlers, or adapters unless a workflow diagram needs to reference them as collaborators.
