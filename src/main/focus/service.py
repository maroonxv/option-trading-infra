from __future__ import annotations

from collections.abc import Iterable
import importlib
import json
from pathlib import Path
import re
import tomllib

from .models import AcceptanceSpec, FocusContext, FocusManifest, FocusPointer, FocusTestMatrix, PackDefinition, SkippedPackTests, StrategyMetadata, WorkflowSpec
from .renderer import build_recommended_first_pass, render_active_surface, render_system_map, render_task_brief, render_task_router, render_test_matrix, render_workflows

FOCUS_ROOT = Path("focus")
PACKS_ROOT = FOCUS_ROOT / "packs"
STRATEGIES_ROOT = FOCUS_ROOT / "strategies"
STATE_ROOT = Path(".focus")
MANIFEST_FILENAME = "strategy.manifest.toml"
CURRENT_POINTER_FILENAME = "current.toml"
DEFAULT_PACK_KEYS: tuple[str, ...] = ("kernel", "selection", "pricing", "risk", "execution", "hedging", "monitoring", "web", "deploy", "backtest")
DEFAULT_EDITABLE_PATHS: tuple[str, ...] = (
    "src/strategy/strategy_entry.py",
    "src/strategy/application",
    "src/strategy/domain",
    "config/strategy_config.toml",
    "config/general/trading_target.toml",
    "config/domain_service",
    "tests/strategy",
    "tests/web",
)
DEFAULT_REFERENCE_PATHS: tuple[str, ...] = (
    "src/main",
    "src/main/validation",
    "src/backtesting",
    "src/web",
    "src/main/scaffold",
    "tests/strategy/application",
    "tests/main/scaffold",
    "tests/main/validation",
    "deploy",
    "docs",
    "README.md",
)
DEFAULT_FROZEN_PATHS: tuple[str, ...] = (".codex", ".git", ".venv", ".hypothesis", "temp", "LICENSE")
PACK_REQUIRED_MODULES: dict[str, tuple[str, ...]] = {"backtest": ("chinese_calendar",)}
SMOKE_TEST_EXCLUDE_KEYWORDS: tuple[str, ...] = ("property", "pbt")
WIDE_FOCUS_PACK_THRESHOLD = 6
WIDE_FOCUS_EDITABLE_THRESHOLD = 6
SMOKE_VERIFICATION_PROFILE = "focus.smoke"
FULL_VERIFICATION_PROFILE = "focus.full"


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", value.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug.lower() or "main"


def manifest_path_for(repo_root: Path, strategy_name: str) -> Path:
    return repo_root / STRATEGIES_ROOT / slugify(strategy_name) / MANIFEST_FILENAME


def current_pointer_path_for(repo_root: Path) -> Path:
    return repo_root / STATE_ROOT / CURRENT_POINTER_FILENAME


def _generated_doc_paths(repo_root: Path) -> tuple[Path, Path, Path, Path, Path, Path]:
    nav_dir = repo_root / STATE_ROOT
    return (
        nav_dir / "SYSTEM_MAP.md",
        nav_dir / "ACTIVE_SURFACE.md",
        nav_dir / "TASK_BRIEF.md",
        nav_dir / "WORKFLOWS.md",
        nav_dir / "TASK_ROUTER.md",
        nav_dir / "TEST_MATRIX.md",
    )


def context_json_path_for(repo_root: Path) -> Path:
    return repo_root / STATE_ROOT / "context.json"


