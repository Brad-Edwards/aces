from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "aces-asset-inventory-capture"
CODEX_SKILL_DIR = REPO_ROOT / ".codex-skills" / "aces-asset-inventory-capture"
GAP_CLAUDE_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "aces-gap-remediation-implement"
GAP_CODEX_SKILL_DIR = REPO_ROOT / ".codex-skills" / "aces-gap-remediation-implement"
SKILL_PATHS = (
    CLAUDE_SKILL_DIR / "SKILL.md",
    CODEX_SKILL_DIR / "SKILL.md",
)
GAP_SKILL_PATHS = (
    GAP_CLAUDE_SKILL_DIR / "SKILL.md",
    GAP_CODEX_SKILL_DIR / "SKILL.md",
)
CODEX_RULES_PATH = REPO_ROOT / ".codex"


def test_asset_inventory_skill_is_cross_agent_and_discoverable_by_codex() -> None:
    claude_skill = (CLAUDE_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_skill = (CODEX_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_rules = CODEX_RULES_PATH.read_text(encoding="utf-8")

    assert "TODO" not in claude_skill
    assert "TODO" not in codex_skill
    assert claude_skill == codex_skill
    assert "from either Claude Code or Codex" in claude_skill
    assert "aces-asset-inventory-capture" in codex_rules
    assert ".codex-skills/aces-asset-inventory-capture/SKILL.md" in codex_rules
    assert ".claude/skills/aces-asset-inventory-capture/SKILL.md" in codex_rules
    assert "~/.codex/skills/aces-asset-inventory-capture" in codex_rules
    assert "~/.claude/skills/aces-asset-inventory-capture" in codex_rules


def test_asset_inventory_skill_metadata_is_agent_runnable() -> None:
    for skill_path in SKILL_PATHS:
        skill = skill_path.read_text(encoding="utf-8")
        openai_yaml = (skill_path.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")

        assert "name: aces-asset-inventory-capture" in skill
        assert "description: Run the ACES asset inventory methodology" in skill
        assert "default_prompt:" in openai_yaml
        assert "$aces-asset-inventory-capture" in openai_yaml


def test_asset_inventory_skill_encodes_methodology_tool_baseline() -> None:
    skills = [path.read_text(encoding="utf-8") for path in SKILL_PATHS]
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

    missing = [
        (path, term)
        for path, skill in zip(SKILL_PATHS, skills, strict=True)
        for term in required_terms
        if term not in skill
    ]

    assert not missing


def test_asset_inventory_skill_requires_declinations_and_valid_ledger() -> None:
    skills = [path.read_text(encoding="utf-8") for path in SKILL_PATHS]
    required_terms = (
        "capture-limits.txt",
        "first-class limit",
        "mapping-ledger.yaml",
        "every evidence file",
        "aptl aces-inventory validate",
        "aptl aces-inventory gaps",
        "aptl aces-inventory schema",
    )

    missing = [
        (path, term)
        for path, skill in zip(SKILL_PATHS, skills, strict=True)
        for term in required_terms
        if term not in skill
    ]

    assert not missing


def test_asset_inventory_skill_blocks_known_agent_failure_modes() -> None:
    skills = [path.read_text(encoding="utf-8") for path in SKILL_PATHS]
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

    missing = [
        (path, term)
        for path, skill in zip(SKILL_PATHS, skills, strict=True)
        for term in required_terms
        if term not in skill
    ]

    assert not missing


def test_gap_remediation_skill_is_cross_agent_and_discoverable_by_codex() -> None:
    claude_skill = (GAP_CLAUDE_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_skill = (GAP_CODEX_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_rules = CODEX_RULES_PATH.read_text(encoding="utf-8")

    assert "TODO" not in claude_skill
    assert "TODO" not in codex_skill
    assert claude_skill == codex_skill
    assert "aces-gap-remediation-implement" in codex_rules
    assert ".codex-skills/aces-gap-remediation-implement/SKILL.md" in codex_rules
    assert ".claude/skills/aces-gap-remediation-implement/SKILL.md" in codex_rules
    assert "~/.codex/skills/aces-gap-remediation-implement" in codex_rules
    assert "~/.claude/skills/aces-gap-remediation-implement" in codex_rules


def test_gap_remediation_skill_metadata_is_agent_runnable() -> None:
    for skill_path in GAP_SKILL_PATHS:
        skill = skill_path.read_text(encoding="utf-8")
        openai_yaml = (skill_path.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")

        assert "name: aces-gap-remediation-implement" in skill
        assert "description: Architecture-first overlay" in skill
        assert "default_prompt:" in openai_yaml
        assert "$aces-gap-remediation-implement" in openai_yaml


def test_gap_remediation_skill_encodes_overlay_contract() -> None:
    skills = [path.read_text(encoding="utf-8") for path in GAP_SKILL_PATHS]
    required_terms = (
        "overlay before the normal Ground Control implementation",
        "does not replace `/implement`",
        "academic peer review for tier-1 publication",
        "Remediation Brief",
        "Gap Claim",
        "Existing Surface Audit",
        "Lineage and Precedent",
        "Literature and Practice",
        "Alternatives",
        "Chosen Architecture",
        "Documentation Defense",
        "Verification Plan",
        "Whole-Surface Gate",
        "Anti-Local-Optimization Gates",
        "duplicate parallel surfaces",
        "primary literature",
        "No downstream-only fix",
        "Delegation to Ground Control",
        "workflow-improvement recommendations",
    )

    missing = [
        (path, term)
        for path, skill in zip(GAP_SKILL_PATHS, skills, strict=True)
        for term in required_terms
        if term not in skill
    ]

    assert not missing
