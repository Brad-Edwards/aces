"""Semantic validation for ACT-617 mixed-control participant operation."""


class _MixedControlMixin:
    def _verify_mixed_control_semantics(self) -> None:
        for spec_name, behavior_spec in self._s.behavior_specifications.items():
            declaration = behavior_spec.mixed_control
            if behavior_spec.behavior_mode == "mixed-control" and declaration is None:
                self._err(f"Behavior specification '{spec_name}' mixed-control mode requires mixed_control")
            if declaration is not None and behavior_spec.behavior_mode != "mixed-control":
                self._err(f"Behavior specification '{spec_name}' mixed_control requires behavior_mode mixed-control")
            if declaration is None:
                continue
            label = f"Behavior specification '{spec_name}' mixed_control"
            if declaration.participant_ref not in behavior_spec.participant_refs:
                self._err(f"{label} must bind exactly one participant_ref owned by the behavior specification")
            if declaration.policy_revision != behavior_spec.semantic_version:
                self._err(f"{label} policy_revision must match the behavior specification semantic_version")
            named_index = self._named_ref_index()
            targetable_index = self._named_ref_index(targetable=True)
            owner_scope = self._resolved_mixed_control_refs(
                behavior_spec.authority_scope_refs,
                index=targetable_index,
            )
            for state_id, state in declaration.controller_states.items():
                controller_ref = declaration.participant_ref if state.controller_ref == "self" else state.controller_ref
                controller = self._s.agents.get(controller_ref)
                if controller is None:
                    self._err(
                        f"{label} controller state '{state_id}' controller_ref '{state.controller_ref}' "
                        "must reference a declared agent or self"
                    )
                    continue
                controller_authority = self._resolved_mixed_control_refs(
                    controller.authority_anchors,
                    index=named_index,
                )
                for ref in state.authority_basis_refs:
                    self._validate_named_ref(
                        ref,
                        owner_label=f"{label} controller state '{state_id}'",
                        ref_label="authority_basis_ref",
                    )
                    if not set(named_index.get(ref, ())).issubset(controller_authority):
                        self._err(
                            f"{label} controller state '{state_id}' authority basis '{ref}' "
                            f"is not declared by controller '{state.controller_ref}'"
                        )
                controller_scope = self._resolved_mixed_control_refs(
                    controller.operating_scope,
                    index=targetable_index,
                )
                for ref in state.scope_refs:
                    self._validate_named_ref(
                        ref,
                        owner_label=f"{label} controller state '{state_id}'",
                        ref_label="scope_ref",
                        targetable=True,
                    )
                    resolved = set(targetable_index.get(ref, ()))
                    if not resolved.issubset(owner_scope):
                        self._err(
                            f"{label} controller state '{state_id}' scope_ref '{ref}' "
                            "widens the behavior specification authority scope"
                        )
                    if not resolved.issubset(controller_scope):
                        self._err(
                            f"{label} controller state '{state_id}' scope_ref '{ref}' "
                            f"is outside controller '{state.controller_ref}' operating_scope"
                        )
                for ref in state.evidence_refs:
                    self._validate_named_ref(
                        ref,
                        owner_label=f"{label} controller state '{state_id}'",
                        ref_label="evidence_ref",
                    )
            initial_state = declaration.controller_states[declaration.initial_state_ref]
            if str(getattr(initial_state.authority_status, "value", initial_state.authority_status)) == "revoked":
                self._err(f"{label} initial state cannot use revoked authority")
            for transition_id, transition in declaration.transitions.items():
                from_state = declaration.controller_states[transition.from_state_ref]
                to_state = declaration.controller_states[transition.to_state_ref]
                if str(getattr(from_state.authority_status, "value", from_state.authority_status)) == "revoked":
                    self._err(f"{label} transition '{transition_id}' starts from revoked authority")
                if not from_state.valid_from_order <= transition.effective_order <= from_state.valid_until_order:
                    self._err(f"{label} transition '{transition_id}' is late for its from-state validity")
                if not to_state.valid_from_order <= transition.effective_order <= to_state.valid_until_order:
                    self._err(f"{label} transition '{transition_id}' precedes its to-state validity")
                if transition.proposal_ref is not None:
                    proposal = declaration.transitions[transition.proposal_ref]
                    if transition.from_state_ref != proposal.to_state_ref:
                        self._err(
                            f"{label} transition '{transition_id}' must start from its proposal's resulting state"
                        )
                    if transition.expected_state_revision != proposal.resulting_state_revision:
                        self._err(
                            f"{label} transition '{transition_id}' must expect its proposal's resulting state revision"
                        )
                kind = str(getattr(transition.transition_kind, "value", transition.transition_kind))
                if kind == "handoff":
                    if from_state.controller_ref == to_state.controller_ref:
                        self._err(f"{label} handoff transition '{transition_id}' must change controller")
                    if not transition.completion_evidence_refs:
                        self._err(f"{label} handoff transition '{transition_id}' requires completion evidence")
                for ref in (*transition.evidence_refs, *transition.completion_evidence_refs):
                    self._validate_named_ref(
                        ref,
                        owner_label=f"{label} transition '{transition_id}'",
                        ref_label="evidence_ref",
                    )

    @staticmethod
    def _resolved_mixed_control_refs(refs: list[str], *, index: dict[str, set[str]]) -> set[str]:
        resolved: set[str] = set()
        for ref in refs:
            resolved.update(index.get(ref, ()))
        return resolved
