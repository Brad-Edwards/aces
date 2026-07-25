"""Semantic validation for DSL-124 authored evidence requirements."""

from __future__ import annotations


class _EvidenceRequirementsMixin:
    def _verify_evidence_requirements(self) -> None:
        for name, requirement in self._s.evidence_requirements.items():
            owner_label = f"Evidence requirement '{name}'"
            self._verify_evidence_requirement_refs(requirement.source_refs, owner_label, "source_ref")
            self._verify_evidence_requirement_refs(requirement.scope_refs, owner_label, "scope_ref")
            self._verify_evidence_requirement_refs(requirement.channel_refs, owner_label, "channel_ref")
            self._verify_evidence_requirement_ref(requirement.trigger_ref, owner_label, "trigger_ref")
            self._verify_evidence_requirement_ref(requirement.boundary_ref, owner_label, "boundary_ref")

    def _verify_evidence_requirement_refs(
        self,
        refs: list[str],
        owner_label: str,
        ref_label: str,
    ) -> None:
        for ref in refs:
            self._verify_evidence_requirement_ref(ref, owner_label, ref_label)

    def _verify_evidence_requirement_ref(
        self,
        ref: str,
        owner_label: str,
        ref_label: str,
    ) -> None:
        if not ref or self._is_unresolved_var(ref):
            return
        self._validate_named_ref(ref, owner_label=owner_label, ref_label=ref_label, targetable=True)
