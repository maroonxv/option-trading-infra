"""整仓库脚手架高层编排。"""

from __future__ import annotations

from dataclasses import replace

from .catalog import DEFAULT_PRESET_KEY, DEFAULT_PROJECT_NAME, build_scaffold_plan
from .models import CreateOptions, ScaffoldPlan
from .prompt import prompt_for_create_options, should_prompt_for_create
from .renderer import render_scaffold_plan


def create_project_scaffold(options: CreateOptions) -> ScaffoldPlan:
    """根据 create 参数生成整仓库脚手架。"""
    resolved_options = options
    if resolved_options.use_default:
        resolved_options = replace(
            resolved_options,
            name=resolved_options.name or DEFAULT_PROJECT_NAME,
            preset=resolved_options.preset or DEFAULT_PRESET_KEY,
            no_interactive=True,
        )
    elif should_prompt_for_create(resolved_options):
        resolved_options = prompt_for_create_options(resolved_options)
    else:
        if not resolved_options.name:
            raise ValueError("项目名称不能为空。请传入名称，或在交互式终端中运行 `option-scaffold create`。")
        if resolved_options.preset is None:
            resolved_options = replace(resolved_options, preset=DEFAULT_PRESET_KEY)

    plan = build_scaffold_plan(resolved_options)
    render_scaffold_plan(plan)
    return plan
