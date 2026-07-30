"""Pure reference resolution for the governed adaptive-threshold profile."""

from __future__ import annotations

from operator import eq, ge, gt, le, lt, ne
from typing import Any

from ..canonical import canonical_json_digest
from ..diagnostics import DiagnosticModel
from .difficulty_adaptation import (
    DifficultyDecisionRecordModel,
    DifficultyDecisionRequestModel,
    DifficultyObservationInputModel,
    DifficultyPolicyModel,
    DifficultyThresholdRuleModel,
    difficulty_decision_history_head,
)
from .difficulty_provenance import DifficultyResolutionResultModel

_ADAPTIVE_THRESHOLD_PROFILE = {
    "profile_id": "adaptive-threshold-v1",
    "profile_version": "1.0.0",
    "rule_order": "ascending-priority-first-match",
    "operators": ["lt", "lte", "eq", "ne", "gte", "gt"],
    "unsupported_disposition": "unsupported",
}
ADAPTIVE_THRESHOLD_PROFILE_DIGEST = canonical_json_digest(_ADAPTIVE_THRESHOLD_PROFILE)
_SUPPORTED_EVALUATOR = (
    _ADAPTIVE_THRESHOLD_PROFILE["profile_id"],
    _ADAPTIVE_THRESHOLD_PROFILE["profile_version"],
    ADAPTIVE_THRESHOLD_PROFILE_DIGEST,
)
_OPERATORS = {"lt": lt, "lte": le, "eq": eq, "ne": ne, "gte": ge, "gt": gt}


def _diagnostic(code: str, address: str, message: str) -> DifficultyResolutionResultModel:
    return DifficultyResolutionResultModel(
        diagnostics=[
            DiagnosticModel(
                code=code,
                domain="difficulty",
                address=address,
                message=message,
            )
        ]
    )


def _request_fingerprint(request: DifficultyDecisionRequestModel) -> str:
    return canonical_json_digest(request.model_dump(mode="json"))


def _replay_or_conflict(
    request: DifficultyDecisionRequestModel,
    prior_decisions: list[DifficultyDecisionRecordModel],
    fingerprint: str,
) -> DifficultyResolutionResultModel | None:
    replay = next(
        (decision for decision in prior_decisions if decision.idempotency_key == request.idempotency_key),
        None,
    )
    if replay is None:
        return None
    if replay.request_fingerprint == fingerprint:
        return DifficultyResolutionResultModel(decision=replay)
    return _diagnostic(
        "difficulty.idempotency-conflict",
        "/idempotency_key",
        "The idempotency identity was already used for a different bounded decision request.",
    )


def _validate_history(
    request: DifficultyDecisionRequestModel,
    prior_decisions: list[DifficultyDecisionRecordModel],
) -> DifficultyResolutionResultModel | None:
    current_head = prior_decisions[-1].history_head if prior_decisions else None
    if request.expected_history_head != current_head:
        return _diagnostic(
            "difficulty.history-conflict",
            "/expected_history_head",
            "The expected adaptive-decision history head is stale.",
        )
    if prior_decisions:
        previous = prior_decisions[-1]
        same_order = (
            previous.state_cut.order_domain == request.state_cut.order_domain
            and previous.state_cut.episode_id == request.state_cut.episode_id
        )
        if not same_order or request.state_cut.coordinate <= previous.state_cut.coordinate:
            return _diagnostic(
                "difficulty.state-cut-conflict",
                "/state_cut",
                "The adaptive-decision state cut must advance the current run episode order.",
            )
    return None


def _validate_prior_history(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
    prior_decisions: list[DifficultyDecisionRecordModel],
) -> DifficultyResolutionResultModel | None:
    prior_head: str | None = None
    prior_cut = None
    for decision in prior_decisions:
        same_policy = (
            decision.policy_id == policy.policy_id
            and decision.policy_version == policy.policy_version
            and decision.policy_digest == policy.policy_digest
        )
        same_scope = (
            decision.run_id == request.run_id
            and decision.state_cut.order_domain == request.state_cut.order_domain
            and decision.state_cut.episode_id == request.state_cut.episode_id
        )
        if (
            decision.prior_history_head != prior_head
            or not same_policy
            or not same_scope
            or (prior_cut is not None and decision.state_cut.coordinate <= prior_cut)
        ):
            return _diagnostic(
                "difficulty.history-conflict",
                "/expected_history_head",
                "The supplied adaptive-decision history is discontinuous or belongs to another scope.",
            )
        prior_head = decision.history_head
        prior_cut = decision.state_cut.coordinate
    return None


def _validate_policy_identity(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
) -> DifficultyResolutionResultModel | None:
    if (
        request.policy_id != policy.policy_id
        or request.policy_version != policy.policy_version
        or request.policy_digest != policy.policy_digest
    ):
        return _diagnostic(
            "difficulty.policy-mismatch",
            "/policy_id",
            "The decision request does not match the declared policy identity.",
        )
    return None


def _validate_observations(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
) -> DifficultyResolutionResultModel | None:
    inputs = {item.source_id: item for item in request.observation_inputs}
    if set(inputs) != set(policy.observation_sources):
        return _diagnostic(
            "difficulty.observation-set-mismatch",
            "/observation_inputs",
            "The decision request must supply exactly the policy's declared observation sources.",
        )
    for source_id, item in inputs.items():
        source = policy.observation_sources[source_id]
        same_scope = (
            item.run_id == request.run_id
            and item.observed_cut.episode_id == request.state_cut.episode_id
            and item.observed_cut.order_domain == request.state_cut.order_domain
        )
        age = request.state_cut.coordinate - item.observed_cut.coordinate
        if not same_scope or age < 0 or age > source.maximum_age:
            return _diagnostic(
                "difficulty.observation-cut-invalid",
                "/observation_inputs",
                "An observation input is outside the declared run, episode, order, or freshness boundary.",
            )
    return None


