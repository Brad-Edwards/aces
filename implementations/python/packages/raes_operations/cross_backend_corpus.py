"""Cross-backend evidence corpus producer (issue #600).

Assembles the backend-paired demonstration corpus for the RAES reference
scenario: one libvirt reference-backend realization and one APTL realization of the
*same authored scenario*, compared through an inspectable cross-backend invariant
ledger (``aces.cross-backend-evidence-corpus/v1``).

The corpus is a thin **local** artifact that composes existing surfaces (issue #600
preflight): it consumes the real ``aces.libvirt.scenario-evidence-run/v1`` artifact
through ``run_libvirt_evidence_run`` (deterministic mode -- no libvirt daemon) and
records the APTL realization as a bounded, honestly-labeled summary + link to
Brad-Edwards/aptl#558 (or, when an operator supplies one, its allowlisted portable
projection). It is not a new published contract, a leaderboard, or an equivalence
proof.

Determinism: only portable, timestamp-free fields cross from the libvirt artifact
into the corpus, so the built artifact is byte-stable and the committed corpus under
``examples/corpus/reference-demonstration/`` is drift-testable. The full timestamped
libvirt evidence stays in its own regenerable run archive.

ADR-036 module boundary: this orchestrates only ``raes_operations`` producers and
the shared ``run_artifacts`` writer; assembly/ledger/validation live in the
``_cross_backend_corpus_*`` modules to stay under the ADR-015 source-size cap.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from raes_operations._cross_backend_corpus_backend_runs import build_aptl_backend_run, build_libvirt_backend_run
from raes_operations._cross_backend_corpus_ledger import build_invariant_ledger
from raes_operations._cross_backend_corpus_validation import (
    CORPUS_SCHEMA,
    validate_cross_backend_corpus_artifact,
)
from raes_operations.libvirt_evidence_run import (
    EvidenceCheck,
    LibvirtEvidenceRunConfig,
    run_libvirt_evidence_run,
)
from raes_operations.run_artifacts import atomic_write_json_artifact

__all__ = [
    "CORPUS_SCHEMA",
    "EvidenceCheck",
    "CrossBackendCorpusConfig",
    "CrossBackendCorpusReport",
    "build_cross_backend_corpus",
    "validate_cross_backend_corpus_artifact",
    "write_cross_backend_corpus_artifact",
]

# The four issue #600 non-claims, carried verbatim in the corpus.
_NON_CLAIMS: tuple[str, ...] = (
    "No autonomous-agent capability benchmark claim.",
    "No claim that Wazuh detection quality is evaluated.",
    "No model-defense robustness claim.",
    "No full semantic equivalence across backends beyond the checked invariant ledger.",
)

_LINKS: dict[str, str] = {
    "issue": "RAESystem/rae#600",
    "authored_scenario_issue": "RAESystem/rae#598",
    "libvirt_participant_runtime": "RAESystem/rae#614",
    "libvirt_evidence": "RAESystem/rae#615",
    "aptl_evidence": "Brad-Edwards/aptl#558",
}

_REDACTION_PROVENANCE: dict[str, Any] = {
    "policy": (
        "The corpus copies only portable, bounded RAES-side facts from each backend run: authored scenario "
        "identity/digest, compiled RAES address sets, backend id/capability profile, topology basis and network "
        "attachment matrix, per-surface evidence coverage, and disclosed limitations. Backend-private semantics are "
        "never recorded."
    ),
    "redacted_field_classes": [
        "raw-libvirt-xml",
        "domain-uuid",
        "qemu-command-line",
        "host-path",
        "connection-uri",
        "credential",
        "private-key",
        "aptl-container-id",
        "compose-service-name",
        "docker-inspect-payload",
        "raw-wazuh-rule-body",
    ],
    "provenance_refs": [
        "docs/decisions/issue-600-paper-demonstration-corpus-preflight.md",
        "docs/decisions/issue-615-libvirt-paper-evidence-preflight.md",
        "examples/scenarios/enterprise-participant-evidence-loop.README.md",
    ],
}


@dataclass(frozen=True)
class CrossBackendCorpusConfig:
    """Runtime controls for the cross-backend evidence corpus producer."""

    aptl_evidence_path: Path | None = None
    libvirt_run_id: str = "cross-backend-corpus-libvirt"


@dataclass(frozen=True)
class CrossBackendCorpusReport:
    """Rendered outcome for the cross-backend evidence corpus producer."""

    scenario: str
    checks: tuple[EvidenceCheck, ...]
    artifact: dict[str, Any] | None = None
    artifact_path: str | None = None

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)

    def render(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        lines = [f"cross-backend evidence corpus -- scenario={self.scenario}: {status}"]
        for check in self.checks:
            marker = "ok" if check.passed else "FAIL"
            lines.append(f"  [{marker}] {check.name}")
            for diagnostic in check.diagnostics:
                lines.append(f"        - {diagnostic}")
        if self.artifact_path:
            lines.append(f"  artifact: {self.artifact_path}")
        return "\n".join(lines)


def _assemble_corpus(
    artifact: dict[str, Any],
    libvirt_run: dict[str, Any],
    aptl_run: dict[str, Any],
    ledger: dict[str, Any],
) -> dict[str, Any]:
    scenario_section = artifact.get("scenario", {})
    compiled = artifact.get("compiled_artifact", {})
    return {
        "schema": CORPUS_SCHEMA,
        "corpus": {
            "name": "enterprise-participant-evidence-loop-n2",
            "claim": (
                "n=2 independent backend realizations (libvirt reference backend + APTL) of the same authored RAES "
                "reference scenario, compared through an inspectable invariant ledger."
            ),
        },
        "authored_scenario": scenario_section,
        "compiled_address_sets": compiled.get("compiled_address_sets", {}),
        "compiled_model_fingerprint": compiled.get("compiled_model_fingerprint", ""),
        "backend_runs": [libvirt_run, aptl_run],
        "invariant_ledger": ledger,
        "non_claims": list(_NON_CLAIMS),
        "redaction_provenance": _REDACTION_PROVENANCE,
        "links": dict(_LINKS),
    }


def build_cross_backend_corpus(
    *,
    scenario_path: Path,
    project_dir: Path,
    config: CrossBackendCorpusConfig | None = None,
) -> CrossBackendCorpusReport:
    """Build the cross-backend evidence corpus artifact for ``scenario_path``.

    Runs the libvirt scenario evidence producer in deterministic mode, projects both
    backend realizations into portable descriptors, computes the invariant ledger,
    assembles and validates the corpus. The returned report's ``artifact`` is set
    only when every gating check passes.
    """
    settings = config or CrossBackendCorpusConfig()
    checks: list[EvidenceCheck] = []

    libvirt_report = run_libvirt_evidence_run(
        scenario_path=scenario_path,
        project_dir=project_dir,
        run_id=settings.libvirt_run_id,
        config=LibvirtEvidenceRunConfig(evidence_source_mode="deterministic"),
    )
    libvirt_failures = tuple(
        f"{check.name}: {'; '.join(check.diagnostics)}" for check in libvirt_report.checks if not check.passed
    )
    checks.append(EvidenceCheck("libvirt_evidence_run", libvirt_report.passed, libvirt_failures))
    if not libvirt_report.passed or libvirt_report.artifact is None:
        return CrossBackendCorpusReport(scenario_path.name, tuple(checks))

    artifact = libvirt_report.artifact
    libvirt_run = build_libvirt_backend_run(artifact)
    scenario_section = artifact.get("scenario", {})
    address_sets = artifact.get("compiled_artifact", {}).get("compiled_address_sets", {})
    aptl_run, aptl_diagnostics = build_aptl_backend_run(scenario_section, address_sets, settings.aptl_evidence_path)
    checks.append(EvidenceCheck("aptl_evidence_descriptor", not aptl_diagnostics, tuple(aptl_diagnostics)))

    ledger = build_invariant_ledger(libvirt_run, aptl_run)
    corpus = _assemble_corpus(artifact, libvirt_run, aptl_run, ledger)
    violations = validate_cross_backend_corpus_artifact(corpus)
    checks.append(EvidenceCheck("corpus_contract_validation", not violations, tuple(violations)))
    # Materialize the artifact only when EVERY gating check passes -- including the
    # APTL descriptor check. A bad operator-supplied APTL export (unreadable, or with
    # divergent scenario/address invariants) must not leave a writable summary that
    # silently overwrites the corpus.
    all_passed = all(check.passed for check in checks)
    return CrossBackendCorpusReport(scenario_path.name, tuple(checks), corpus if all_passed else None)


def write_cross_backend_corpus_artifact(artifact: dict[str, Any], output_path: Path) -> str:
    """Atomically write the corpus artifact as canonical JSON; return the written path."""
    atomic_write_json_artifact(output_path, artifact)
    return str(output_path)
