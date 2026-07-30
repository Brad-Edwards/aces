from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CLAUDE_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "raes-asset-inventory-capture"
CODEX_SKILL_DIR = REPO_ROOT / ".codex-skills" / "raes-asset-inventory-capture"
GAP_CLAUDE_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "raes-gap-remediation-implement"
GAP_CODEX_SKILL_DIR = REPO_ROOT / ".codex-skills" / "raes-gap-remediation-implement"
SKILL_PATHS = (
    CLAUDE_SKILL_DIR / "SKILL.md",
    CODEX_SKILL_DIR / "SKILL.md",
)
TEMPLATE_PATHS = (
    CLAUDE_SKILL_DIR / "scripts" / "capture-container-evidence-template.sh",
    CODEX_SKILL_DIR / "scripts" / "capture-container-evidence-template.sh",
)
GAP_SKILL_PATHS = (
    GAP_CLAUDE_SKILL_DIR / "SKILL.md",
    GAP_CODEX_SKILL_DIR / "SKILL.md",
)
AGENT_RULES_PATH = REPO_ROOT / "AGENTS.md"


def test_asset_inventory_skill_is_cross_agent_and_discoverable_by_codex() -> None:
    claude_skill = (CLAUDE_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_skill = (CODEX_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    agent_rules = AGENT_RULES_PATH.read_text(encoding="utf-8")

    assert "TODO" not in claude_skill
    assert "TODO" not in codex_skill
    assert claude_skill == codex_skill
    assert "from either Claude Code or Codex" in claude_skill
    assert "raes-asset-inventory-capture" in agent_rules
    assert ".codex-skills/raes-asset-inventory-capture/SKILL.md" in agent_rules
    assert ".claude/skills/raes-asset-inventory-capture/SKILL.md" in agent_rules
    assert "~/.codex/skills/raes-asset-inventory-capture" in agent_rules
    assert "~/.claude/skills/raes-asset-inventory-capture" in agent_rules


def test_asset_inventory_skill_metadata_is_agent_runnable() -> None:
    for skill_path in SKILL_PATHS:
        skill = skill_path.read_text(encoding="utf-8")
        openai_yaml = (skill_path.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")

        assert "name: raes-asset-inventory-capture" in skill
        assert "description: Run the RAES asset inventory methodology" in skill
        assert "default_prompt:" in openai_yaml
        assert "$raes-asset-inventory-capture" in openai_yaml


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
        "aptl raes-inventory validate",
        "aptl raes-inventory gaps",
        "aptl raes-inventory schema",
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


def test_asset_inventory_skill_preserves_scenario_target_secrets() -> None:
    skills = [path.read_text(encoding="utf-8") for path in SKILL_PATHS]
    required_terms = (
        "scenario-target secrets",
        "capture facts",
        "must not be redacted",
        "operator/out-of-scenario",
        "internal_users.yml",
        "bcrypt hashes",
    )
    stale_terms = (
        "Hash and redact before committing",
        "Participant-visible fixture secrets may be retained only",
        "Do not place credentials, bearer tokens, private keys, generated service secrets",
    )

    missing = [
        (path, term)
        for path, skill in zip(SKILL_PATHS, skills, strict=True)
        for term in required_terms
        if term not in skill
    ]
    stale = [
        (path, term) for path, skill in zip(SKILL_PATHS, skills, strict=True) for term in stale_terms if term in skill
    ]

    assert not missing
    assert not stale


def test_asset_inventory_container_template_preserves_target_values_by_default() -> None:
    claude_template = TEMPLATE_PATHS[0].read_text(encoding="utf-8")
    codex_template = TEMPLATE_PATHS[1].read_text(encoding="utf-8")

    assert claude_template == codex_template
    assert 'CAPTURE_BOUNDARY="${CAPTURE_BOUNDARY:-}"' in claude_template
    assert "CAPTURE_BOUNDARY=scenario-target" in claude_template
    assert 'OPERATOR_SECRET_NAME_REGEX="${OPERATOR_SECRET_NAME_REGEX:-}"' in claude_template
    assert 'SECRET_NAME_REGEX="${SECRET_NAME_REGEX:-' not in claude_template
    assert "preserves scenario-target values by default" in claude_template
    assert "operator/out-of-scenario" in claude_template


def test_gap_remediation_skill_is_cross_agent_and_discoverable_by_codex() -> None:
    claude_skill = (GAP_CLAUDE_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    codex_skill = (GAP_CODEX_SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    agent_rules = AGENT_RULES_PATH.read_text(encoding="utf-8")

    assert "TODO" not in claude_skill
    assert "TODO" not in codex_skill
    assert claude_skill == codex_skill
    assert "raes-gap-remediation-implement" in agent_rules
    assert ".codex-skills/raes-gap-remediation-implement/SKILL.md" in agent_rules
    assert ".claude/skills/raes-gap-remediation-implement/SKILL.md" in agent_rules
    assert "~/.codex/skills/raes-gap-remediation-implement" in agent_rules
    assert "~/.claude/skills/raes-gap-remediation-implement" in agent_rules


def test_gap_remediation_skill_metadata_is_agent_runnable() -> None:
    for skill_path in GAP_SKILL_PATHS:
        skill = skill_path.read_text(encoding="utf-8")
        openai_yaml = (skill_path.parent / "agents" / "openai.yaml").read_text(encoding="utf-8")

        assert "name: raes-gap-remediation-implement" in skill
        assert "description: Architecture-first overlay" in skill
        assert "default_prompt:" in openai_yaml
        assert "$raes-gap-remediation-implement" in openai_yaml


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