def _read_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _ensure_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field_name}` must be a non-empty string.")
    return value.strip()


def _ensure_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"`{field_name}` must be an array of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"`{field_name}` contains an empty string.")
        items.append(item.strip())
    return tuple(items)


def _quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _selector_base_path(selector: str) -> str:
    return selector.split("::", 1)[0].strip()


def _validate_repo_path(repo_root: Path, relative_path: str, field_name: str) -> None:
    if not (repo_root / relative_path).exists():
        raise ValueError(f"`{field_name}` references missing path: {relative_path}")


def _validate_selector(repo_root: Path, selector: str, field_name: str) -> None:
    base_path = _selector_base_path(selector)
    if not base_path:
        raise ValueError(f"`{field_name}` contains an empty selector.")
    if not base_path.startswith("-"):
        _validate_repo_path(repo_root, base_path, field_name)


def load_pack_catalog(repo_root: Path) -> dict[str, PackDefinition]:
    pack_root = repo_root / PACKS_ROOT
    if not pack_root.exists():
        raise ValueError(f"Missing pack metadata directory: {PACKS_ROOT.as_posix()}")
    catalog: dict[str, PackDefinition] = {}
    for pack_key in DEFAULT_PACK_KEYS:
        pack_path = pack_root / pack_key / "pack.toml"
        if not pack_path.exists():
            raise ValueError(f"Missing pack metadata file: {(PACKS_ROOT / pack_key / 'pack.toml').as_posix()}")
        raw = _read_toml(pack_path)
        key = _ensure_string(raw.get("key"), f"{pack_path.name}.key")
        catalog[key] = PackDefinition(
            key=key,
            manifest_path=pack_path,
            depends_on=_ensure_string_tuple(raw.get("depends_on", []), f"{key}.depends_on"),
            owned_paths=_ensure_string_tuple(raw.get("owned_paths", []), f"{key}.owned_paths"),
            config_keys=_ensure_string_tuple(raw.get("config_keys", []), f"{key}.config_keys"),
            test_selectors=_ensure_string_tuple(raw.get("test_selectors", []), f"{key}.test_selectors"),
            workflow_refs=_ensure_string_tuple(raw.get("workflow_refs", []), f"{key}.workflow_refs"),
            agent_notes=_ensure_string_tuple(raw.get("agent_notes", []), f"{key}.agent_notes"),
        )
    for key, definition in catalog.items():
        for dependency in definition.depends_on:
            if dependency not in catalog:
                raise ValueError(f"pack `{key}` depends on unknown pack `{dependency}`.")
        for owned_path in definition.owned_paths:
            _validate_repo_path(repo_root, owned_path, f"{key}.owned_paths")
        for selector in definition.test_selectors:
            _validate_selector(repo_root, selector, f"{key}.test_selectors")
    _resolve_pack_keys(tuple(catalog.keys()), catalog)
    return catalog


def _resolve_pack_keys(pack_keys: tuple[str, ...], catalog: dict[str, PackDefinition]) -> tuple[str, ...]:
    resolved: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(key: str, trail: tuple[str, ...]) -> None:
        if key not in catalog:
            raise ValueError(f"Unknown pack: {key}")
        if key in visited:
            return
        if key in visiting:
            raise ValueError(f"Detected pack dependency cycle: {' -> '.join((*trail, key))}")
        visiting.add(key)
        for dependency in catalog[key].depends_on:
            visit(dependency, (*trail, key))
        visiting.remove(key)
        visited.add(key)
        if key not in resolved:
            resolved.append(key)

    for key in pack_keys:
        visit(key, ())
    return tuple(resolved)


def _pack_definitions_for(pack_keys: tuple[str, ...], catalog: dict[str, PackDefinition]) -> tuple[PackDefinition, ...]:
    return tuple(catalog[key] for key in _resolve_pack_keys(pack_keys, catalog))


def validate_manifest(repo_root: Path, manifest: FocusManifest, catalog: dict[str, PackDefinition]) -> None:
    if not manifest.workflow.runtime_module or not manifest.workflow.backtest_module or not manifest.workflow.monitor_script:
        raise ValueError("Workflow metadata is incomplete.")
    if not manifest.packs:
        raise ValueError("`packs` cannot be empty.")
    _resolve_pack_keys(manifest.packs, catalog)
    for relative_path in manifest.editable_paths:
        _validate_repo_path(repo_root, relative_path, "editable_paths")
    for relative_path in manifest.reference_paths:
        _validate_repo_path(repo_root, relative_path, "reference_paths")
    for relative_path in manifest.frozen_paths:
        _validate_repo_path(repo_root, relative_path, "frozen_paths")
    for selector in manifest.acceptance.test_selectors:
        _validate_selector(repo_root, selector, "acceptance.test_selectors")
    overlap = sorted(set(manifest.editable_paths) & set(manifest.frozen_paths))
    if overlap:
        raise ValueError(f"`editable_paths` and `frozen_paths` overlap: {', '.join(overlap)}")


def _load_manifest_from_path(repo_root: Path, manifest_path: Path) -> FocusManifest:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Focus manifest not found: {manifest_path}")
    raw = _read_toml(manifest_path)
    strategy_raw = raw.get("strategy")
    workflow_raw = raw.get("workflow")
    acceptance_raw = raw.get("acceptance")
    if not isinstance(strategy_raw, dict):
        raise ValueError("Focus manifest is missing `[strategy]`.")
    if not isinstance(workflow_raw, dict):
        raise ValueError("Focus manifest is missing `[workflow]`.")
    if not isinstance(acceptance_raw, dict):
        raise ValueError("Focus manifest is missing `[acceptance]`.")
    manifest = FocusManifest(
        manifest_path=manifest_path,
        strategy=StrategyMetadata(
            name=_ensure_string(strategy_raw.get("name"), "strategy.name"),
            trading_target=_ensure_string(strategy_raw.get("trading_target"), "strategy.trading_target"),
            strategy_type=_ensure_string(strategy_raw.get("strategy_type"), "strategy.strategy_type"),
            run_mode=_ensure_string(strategy_raw.get("run_mode"), "strategy.run_mode"),
            summary=_ensure_string(strategy_raw.get("summary"), "strategy.summary"),
        ),
        packs=_ensure_string_tuple(raw.get("packs"), "packs"),
        workflow=WorkflowSpec(
            runtime_module=_ensure_string(workflow_raw.get("runtime_module"), "workflow.runtime_module"),
            backtest_module=_ensure_string(workflow_raw.get("backtest_module"), "workflow.backtest_module"),
            monitor_script=_ensure_string(workflow_raw.get("monitor_script"), "workflow.monitor_script"),
        ),
        editable_paths=_ensure_string_tuple(raw.get("editable_paths"), "editable_paths"),
        reference_paths=_ensure_string_tuple(raw.get("reference_paths"), "reference_paths"),
        frozen_paths=_ensure_string_tuple(raw.get("frozen_paths"), "frozen_paths"),
        acceptance=AcceptanceSpec(
            summary=_ensure_string(acceptance_raw.get("summary"), "acceptance.summary"),
            completion_checks=_ensure_string_tuple(acceptance_raw.get("completion_checks"), "acceptance.completion_checks"),
            default_verification_profile=_ensure_string(acceptance_raw.get("default_verification_profile"), "acceptance.default_verification_profile"),
            test_selectors=_ensure_string_tuple(acceptance_raw.get("test_selectors"), "acceptance.test_selectors"),
            key_logs=_ensure_string_tuple(acceptance_raw.get("key_logs"), "acceptance.key_logs"),
            key_outputs=_ensure_string_tuple(acceptance_raw.get("key_outputs"), "acceptance.key_outputs"),
        ),
    )
    validate_manifest(repo_root, manifest, load_pack_catalog(repo_root))
    return manifest


def load_current_pointer(repo_root: Path) -> FocusPointer:
    pointer_path = current_pointer_path_for(repo_root)
    if not pointer_path.exists():
        raise FileNotFoundError("Current repository has not initialized a focus pointer yet.")
    raw = _read_toml(pointer_path)
    strategy = _ensure_string(raw.get("strategy"), "current.strategy")
    manifest_relative_path = _ensure_string(raw.get("manifest_path"), "current.manifest_path")
    manifest_path = repo_root / manifest_relative_path
    if not manifest_path.exists():
        raise FileNotFoundError(f"Current focus pointer references missing manifest: {manifest_relative_path}")
    return FocusPointer(strategy=strategy, manifest_path=manifest_path)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_current_pointer(repo_root: Path, strategy_name: str, manifest_path: Path) -> FocusPointer:
    relative_manifest_path = manifest_path.relative_to(repo_root).as_posix()
    content = "\n".join([f"strategy = {_quote(slugify(strategy_name))}", f"manifest_path = {_quote(relative_manifest_path)}", ""])
    path = current_pointer_path_for(repo_root)
    _write(path, content)
    return FocusPointer(strategy=slugify(strategy_name), manifest_path=manifest_path)


def _default_workflow() -> WorkflowSpec:
    return WorkflowSpec(runtime_module="src.main.main", backtest_module="src.backtesting.main", monitor_script="src/web/app.py")


def _default_acceptance(*, summary: str | None = None, completion_checks: tuple[str, ...] | None = None) -> AcceptanceSpec:
    return AcceptanceSpec(
        summary=summary or "Focus navigation, current context, and verification outputs stay aligned for agent-driven edits.",
        completion_checks=completion_checks or (
            "Focus navigation files are refreshed and point to the current manifest.",
            "Validation succeeds for the current strategy configuration.",
            "Focus smoke verification passes for the current strategy.",
        ),
        default_verification_profile=SMOKE_VERIFICATION_PROFILE,
        test_selectors=("tests/main/focus", "tests/main/validation", "tests/main/scaffold"),
        key_logs=("Validation passed", "Focus assets refreshed"),
        key_outputs=(
            ".focus/SYSTEM_MAP.md",
            ".focus/ACTIVE_SURFACE.md",
            ".focus/TASK_BRIEF.md",
            ".focus/WORKFLOWS.md",
            ".focus/TASK_ROUTER.md",
            ".focus/TEST_MATRIX.md",
            ".focus/context.json",
            "tests/TEST.md",
        ),
    )


def _render_manifest(manifest: FocusManifest) -> str:
    return "\n".join(
        [
            f"packs = [{', '.join(_quote(item) for item in manifest.packs)}]",
            f"editable_paths = [{', '.join(_quote(item) for item in manifest.editable_paths)}]",
            f"reference_paths = [{', '.join(_quote(item) for item in manifest.reference_paths)}]",
            f"frozen_paths = [{', '.join(_quote(item) for item in manifest.frozen_paths)}]",
            "",
            "[strategy]",
            f"name = {_quote(manifest.strategy.name)}",
            f"trading_target = {_quote(manifest.strategy.trading_target)}",
            f"strategy_type = {_quote(manifest.strategy.strategy_type)}",
            f"run_mode = {_quote(manifest.strategy.run_mode)}",
            f"summary = {_quote(manifest.strategy.summary)}",
            "",
            "[workflow]",
            f"runtime_module = {_quote(manifest.workflow.runtime_module)}",
            f"backtest_module = {_quote(manifest.workflow.backtest_module)}",
            f"monitor_script = {_quote(manifest.workflow.monitor_script)}",
            "",
            "[acceptance]",
            f"summary = {_quote(manifest.acceptance.summary)}",
            "completion_checks = [" + ", ".join(_quote(item) for item in manifest.acceptance.completion_checks) + "]",
            f"default_verification_profile = {_quote(manifest.acceptance.default_verification_profile)}",
            "test_selectors = [" + ", ".join(_quote(item) for item in manifest.acceptance.test_selectors) + "]",
            f"key_logs = [{', '.join(_quote(item) for item in manifest.acceptance.key_logs)}]",
            f"key_outputs = [{', '.join(_quote(item) for item in manifest.acceptance.key_outputs)}]",
            "",
        ]
    )


def _build_default_manifest(repo_root: Path, strategy_name: str, *, trading_target: str, strategy_type: str, run_mode: str, pack_keys: tuple[str, ...], summary: str | None = None, completion_checks: tuple[str, ...] | None = None) -> FocusManifest:
    manifest_path = manifest_path_for(repo_root, strategy_name)
    return FocusManifest(
        manifest_path=manifest_path,
        strategy=StrategyMetadata(
            name=slugify(strategy_name),
            trading_target=trading_target,
            strategy_type=strategy_type,
            run_mode=run_mode,
            summary=summary or "Default full-pack focus for agent-driven strategy development in the current repository.",
        ),
        packs=pack_keys,
        workflow=_default_workflow(),
        editable_paths=DEFAULT_EDITABLE_PATHS,
        reference_paths=tuple(path for path in DEFAULT_REFERENCE_PATHS if (repo_root / path).exists()),
        frozen_paths=tuple(path for path in DEFAULT_FROZEN_PATHS if (repo_root / path).exists()),
        acceptance=_default_acceptance(summary=summary, completion_checks=completion_checks),
    )


def _unique_preserve_order(items: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return tuple(result)


def focus_test_profile(*, full: bool = False) -> str:
    return FULL_VERIFICATION_PROFILE if full else SMOKE_VERIFICATION_PROFILE


def _smoke_keyword_expression() -> str:
    return " and ".join(f"not {keyword}" for keyword in SMOKE_TEST_EXCLUDE_KEYWORDS)


def _smoke_filter_descriptions() -> tuple[str, ...]:
    return tuple(f"Exclude test nodes whose names contain `{keyword}`." for keyword in SMOKE_TEST_EXCLUDE_KEYWORDS)


def _collect_workflow_refs(context: FocusContext) -> tuple[str, ...]:
    refs = ["validation", "runtime", "backtest", "monitoring", context.manifest.acceptance.default_verification_profile, focus_test_profile(full=True)]
    for pack in context.resolved_packs:
        refs.extend(pack.workflow_refs)
    return _unique_preserve_order(tuple(refs))


def build_focus_context_payload(context: FocusContext) -> dict[str, object]:
    recommended_pack, first_entry = build_recommended_first_pass(context)
    test_matrix = build_focus_test_matrix(context)
    generated_docs = {
        "system_map": context.system_map_path.relative_to(context.repo_root).as_posix(),
        "active_surface": context.active_surface_path.relative_to(context.repo_root).as_posix(),
        "task_brief": context.task_brief_path.relative_to(context.repo_root).as_posix(),
        "workflows": context.workflows_path.relative_to(context.repo_root).as_posix(),
        "task_router": context.task_router_path.relative_to(context.repo_root).as_posix(),
        "test_matrix": context.test_matrix_path.relative_to(context.repo_root).as_posix(),
        "context_json": context.context_json_path.relative_to(context.repo_root).as_posix(),
    }
    return {
        "strategy": {
            "name": context.manifest.strategy.name,
            "trading_target": context.manifest.strategy.trading_target,
            "strategy_type": context.manifest.strategy.strategy_type,
            "run_mode": context.manifest.strategy.run_mode,
            "summary": context.manifest.strategy.summary,
        },
        "manifest_path": context.manifest.manifest_path.relative_to(context.repo_root).as_posix(),
        "packs": [pack.key for pack in context.resolved_packs],
        "workflows": {
            "runtime_module": context.manifest.workflow.runtime_module,
            "backtest_module": context.manifest.workflow.backtest_module,
            "monitor_script": context.manifest.workflow.monitor_script,
            "workflow_refs": list(_collect_workflow_refs(context)),
            "default_verification_profile": context.manifest.acceptance.default_verification_profile,
            "expanded_verification_profile": focus_test_profile(full=True),
        },
        "recommended_first_pass": {"pack": recommended_pack, "entry": first_entry},
        "surfaces": {
            "editable": list(context.manifest.editable_paths),
            "reference": list(context.manifest.reference_paths),
            "frozen": list(context.manifest.frozen_paths),
        },
        "health": list(describe_focus_health(context)),
        "test_matrix": {
            "smoke_selectors": list(test_matrix.smoke_selectors),
            "full_selectors": list(test_matrix.full_selectors),
            "smoke_keyword_expression": test_matrix.smoke_keyword_expression,
            "smoke_filter_descriptions": list(test_matrix.smoke_filter_descriptions),
            "skipped_packs": [{"pack_key": item.pack_key, "missing_modules": list(item.missing_modules)} for item in test_matrix.skipped_packs],
        },
        "generated_docs": generated_docs,
        "acceptance": {
            "summary": context.manifest.acceptance.summary,
            "completion_checks": list(context.manifest.acceptance.completion_checks),
            "default_verification_profile": context.manifest.acceptance.default_verification_profile,
            "test_selectors": list(context.manifest.acceptance.test_selectors),
            "key_logs": list(context.manifest.acceptance.key_logs),
            "key_outputs": list(context.manifest.acceptance.key_outputs),
        },
    }


def build_focus_test_matrix(context: FocusContext) -> FocusTestMatrix:
    selectors: list[str] = list(context.manifest.acceptance.test_selectors)
    skipped_packs: list[SkippedPackTests] = []
    for pack in context.resolved_packs:
        missing_modules = tuple(module_name for module_name in PACK_REQUIRED_MODULES.get(pack.key, ()) if not _module_available(module_name))
        if missing_modules:
            skipped_packs.append(SkippedPackTests(pack_key=pack.key, missing_modules=missing_modules))
            continue
        selectors.extend(pack.test_selectors)
    full_selectors = _unique_preserve_order(tuple(selectors))
    return FocusTestMatrix(smoke_selectors=full_selectors, full_selectors=full_selectors, skipped_packs=tuple(skipped_packs), smoke_keyword_expression=_smoke_keyword_expression(), smoke_filter_descriptions=_smoke_filter_descriptions())


def collect_test_selectors(context: FocusContext) -> tuple[str, ...]:
    selectors: list[str] = list(context.manifest.acceptance.test_selectors)
    for pack in context.resolved_packs:
        selectors.extend(pack.test_selectors)
    return _unique_preserve_order(tuple(selectors))


def collect_runnable_test_selectors(context: FocusContext) -> tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]]:
    test_matrix = build_focus_test_matrix(context)
    skipped_packs = tuple((item.pack_key, item.missing_modules) for item in test_matrix.skipped_packs)
    return test_matrix.full_selectors, skipped_packs


def _module_available(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError:
        return False
    return True


def describe_focus_health(context: FocusContext) -> tuple[str, ...]:
    pack_count = len(context.resolved_packs)
    editable_path_count = len(context.manifest.editable_paths)
    summary = f"Focus width: {pack_count} packs and {editable_path_count} editable-surface entries."
    if pack_count >= WIDE_FOCUS_PACK_THRESHOLD or editable_path_count >= WIDE_FOCUS_EDITABLE_THRESHOLD:
        return (summary, "This focus is wide. Start from the TASK_ROUTER first-pass entry instead of scanning everything.")
    return (summary, "This focus is narrow enough to start directly from the recommended first pass.")


def _render_navigation(context: FocusContext) -> None:
    system_map_path, active_surface_path, task_brief_path, workflows_path, task_router_path, test_matrix_path = _generated_doc_paths(context.repo_root)
    test_matrix = build_focus_test_matrix(context)
    smoke_profile = focus_test_profile()
    full_profile = focus_test_profile(full=True)
    _write(system_map_path, render_system_map(context))
    _write(active_surface_path, render_active_surface(context))
    _write(task_brief_path, render_task_brief(context))
    _write(workflows_path, render_workflows(context, _collect_workflow_refs(context), smoke_profile=smoke_profile, full_profile=full_profile))
    _write(task_router_path, render_task_router(context, test_matrix, smoke_profile=smoke_profile, full_profile=full_profile))
    _write(test_matrix_path, render_test_matrix(context, test_matrix, smoke_profile=smoke_profile, full_profile=full_profile))
    commands_path = context.repo_root / STATE_ROOT / "COMMANDS.md"
    if commands_path.exists():
        commands_path.unlink()
    _write_json(context.context_json_path, build_focus_context_payload(context))


def load_focus_context(repo_root: Path, strategy_name: str | None = None) -> FocusContext:
    catalog = load_pack_catalog(repo_root)
    pointer = load_current_pointer(repo_root) if strategy_name is None else FocusPointer(strategy=slugify(strategy_name), manifest_path=manifest_path_for(repo_root, strategy_name))
    manifest = _load_manifest_from_path(repo_root, pointer.manifest_path)
    return FocusContext(repo_root=repo_root, pointer=FocusPointer(strategy=manifest.strategy.name, manifest_path=manifest.manifest_path), manifest=manifest, resolved_packs=_pack_definitions_for(manifest.packs, catalog))


def initialize_focus(repo_root: Path, strategy_name: str, *, trading_target: str, strategy_type: str, run_mode: str, include_packs: tuple[str, ...] = (), exclude_packs: tuple[str, ...] = (), force: bool = False, summary: str | None = None, completion_checks: tuple[str, ...] | None = None) -> FocusContext:
    catalog = load_pack_catalog(repo_root)
    selected = include_packs or tuple(key for key in DEFAULT_PACK_KEYS if key in catalog)
    selected = tuple(key for key in selected if key not in set(exclude_packs))
    if not selected:
        raise ValueError("Initializing focus requires at least one retained pack.")
    manifest = _build_default_manifest(repo_root, strategy_name, trading_target=trading_target, strategy_type=strategy_type, run_mode=run_mode, pack_keys=_resolve_pack_keys(selected, catalog), summary=summary, completion_checks=completion_checks)
    if manifest.manifest_path.exists() and not force:
        raise FileExistsError(f"Focus manifest already exists: {manifest.manifest_path.relative_to(repo_root).as_posix()}. Use force=True to overwrite it.")
    validate_manifest(repo_root, manifest, catalog)
    _write(manifest.manifest_path, _render_manifest(manifest))
    write_current_pointer(repo_root, strategy_name, manifest.manifest_path)
    context = load_focus_context(repo_root, strategy_name)
    _render_navigation(context)
    return context


def refresh_focus(repo_root: Path, strategy_name: str | None = None) -> FocusContext:
    context = load_focus_context(repo_root, strategy_name)
    write_current_pointer(repo_root, context.manifest.strategy.name, context.manifest.manifest_path)
    _render_navigation(context)
    return context


def refresh_agent_assets(repo_root: Path) -> FocusContext:
    spec_path = repo_root / "strategy_spec.toml"
    if not spec_path.exists():
        return refresh_focus(repo_root)
    from src.main.spec.service import build_test_plan_markdown, load_strategy_spec, pack_keys_from_spec
    spec = load_strategy_spec(repo_root, spec_path)
    context = initialize_focus(
        repo_root,
        spec.strategy.name,
        trading_target=spec.strategy.trading_target,
        strategy_type=spec.strategy.strategy_type,
        run_mode=spec.strategy.run_mode,
        include_packs=pack_keys_from_spec(spec),
        force=True,
        summary=spec.strategy.summary,
        completion_checks=spec.acceptance.completion_checks,
    )
    test_plan_path = repo_root / "tests" / "TEST.md"
    test_plan_path.parent.mkdir(parents=True, exist_ok=True)
    test_plan_path.write_text(build_test_plan_markdown(spec), encoding="utf-8")
    return context


def _merge_keyword_expression(extra_args: tuple[str, ...], expression: str) -> tuple[str, ...]:
    args = list(extra_args)
    for index, argument in enumerate(args):
        if argument == "-k" and index + 1 < len(args):
            args[index + 1] = f"({args[index + 1]}) and ({expression})"
            return tuple(args)
        if argument.startswith("-k="):
            args[index] = f"-k=({argument[3:]}) and ({expression})"
            return tuple(args)
        if argument == "--keyword" and index + 1 < len(args):
            args[index + 1] = f"({args[index + 1]}) and ({expression})"
            return tuple(args)
        if argument.startswith("--keyword="):
            args[index] = f"--keyword=({argument[len('--keyword='):]}) and ({expression})"
            return tuple(args)
    return ("-k", expression, *extra_args)


def run_focus_tests(repo_root: Path, strategy_name: str | None = None, extra_args: tuple[str, ...] = (), *, full: bool = False) -> int:
    context = load_focus_context(repo_root, strategy_name)
    test_matrix = build_focus_test_matrix(context)
    selectors = test_matrix.full_selectors if full else test_matrix.smoke_selectors
    if not selectors:
        raise ValueError("Current focus has no runnable selectors.")
    try:
        import pytest
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("pytest is required before running focus tests.") from exc
    args: list[str] = []
    config_path = repo_root / "config" / "pytest.ini"
    if config_path.exists():
        args.extend(["-c", str(config_path)])
    args.extend(selectors)
    if not full:
        args.extend(_merge_keyword_expression(extra_args, test_matrix.smoke_keyword_expression))
    else:
        args.extend(extra_args)
    return int(pytest.main(args))
