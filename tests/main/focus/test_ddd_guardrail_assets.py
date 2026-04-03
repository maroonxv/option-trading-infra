from __future__ import annotations

from pathlib import Path
import tomllib

from src.main.focus.service import refresh_agent_assets


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def test_ddd_guardrail_docs_and_skills_exist() -> None:
    repo_root = _repo_root()
    agents_text = (repo_root / "AGENTS.md").read_text(encoding="utf-8")

    assert (repo_root / "docs" / "architecture" / "ddd-constitution.md").exists()
    assert (repo_root / "docs" / "architecture" / "context-map.md").exists()
    assert (repo_root / "docs" / "architecture" / "refactor-catalog.md").exists()
    assert (repo_root / ".codex" / "skills" / "ddd-coding-guard" / "SKILL.md").exists()
    assert (repo_root / ".codex" / "skills" / "ddd-refactor-coach" / "SKILL.md").exists()
    assert "ddd-coding-guard" in agents_text
    assert "ddd-refactor-coach" in agents_text
    assert "src/strategy/**" in agents_text


def test_ddd_guardrail_prompt_eval_suite_uses_real_repository_smells() -> None:
    repo_root = _repo_root()
    cases_dir = repo_root / "tests" / "agent-skills" / "cases"
    rubrics_dir = repo_root / "tests" / "agent-skills" / "rubrics"

    case_names = sorted(path.name for path in cases_dir.glob("*.md"))

    assert 6 <= len(case_names) <= 8
    assert "coding-guard-domain-infra-leak.md" in case_names
    assert "coding-guard-gateway-business-rule.md" in case_names
    assert "coding-guard-scaffold-stateful-service.md" in case_names
    assert "refactor-coach-domain-infra-leak.md" in case_names
    assert "refactor-coach-strategy-entry-bloat.md" in case_names
    assert "refactor-coach-refuse-big-bang.md" in case_names
    assert (rubrics_dir / "trigger-correctness.md").exists()
    assert (rubrics_dir / "boundary-judgment.md").exists()
    assert (rubrics_dir / "intervention-quality.md").exists()
    assert (rubrics_dir / "migration-quality.md").exists()


def test_focus_assets_do_not_freeze_pytest_cache() -> None:
    repo_root = _repo_root()

    context = refresh_agent_assets(repo_root)
    manifest_payload = tomllib.loads(
        (repo_root / "focus" / "strategies" / "main" / "strategy.manifest.toml").read_text(encoding="utf-8")
    )

    assert ".pytest_cache" not in context.manifest.frozen_paths
    assert ".pytest_cache" not in manifest_payload["frozen_paths"]
    assert '".pytest_cache"' not in context.context_json_path.read_text(encoding="utf-8")
    assert ".pytest_cache" not in context.active_surface_path.read_text(encoding="utf-8")
    assert ".pytest_cache" not in context.task_brief_path.read_text(encoding="utf-8")