def _compare(rule: DifficultyThresholdRuleModel, observation: DifficultyObservationInputModel) -> bool:
    comparator = _OPERATORS[rule.operator]
    if rule.operator in {"lt", "lte", "gte", "gt"}:
        if isinstance(observation.value, bool) or isinstance(rule.threshold, bool):
            return False
        if not isinstance(observation.value, (int, float)) or not isinstance(rule.threshold, (int, float)):
            return False
    try:
        return bool(comparator(observation.value, rule.threshold))
    except TypeError:
        return False


def _selected_rule(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
) -> DifficultyThresholdRuleModel | None:
    inputs = {item.source_id: item for item in request.observation_inputs}
    ordered_rules = sorted(policy.threshold_rules.values(), key=lambda rule: rule.priority)
    return next(
        (rule for rule in ordered_rules if _compare(rule, inputs[rule.observation_source_id])),
        None,
    )


def _decision_payload(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
    prior_head: str | None,
    fingerprint: str,
    disposition: str,
    selected_rule: DifficultyThresholdRuleModel | None,
) -> dict[str, Any]:
    action = policy.actions[selected_rule.action_id] if selected_rule is not None else None
    return {
        "decision_id": f"difficulty-decision-{fingerprint.removeprefix('sha256:')[:24]}",
        "idempotency_key": request.idempotency_key,
        "request_fingerprint": fingerprint,
        "prior_history_head": prior_head,
        "policy_id": policy.policy_id,
        "policy_version": policy.policy_version,
        "policy_digest": policy.policy_digest,
        "run_id": request.run_id,
        "state_cut": request.state_cut.model_dump(mode="json"),
        "observation_refs": [item.model_dump(mode="json", exclude={"value"}) for item in request.observation_inputs],
        "trigger_rule_id": selected_rule.rule_id if selected_rule is not None else None,
        "selected_action_id": selected_rule.action_id if selected_rule is not None else None,
        "affected_refs": (
            [reference.model_dump(mode="json") for reference in action.affected_refs] if action is not None else []
        ),
        "disposition": disposition,
        "decided_at": request.requested_at,
        "validity_effect": policy.validity_effect,
    }


def _seal_decision(payload: dict[str, Any]) -> DifficultyDecisionRecordModel:
    history_head = difficulty_decision_history_head(payload)
    return DifficultyDecisionRecordModel.model_validate({**payload, "history_head": history_head})


def _bounded_disposition(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
    prior_decisions: list[DifficultyDecisionRecordModel],
) -> str | None:
    if request.intervention_count >= policy.bounds.maximum_interventions:
        return "terminal"
    if prior_decisions:
        distance = request.state_cut.coordinate - prior_decisions[-1].state_cut.coordinate
        if distance < policy.bounds.minimum_decision_interval:
            return "denied"
        last_selected = next(
            (decision for decision in reversed(prior_decisions) if decision.disposition == "selected"),
            None,
        )
        if (
            last_selected is not None
            and request.state_cut.coordinate - last_selected.state_cut.coordinate < policy.bounds.cooldown
        ):
            return "denied"
    return None


def resolve_difficulty_policy(
    policy: DifficultyPolicyModel,
    request: DifficultyDecisionRequestModel,
    *,
    prior_decisions: list[DifficultyDecisionRecordModel],
) -> DifficultyResolutionResultModel:
    """Resolve one exact-cut decision without performing or dispatching the effect."""

    fingerprint = _request_fingerprint(request)
    for validation in (
        _validate_policy_identity(policy, request),
        _validate_prior_history(policy, request, prior_decisions),
    ):
        if validation is not None:
            return validation
    replay_result = _replay_or_conflict(request, prior_decisions, fingerprint)
    if replay_result is not None:
        return replay_result
    history_validation = _validate_history(request, prior_decisions)
    if history_validation is not None:
        return history_validation
    prior_head = prior_decisions[-1].history_head if prior_decisions else None
    if policy.condition == "fixed":
        if request.observation_inputs or request.intervention_count:
            return _diagnostic(
                "difficulty.fixed-authority-invalid",
                "/observation_inputs",
                "Fixed difficulty requests must not supply adaptive observations or intervention state.",
            )
        payload = _decision_payload(policy, request, prior_head, fingerprint, "fixed", None)
        return DifficultyResolutionResultModel(decision=_seal_decision(payload))
    assert policy.evaluator_ref is not None
    evaluator_identity = (
        policy.evaluator_ref.ref_id,
        policy.evaluator_ref.ref_version,
        policy.evaluator_ref.ref_digest,
    )
    if evaluator_identity != _SUPPORTED_EVALUATOR:
        payload = _decision_payload(policy, request, prior_head, fingerprint, "unsupported", None)
        return DifficultyResolutionResultModel(decision=_seal_decision(payload))
    observation_error = _validate_observations(policy, request)
    if observation_error is not None:
        return observation_error
    bounded = _bounded_disposition(policy, request, prior_decisions)
    if bounded is not None:
        payload = _decision_payload(policy, request, prior_head, fingerprint, bounded, None)
        return DifficultyResolutionResultModel(decision=_seal_decision(payload))
    selected = _selected_rule(policy, request)
    disposition = "selected" if selected is not None else "no-change"
    payload = _decision_payload(policy, request, prior_head, fingerprint, disposition, selected)
    return DifficultyResolutionResultModel(decision=_seal_decision(payload))


__all__ = ["ADAPTIVE_THRESHOLD_PROFILE_DIGEST", "resolve_difficulty_policy"]
