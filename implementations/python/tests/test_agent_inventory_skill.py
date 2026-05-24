from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILL_PATH = REPO_ROOT / ".claude" / "skills" / "aces-asset-inventory-capture" / "SKILL.md"
CODEX_RULES_PATH = REPO_ROOT / ".codex"


def test_asset_inventory_skill_is_cross_agent_and_discoverable_by_codex() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    codex_rules = CODEX_RULES_PATH.read_text(encoding="utf-8")

    assert "TODO" not in skill
    assert "from either Claude Code or Codex" in skill
    assert "aces-asset-inventory-capture" in codex_rules
    assert ".claude/skills/aces-asset-inventory-capture/SKILL.md" in codex_rules


def test_asset_inventory_skill_encodes_methodology_tool_baseline() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    required_terms = (
        "Trivy CycloneDX SBOM",
        "Trivy vulnerability JSON",
        "Syft",
        "osquery",
        "installed_applications",
        "programs",
        "apt_sources",
        "processes",
        "listening_ports",
        "docker_containers",
        "docker_images",
        "mtree",
        "AIDE",
        "Tripwire",
        "ADR-029",
    )

    missing = [term for term in required_terms if term not in skill]

    assert not missing


def test_asset_inventory_skill_requires_declinations_and_valid_ledger() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    required_terms = (
        "capture-limits.txt",
        "first-class limit",
        "mapping-ledger.yaml",
        "every evidence file",
        "aptl aces-inventory validate",
        "aptl aces-inventory gaps",
        "aptl aces-inventory schema",
    )

    missing = [term for term in required_terms if term not in skill]

    assert not missing


def test_asset_inventory_skill_blocks_known_agent_failure_modes() -> None:
    skill = SKILL_PATH.read_text(encoding="utf-8")
    required_terms = (
        "no-smuggling",
        "no-force-fit",
        "lineage.md",
        "precedents.md",
        "primary literature",
        "no-solution-design",
        "is this state on a range node",
        "scenario state",
        "delivery infrastructure",
    )

    missing = [term for term in required_terms if term not in skill]

    assert not missing
