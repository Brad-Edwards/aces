"""Reference participant runtime: RUN-311 episode lifecycle transitions.

Each control method advances the current ``participant_episode_results``
entry in lockstep with append-only history events, so the resulting
snapshot always satisfies ``iter_participant_episode_snapshot_violations``:
identity is stable across resets/restarts, history is append-only, and the
current result is the head of the history chain. Independent of the stub.
"""

from __future__ import annotations

from raes_backend_protocols.participant_runtime_base import BaseParticipantRuntime


class ReferenceParticipantRuntime(BaseParticipantRuntime):
    """In-process participant runtime driving RUN-311 transitions.

    Delegates the full episode lifecycle to ``BaseParticipantRuntime``. No
    domain side-effects are injected — this runtime is intended for reference
    and testing use where no real infrastructure is required.
    """

    def participant_relation_probe(
        self,
        *,
        relation_id: str,
        profile_id: str,
        profile_revision: str,
        possible_point_ref: str,
    ) -> dict[str, object]:
        """Expose the closed reference observation transcript to conformance.

        This is an in-process backend probe, not a public control-plane route.
        It accepts only the exact finite opacity profile and its two governed
        points, then returns the complete non-secret observation normal form.
        """

        expected = (
            relation_id == "participant-predicate-opacity"
            and profile_id == "participant-opacity-runtime-reference-v1"
            and profile_revision == "sem-231/runtime-rev2"
            and possible_point_ref
            in {
                "possible-point:runtime-reference-protected",
                "possible-point:runtime-reference-complement",
            }
        )
        if not expected:
            raise ValueError("unsupported participant relation probe coordinates")
        return {
            "decision": "deny",
            "failure": "uniform-refusal",
            "action_availability": "denied",
            "delivery": "withheld",
            "omission": "recorded-at-governed-opportunity",
            "retry": "stable-replay",
            "logical_timing": "logical-bucket:contained",
            "logical_order": "stable-causal-order",
            "policy_release_effect": "contained",
            "external_effect": "none",
            "payload_released": False,
        }
