#!/usr/bin/env python3
# ruff: noqa: E402, I001
"""Prove that the normative SDL catalogs cover the live language surface.

The published schema and normative prose remain independently governed
authorities. This read-only check compares both with the reference
implementation registries so drift is reported instead of silently generated
away.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import types
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_PACKAGES = REPO_ROOT / "implementations" / "python" / "packages"
for import_root in (REPO_ROOT, PYTHON_PACKAGES):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from raes._language_metadata import REFERENCE_COMPLETION_TARGETS
from raes._mapping_scopes import HASHMAP_SECTIONS
from raes._module_symbols import HASHMAP_SECTIONS as MODULE_HASHMAP_SECTIONS
from raes._runtime_service_families import (
    RUNTIME_SERVICE_FAMILIES,
    RuntimeReferenceChild,
)
from raes.phase_contracts import ExpansionProvenance, InstantiationProvenance
from raes.scenario import (
    ExpandedScenario,
    InstantiatedScenario,
    Scenario,
    ScenarioContent,
)
from tools.policy.common import (
    PolicyFailure,
    apply_exceptions,
    failures_to_json,
    load_exceptions,
)

SECTIONS_PATH = "specs/sdl/sections.md"
REFERENCES_PATH = "specs/sdl/references.md"
RUNTIME_PATH = "specs/sdl/runtime-inventory.md"
DOCUMENT_MODEL_PATH = "specs/sdl/document-model.md"
VARIABLES_PATH = "specs/sdl/variables-and-instantiation.md"
DIAGNOSTICS_PATH = "specs/sdl/diagnostics.md"
PHASES_PATH = "specs/formal/sdl-phases/README.md"
SCHEMA_PATH = "contracts/schemas/sdl/sdl-authoring-input-v1.json"

_TOP_LEVEL_HEADING = "## Complete top-level field catalog"
_REFERENCE_HEADING = "## 6. Machine-checkable reference-edge index"
_RUNTIME_HEADING = "## 2. Family index"
_PHASE_HEADING = "## Phase-specific member catalog"
_SUMMARY_RE = re.compile(
    r"<!-- sdl-catalog-summary "
    r"top-level=(?P<top>\d+) metadata-composition=(?P<meta>\d+) "
    r"sections=(?P<sections>\d+) maps=(?P<maps>\d+) lists=(?P<lists>\d+) -->"
)
_SEPARATOR_RE = re.compile(r"^:?-{2,}:?$")
_BACKTICK_RE = re.compile(r"`([^`]+)`")
_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\((?P<target>[^)]+)\)")
_IMPLEMENTATION_TERM_RE = re.compile(
    r"\b(?:Python|Pydantic|ValidationError|SDLParseError|SDLInstantiationError|SDLValidationError|"
    r"SDLMigrationPolicy)\b"
)
_VALID_KINDS = frozenset({"metadata", "composition", "section"})
_VALID_SHAPES = frozenset({"scalar", "mapping", "map", "list"})
_VALID_LIFECYCLE = frozenset({"normalized", "expanded", "instantiated"})
_MAX_CATALOG_BYTES = 512 * 1024
_MAX_CATALOG_ROWS = 512
_METADATA_FIELDS = frozenset({"name", "version", "description"})
_COMPOSITION_FIELDS = frozenset({"module", "imports", "realization"})

_NODE_VALIDATOR = "[node validator](../../implementations/python/packages/raes/validator/_nodes_infra_network.py)"
_INFRASTRUCTURE_VALIDATOR = (
    "[infrastructure validator](../../implementations/python/packages/raes/validator/_nodes_infra_network.py)"
)
_SECTION_VALIDATOR = "[section validator](../../implementations/python/packages/raes/validator/_sections.py)"
_CONTENT_VALIDATOR = "[content validator](../../implementations/python/packages/raes/validator/_content_objectives.py)"
_SERVICE_MATERIALIZATION_VALIDATOR = (
    "[service materialization validator]"
    "(../../implementations/python/packages/raes/validator/_service_materialization.py)"
)
_CONTENT_COMPILER = "[content compiler](../../implementations/python/packages/raes_processor/compiler/placement.py)"
_ACCOUNT_VALIDATOR = "[account validator](../../implementations/python/packages/raes/validator/_content_objectives.py)"
_STATEFUL_MODEL = "[scenario model](../../implementations/python/packages/raes/scenario.py)"
_RELATIONSHIP_VALIDATOR = (
    "[relationship validator](../../implementations/python/packages/raes/validator/_relationships.py)"
)
_RELATIONSHIP_PROXY_VALIDATOR = (
    "[proxy relationship validator](../../implementations/python/packages/raes/validator/_relationships_proxy.py)"
)
_MAIL_VALIDATOR = "[mail validator](../../implementations/python/packages/raes/validator/_runtime_mail.py)"
_DOMAIN_TOPOLOGY_SEMANTICS = (
    "[domain topology semantics](../../implementations/python/packages/raes/semantics/domain_topology.py)"
)
_ENTERPRISE_IDENTITY_SEMANTICS = (
    "[enterprise identity semantics](../../implementations/python/packages/raes/semantics/enterprise_identity.py)"
)
_DEPLOYMENT_TENANCY_SEMANTICS = (
    "[deployment tenancy semantics](../../implementations/python/packages/raes/semantics/deployment_tenancy.py)"
)
_PARTICIPANT_VALIDATOR = (
    "[participant validator](../../implementations/python/packages/raes/validator/_content_objectives.py)"
)
_PARTICIPANT_SEMANTICS = (
    "[participant semantics](../../implementations/python/packages/raes/semantics/participant_behavior/__init__.py)"
)
_PARTICIPANT_INTERACTIVE_ACCESS_SEMANTICS = (
    "[participant interactive-access semantics]"
    "(../../implementations/python/packages/raes/semantics/participant_interactive_access.py)"
)
_OUTCOME_SEMANTICS = "[outcome semantics](../../implementations/python/packages/raes/semantics/participant_outcome.py)"
_BEHAVIOR_SEMANTICS = (
    "[behavior semantics](../../implementations/python/packages/raes/semantics/participant_behavior/__init__.py)"
)
_BEHAVIOR_VALIDATOR = (
    "[behavior validator](../../implementations/python/packages/raes/validator/_content_objectives.py)"
)
_MIXED_CONTROL_VALIDATOR = (
    "[behavior validator](../../implementations/python/packages/raes/validator/_mixed_control.py)"
)
_TOOL_AFFORDANCE_VALIDATOR = (
    "[tool-affordance validator](../../implementations/python/packages/raes/validator/_participant_tool_affordances.py)"
)
_PARTICIPANT_INJECT_DELIVERY_VALIDATOR = (
    "[participant-inject delivery validator]"
    "(../../implementations/python/packages/raes/validator/_participant_inject_deliveries.py)"
)
_BEHAVIOR_MODEL = "[behavior model](../../implementations/python/packages/raes/participant_behavior/__init__.py)"
_MIXED_CONTROL_MODEL = (
    "[behavior model](../../implementations/python/packages/raes/participant_behavior_specification.py)"
)
_EVIDENCE_VALIDATOR = (
    "[evidence validator](../../implementations/python/packages/raes/validator/_evidence_requirements.py)"
)
_OBJECTIVE_SEMANTICS = (
    "[objective semantics](../../implementations/python/packages/raes/semantics/objective_semantics/__init__.py)"
)
_WORKFLOW_SEMANTICS = "[workflow validator](../../implementations/python/packages/raes/validator/_workflows_verify.py)"
_PROPOSITION_VALIDATOR = (
    "[proposition validator](../../implementations/python/packages/raes/validator/_propositions.py)"
)
_VARIATION_VALIDATOR = "[variation validator](../../implementations/python/packages/raes/validator/_variation.py)"
_PARTICIPANT_TEMPORAL_MODEL = (
    "[temporal model](../../implementations/python/packages/raes/participant_temporal_semantics.py)"
)
_TIME_MODEL_VALIDATOR = "[time-model validator](../../implementations/python/packages/raes/validator/_time_model.py)"
_SEMANTIC = "semantic validation"
_STRUCTURAL = "structural validation"
_DANGLING = "fatal dangling or ambiguous"

# This independently owned expectation makes every normative reference row a
# checked contract. The catalog is not generated from this registry; changing
# either authority requires an explicit, reviewable reconciliation.
_REFERENCE_EDGE_EXPECTATIONS: dict[str, tuple[str, str, str, str]] = {
    "nodes.*.features[]": ("features", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "nodes.*.features.*": (
        "derived:node_roles",
        _SEMANTIC,
        "fatal dangling role when non-empty",
        _NODE_VALIDATOR,
    ),
    "nodes.*.conditions[]": ("conditions", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "nodes.*.conditions.*": (
        "derived:node_roles",
        _SEMANTIC,
        "fatal dangling role when non-empty",
        _NODE_VALIDATOR,
    ),
    "conditions.*.proposition": (
        "propositions",
        _SEMANTIC,
        "fatal dangling or ambiguous when present",
        _PROPOSITION_VALIDATOR,
    ),
    "propositions.*.subjects[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "propositions.*.evidence_requirements[]": (
        "evidence_requirements",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "assertions.*.proposition": (
        "propositions",
        _SEMANTIC,
        _DANGLING,
        _PROPOSITION_VALIDATOR,
    ),
    "nodes.*.injects[]": ("injects", _SEMANTIC, _DANGLING, _NODE_VALIDATOR),
    "nodes.*.injects.*": (
        "derived:node_roles",
        _SEMANTIC,
        "fatal dangling role when non-empty",
        _NODE_VALIDATOR,
    ),
    "nodes.*.vulnerabilities[]": (
        "vulnerabilities",
        _SEMANTIC,
        _DANGLING,
        _NODE_VALIDATOR,
    ),
    "nodes.*.roles.*.entities[]": (
        "entities",
        _SEMANTIC,
        _DANGLING,
        _SECTION_VALIDATOR,
    ),
    "infrastructure.*.$key": (
        "nodes",
        _SEMANTIC,
        "fatal when no same-named node exists",
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.links[]": (
        "infrastructure",
        _SEMANTIC,
        _DANGLING,
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.properties[].*": (
        "infrastructure",
        _SEMANTIC,
        "fatal unless the key names a linked switch-backed entry",
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.acls[].from_net": (
        "infrastructure",
        _SEMANTIC,
        "fatal unless the target is switch-backed",
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.acls[].to_net": (
        "infrastructure",
        _SEMANTIC,
        "fatal unless the target is switch-backed",
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "infrastructure.*.dependencies[]": (
        "infrastructure",
        _SEMANTIC,
        _DANGLING,
        _INFRASTRUCTURE_VALIDATOR,
    ),
    "features.*.dependencies[]": (
        "features",
        _SEMANTIC,
        "fatal dangling, ambiguous, or cyclic",
        _SECTION_VALIDATOR,
    ),
    "features.*.vulnerabilities[]": (
        "vulnerabilities",
        _SEMANTIC,
        _DANGLING,
        _SECTION_VALIDATOR,
    ),
    "entities.*.vulnerabilities[]": (
        "vulnerabilities",
        _SEMANTIC,
        _DANGLING,
        _SECTION_VALIDATOR,
    ),
    "entities.*.events[]": ("events", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "injects.*.from_entity": ("entities", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "injects.*.to_entities[]": ("entities", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "events.*.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _PROPOSITION_VALIDATOR,
    ),
    "events.*.injects[]": ("injects", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "scripts.*.events[]": ("events", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "stories.*.scripts[]": ("scripts", _SEMANTIC, _DANGLING, _SECTION_VALIDATOR),
    "content.*.target": (
        "nodes",
        _SEMANTIC,
        "fatal unless target is a vm node",
        _CONTENT_VALIDATOR,
    ),
    "content.*.service_materialization.target_service_ref": (
        "derived:node_services",
        _SEMANTIC,
        "fatal unless the exact service exists on the content target vm",
        _SERVICE_MATERIALIZATION_VALIDATOR,
    ),
    "content.*.service_materialization.shared_service_relationship_ref": (
        "relationships",
        _SEMANTIC,
        "fatal unless a matching typed shared-service relationship owns cross-tenant mutable state/reset",
        _SERVICE_MATERIALIZATION_VALIDATOR,
    ),
    "content.*.service_materialization.ordering_content_refs[]": (
        "content",
        "semantic validation and planner ordering",
        "fatal dangling, self, or cyclic dependency",
        _CONTENT_COMPILER,
    ),
    "content.*.service_materialization.readback_assertion_refs[]": (
        "assertions",
        _SEMANTIC,
        "fatal unless each ref is an observed-state postcondition",
        _SERVICE_MATERIALIZATION_VALIDATOR,
    ),
    "content.*.service_materialization.evidence_requirement_refs[]": (
        "evidence_requirements",
        _SEMANTIC,
        "fatal unless each ref exists and every readback proposition requires it",
        _SERVICE_MATERIALIZATION_VALIDATOR,
    ),
    "content.*.service_materialization.observation_boundary_refs[]": (
        "observation_boundaries",
        _SEMANTIC,
        "fatal dangling ref",
        _SERVICE_MATERIALIZATION_VALIDATOR,
    ),
    "generated_artifacts.*.consumers[].node": (
        "nodes",
        "structural model validation",
        _DANGLING,
        _STATEFUL_MODEL,
    ),
    "generated_artifacts.*.ordering_dependencies[]": (
        "generated_artifacts,persistent_volumes",
        "structural model and planner graph validation",
        "fatal dangling, ambiguous, or cyclic",
        _STATEFUL_MODEL,
    ),
    "generated_artifacts.*.refresh_dependencies[]": (
        "generated_artifacts,persistent_volumes",
        "structural model validation",
        _DANGLING,
        _STATEFUL_MODEL,
    ),
    "persistent_volumes.*.consumers[].node": (
        "nodes",
        "structural model validation",
        _DANGLING,
        _STATEFUL_MODEL,
    ),
    "persistent_volumes.*.ordering_dependencies[]": (
        "generated_artifacts,persistent_volumes",
        "structural model and planner graph validation",
        "fatal dangling, ambiguous, or cyclic",
        _STATEFUL_MODEL,
    ),
    "persistent_volumes.*.refresh_dependencies[]": (
        "generated_artifacts,persistent_volumes",
        "structural model validation",
        _DANGLING,
        _STATEFUL_MODEL,
    ),
    "accounts.*.domain_ref": (
        "identity_domains",
        _SEMANTIC,
        "fatal dangling, ambiguous, or inconsistent topology",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "identity_domains.*.authority_account_ref": (
        "accounts",
        _SEMANTIC,
        "fatal dangling, ambiguous, or authority outside domain controllers",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "identity_forests.*.root_domain_ref": (
        "identity_domains",
        _SEMANTIC,
        "fatal dangling or root outside declared membership",
        _ENTERPRISE_IDENTITY_SEMANTICS,
    ),
    "identity_forests.*.domain_refs[]": (
        "identity_domains",
        _SEMANTIC,
        "fatal dangling, duplicate, or domain in multiple forests",
        _ENTERPRISE_IDENTITY_SEMANTICS,
    ),
    "identity_facades.*.service_ref": (
        "targetable",
        _SEMANTIC,
        "fatal unless target is a named vm service",
        _ENTERPRISE_IDENTITY_SEMANTICS,
    ),
    "deployment_cells.*.tenant_ref": (
        "deployment_tenants",
        _SEMANTIC,
        _DANGLING,
        _DEPLOYMENT_TENANCY_SEMANTICS,
    ),
    "deployment_cells.*.node_refs[]": (
        "nodes",
        _SEMANTIC,
        "fatal dangling, duplicate, or node in multiple cells",
        _DEPLOYMENT_TENANCY_SEMANTICS,
    ),
    "accounts.*.node": (
        "nodes",
        _SEMANTIC,
        "fatal unless target is a vm node",
        _ACCOUNT_VALIDATOR,
    ),
    "relationships.*.source": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or ambiguous; subtype may narrow domain",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.target": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or ambiguous; subtype may narrow domain",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.database_access.role_ref": (
        "derived:database_roles",
        _SEMANTIC,
        "fatal outside the target database service",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.mail_access.listener_ref": (
        "derived:mail_listeners",
        _SEMANTIC,
        "fatal outside the target mail service",
        _MAIL_VALIDATOR,
    ),
    "relationships.*.mail_access.mailbox_ref": (
        "derived:mailboxes",
        _SEMANTIC,
        "fatal outside the target mail service",
        _MAIL_VALIDATOR,
    ),
    "relationships.*.mail_access.domain_ref": (
        "derived:mail_domains",
        _SEMANTIC,
        "fatal outside the target mail service",
        _MAIL_VALIDATOR,
    ),
    "relationships.*.forwarding_edge.forwarder_ref": (
        "runtime:forwarding_agents",
        _SEMANTIC,
        "fatal dangling or ambiguous across scenario and node scopes",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.service_integration.consumer_ref": (
        "runtime:platform_applications",
        _SEMANTIC,
        _DANGLING,
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.service_integration.engine_ref": (
        "runtime:platform_applications",
        _SEMANTIC,
        _DANGLING,
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.service_integration.auth_principal_ref": (
        "derived:engine_authorization_principals",
        _SEMANTIC,
        "fatal outside the engine authorization scope",
        _RELATIONSHIP_VALIDATOR,
    ),
    "relationships.*.proxy_upstream.route_ref": (
        "derived:source_application_routes",
        _SEMANTIC,
        "fatal outside the source application",
        _RELATIONSHIP_PROXY_VALIDATOR,
    ),
    "relationships.*.proxy_upstream.upstream_node_ref": (
        "nodes",
        _SEMANTIC,
        _DANGLING,
        _RELATIONSHIP_PROXY_VALIDATOR,
    ),
    "relationships.*.proxy_upstream.upstream_service_ref": (
        "derived:upstream_node_services",
        _SEMANTIC,
        "fatal without a resolvable upstream node and service",
        _RELATIONSHIP_PROXY_VALIDATOR,
    ),
    "relationships.*.domain_join.controller_refs[]": (
        "nodes",
        _SEMANTIC,
        "fatal dangling, ambiguous, or controller outside target domain",
        _DOMAIN_TOPOLOGY_SEMANTICS,
    ),
    "relationships.*.shared_service.mutable_state_refs[]": (
        "persistent_volumes",
        _SEMANTIC,
        "fatal dangling or conflicting state ownership",
        _DEPLOYMENT_TENANCY_SEMANTICS,
    ),
    "agents.*.entity": ("entities", _SEMANTIC, _DANGLING, _PARTICIPANT_VALIDATOR),
    "agents.*.actions[]": (
        "action_contracts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_SEMANTICS,
    ),
    "agents.*.starting_accounts[]": (
        "accounts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.interactive_access.*.target_ref": (
        "nodes",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-vm target",
        _PARTICIPANT_INTERACTIVE_ACCESS_SEMANTICS,
    ),
    "agents.*.interactive_access.*.account_ref": (
        "accounts",
        _SEMANTIC,
        "fatal dangling, same-node mismatch, or outside participant starting accounts",
        _PARTICIPANT_INTERACTIVE_ACCESS_SEMANTICS,
    ),
    "agents.*.starting_assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _PROPOSITION_VALIDATOR,
    ),
    "agents.*.initial_knowledge.hosts[]": (
        "nodes",
        _SEMANTIC,
        "fatal unless the target is a vm node",
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.initial_knowledge.subnets[]": (
        "infrastructure",
        _SEMANTIC,
        "fatal unless the target is switch-backed",
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.initial_knowledge.services[]": (
        "derived:node_services",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.initial_knowledge.accounts[]": (
        "accounts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.allowed_subnets[]": (
        "infrastructure",
        _SEMANTIC,
        "fatal unless the target is switch-backed",
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.authority_anchors[]": (
        "declared",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.operating_scope[]": (
        "derived:operating_scope",
        _SEMANTIC,
        "fatal dangling or ambiguous outside vm nodes, switch-backed infrastructure, services, and content",
        _PARTICIPANT_VALIDATOR,
    ),
    "agents.*.observation_boundaries[]": (
        "observation_boundaries",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_SEMANTICS,
    ),
    "action_contracts.*.interactions.*.related_actions[]": (
        "action_contracts",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_SEMANTICS,
    ),
    "action_contracts.*.interactions.*.target": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "action_contracts.*.interactions.*.shared_state_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_VALIDATOR,
    ),
    "action_contracts.*.temporal_contracts.*.backend_disclosure_refs[]": (
        "derived:backend_timing_disclosures",
        _STRUCTURAL,
        "fatal dangling local disclosure id",
        _PARTICIPANT_TEMPORAL_MODEL,
    ),
    "action_contracts.*.backend_timing_disclosures.*.affected_temporal_ids[]": (
        "derived:temporal_contracts",
        _STRUCTURAL,
        "fatal dangling local temporal id",
        _PARTICIPANT_TEMPORAL_MODEL,
    ),
    "observation_boundaries.*.view_rules.*.information_ref": (
        "derived:boundary_information",
        _SEMANTIC,
        "fatal outside declared boundary information",
        _PARTICIPANT_SEMANTICS,
    ),
    "observation_boundaries.*.view_rules.*.evidence_refs[]": (
        "derived:boundary_evidence",
        _SEMANTIC,
        "fatal outside declared boundary evidence",
        _PARTICIPANT_SEMANTICS,
    ),
    "observation_boundaries.*.view_transitions.*.information_ref": (
        "derived:boundary_view_rules",
        _SEMANTIC,
        "fatal without a matching view rule",
        _PARTICIPANT_SEMANTICS,
    ),
    "observation_boundaries.*.view_transitions.*.evidence_refs[]": (
        "derived:boundary_evidence",
        _SEMANTIC,
        "fatal outside declared boundary evidence",
        _PARTICIPANT_SEMANTICS,
    ),
    "outcome_interpretation_rules.*.source_bindings.*.ref": (
        "action_contracts,objectives,workflows",
        _SEMANTIC,
        "fatal dangling for sdl-bound layers",
        _OUTCOME_SEMANTICS,
    ),
    "outcome_interpretation_rules.*.target_bindings.*.ref": (
        "objectives,workflows",
        _SEMANTIC,
        "fatal dangling for sdl-bound layers",
        _OUTCOME_SEMANTICS,
    ),
    "behavior_specifications.*.participant_refs[]": (
        "agents",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.participant_role_refs[]": (
        "derived:agent_roles",
        _SEMANTIC,
        "fatal unless bound by a referenced participant",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.action_contract_refs[]": (
        "action_contracts",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.observation_boundary_refs[]": (
        "observation_boundaries",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.outcome_interpretation_rule_refs[]": (
        "outcome_interpretation_rules",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.authority_scope_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _BEHAVIOR_VALIDATOR,
    ),
    "behavior_specifications.*.tool_affordances.*.tool_ref": (
        "content",
        _SEMANTIC,
        "fatal dangling, ambiguous, or outside the `scenario-content` tools-and-artifacts reference model",
        _TOOL_AFFORDANCE_VALIDATOR,
    ),
    "behavior_specifications.*.tool_affordances.*.action_contract_refs[]": (
        "action_contracts",
        _SEMANTIC,
        "fatal dangling, outside the owning behavior specification, or outside a resolved participant",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.tool_affordances.*.observation_boundary_refs[]": (
        "observation_boundaries",
        _SEMANTIC,
        "fatal dangling, outside the owner/participant, or without explicit view classification",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.participant_ref": (
        "agents",
        _SEMANTIC,
        "fatal dangling or outside the owning behavior specification",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.inject_ref": (
        "injects",
        _SEMANTIC,
        "fatal dangling or outside the anchored event occurrence",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.occurrence.event_ref": (
        "events",
        _SEMANTIC,
        "fatal dangling or not containing the bound inject",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.occurrence.script_ref": (
        "scripts",
        _SEMANTIC,
        "fatal dangling or not containing the anchored event",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.occurrence.story_ref": (
        "stories",
        _SEMANTIC,
        "fatal dangling or not containing the anchored script",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.source_item_ref": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.result_item_ref": (
        "targetable",
        _SEMANTIC,
        "fatal dangling, ambiguous, hidden, or unclassified at the participant boundary",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.observation_boundary_ref": (
        "observation_boundaries",
        _SEMANTIC,
        "fatal dangling or outside the owner/participant",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.temporal_constraint_refs[]": (
        "temporal_constraints",
        _SEMANTIC,
        "fatal dangling or not binding this delivery declaration",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.evidence_requirement_refs[]": (
        "evidence_requirements",
        _SEMANTIC,
        "fatal dangling or not binding this delivery declaration",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.control_transition_ref": (
        "derived:mixed_control_local_ids",
        "structural and semantic validation",
        "fatal dangling, wrong-kind, or incomplete control agreement",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.controller_ref": (
        "agents",
        _SEMANTIC,
        "fatal disagreement with the selected control-transition target controller",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.control_authority_scope_refs[]": (
        "targetable",
        _SEMANTIC,
        "fatal dangling, ambiguous, or disagreement with the selected target-state scope",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.participant_inject_deliveries.*.control_evidence_refs[]": (
        "targetable",
        _SEMANTIC,
        "fatal dangling, control disagreement, or absent evidence-requirement coverage",
        _PARTICIPANT_INJECT_DELIVERY_VALIDATOR,
    ),
    "behavior_specifications.*.behavior_mode": (
        "vocabulary:behavior_mode",
        _STRUCTURAL,
        "fatal invalid vocabulary value",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.mixed_control.participant_ref": (
        "agents",
        _SEMANTIC,
        "fatal unless owned by the enclosing behavior specification",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.controller_states.*.controller_ref": (
        "agents-or-self",
        _SEMANTIC,
        "fatal operator/role/identity impersonation or dangling agent",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.controller_states.*.authority_basis_refs[]": (
        "derived:controller_authority_anchors",
        _SEMANTIC,
        "fatal dangling, ambiguous, or authority widening",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.controller_states.*.scope_refs[]": (
        "derived:behavior-and-controller-scope",
        _SEMANTIC,
        "fatal dangling, ambiguous, or scope widening",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.controller_states.*.evidence_refs[]": (
        "declared",
        _SEMANTIC,
        _DANGLING,
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.transitions.*.from_state_ref": (
        "derived:mixed_control_local_ids",
        "structural and semantic validation",
        "fatal dangling, stale, reversed, or ambiguously ordered local ref",
        _MIXED_CONTROL_MODEL,
    ),
    "behavior_specifications.*.mixed_control.transitions.*.to_state_ref": (
        "derived:mixed_control_local_ids",
        "structural and semantic validation",
        "fatal dangling, stale, reversed, or ambiguously ordered local ref",
        _MIXED_CONTROL_MODEL,
    ),
    "behavior_specifications.*.mixed_control.transitions.*.proposal_ref": (
        "derived:mixed_control_local_ids",
        "structural and semantic validation",
        "fatal dangling, stale, reversed, or ambiguously ordered local ref",
        _MIXED_CONTROL_MODEL,
    ),
    "behavior_specifications.*.mixed_control.transitions.*.evidence_refs[]": (
        "declared",
        _SEMANTIC,
        "fatal dangling, ambiguous, or silent handoff",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.mixed_control.transitions.*.completion_evidence_refs[]": (
        "declared",
        _SEMANTIC,
        "fatal dangling, ambiguous, or silent handoff",
        _MIXED_CONTROL_VALIDATOR,
    ),
    "behavior_specifications.*.ai_offensive_behavior_refs[]": (
        "vocabulary:ai_offensive_behavior",
        _SEMANTIC,
        "fatal unknown vocabulary identifier",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.defensive_behavior_refs[]": (
        "vocabulary:defensive_behavior",
        _SEMANTIC,
        "fatal unknown vocabulary identifier",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.offensive_behavior_refs[]": (
        "vocabulary:offensive_behavior",
        _SEMANTIC,
        "fatal unknown vocabulary identifier",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.realization_profile_ref": (
        "opaque:realization_profile",
        _STRUCTURAL,
        "fatal invalid reference shape; resolution belongs to realization",
        _BEHAVIOR_MODEL,
    ),
    "behavior_specifications.*.backend_feature_support_refs[]": (
        "registry:behavior_features",
        _SEMANTIC,
        "fatal unsupported feature identifier",
        _BEHAVIOR_SEMANTICS,
    ),
    "behavior_specifications.*.evidence_contract_refs[]": (
        "contract:participant_evidence",
        _SEMANTIC,
        "fatal unknown contract identifier",
        _BEHAVIOR_SEMANTICS,
    ),
    "evidence_requirements.*.source_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.scope_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.channel_refs[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.trigger_ref": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "evidence_requirements.*.boundary_ref": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _EVIDENCE_VALIDATOR,
    ),
    "clocks.*.time_domain_ref": (
        "time_domains",
        _SEMANTIC,
        "fatal dangling",
        _TIME_MODEL_VALIDATOR,
    ),
    "time_domain_mappings.*.source_domain_ref": (
        "time_domains",
        _SEMANTIC,
        "fatal dangling, duplicate, or cyclic mapping",
        _TIME_MODEL_VALIDATOR,
    ),
    "time_domain_mappings.*.target_domain_ref": (
        "time_domains",
        _SEMANTIC,
        "fatal dangling, duplicate, or cyclic mapping",
        _TIME_MODEL_VALIDATOR,
    ),
    "time_progression_policies.*.clock_ref": (
        "clocks",
        _SEMANTIC,
        "fatal dangling or incompatible reset/replay lifecycle",
        _TIME_MODEL_VALIDATOR,
    ),
    "temporal_constraints.*.clock_ref": (
        "clocks",
        _SEMANTIC,
        "fatal dangling",
        _TIME_MODEL_VALIDATOR,
    ),
    "temporal_constraints.*.subject_refs[]": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or ambiguous",
        _TIME_MODEL_VALIDATOR,
    ),
    "variation_points.*.target.variable": (
        "variables",
        _SEMANTIC,
        "fatal dangling or wrong variable type",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.target.owner": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or wrong slot owner type",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.domain.allowed_refs[]": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or wrong slot candidate type",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.alternatives.*.reference": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or wrong slot candidate type",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.members.*.reference": (
        "targetable",
        _SEMANTIC,
        "fatal dangling or wrong slot candidate type",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.alternatives.*.requires[].point": (
        "variation_points",
        _SEMANTIC,
        _DANGLING,
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.alternatives.*.requires[].members[]": (
        "derived:variation_members",
        _SEMANTIC,
        "fatal outside the resolved variation point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.alternatives.*.excludes[].point": (
        "variation_points",
        _SEMANTIC,
        _DANGLING,
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.alternatives.*.excludes[].members[]": (
        "derived:variation_members",
        _SEMANTIC,
        "fatal outside the resolved variation point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.members.*.requires[].point": (
        "variation_points",
        _SEMANTIC,
        _DANGLING,
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.members.*.requires[].members[]": (
        "derived:variation_members",
        _SEMANTIC,
        "fatal outside the resolved variation point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.members.*.excludes[].point": (
        "variation_points",
        _SEMANTIC,
        _DANGLING,
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.members.*.excludes[].members[]": (
        "derived:variation_members",
        _SEMANTIC,
        "fatal outside the resolved variation point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.precedence[].before": (
        "derived:variation_members",
        _STRUCTURAL,
        "fatal outside the owning order point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.precedence[].after": (
        "derived:variation_members",
        _STRUCTURAL,
        "fatal outside the owning order point",
        _VARIATION_VALIDATOR,
    ),
    "variation_points.*.fixed_positions.*.$key": (
        "derived:variation_members",
        _STRUCTURAL,
        "fatal outside the owning order point",
        _VARIATION_VALIDATOR,
    ),
    "objectives.*.agent": ("agents", _SEMANTIC, _DANGLING, _OBJECTIVE_SEMANTICS),
    "objectives.*.entity": ("entities", _SEMANTIC, _DANGLING, _OBJECTIVE_SEMANTICS),
    "objectives.*.actions[]": (
        "derived:agent_actions",
        _SEMANTIC,
        "fatal outside the bound agent action contracts",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.targets[]": (
        "targetable",
        _SEMANTIC,
        _DANGLING,
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.success.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or precondition role",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.depends_on[]": (
        "objectives",
        _SEMANTIC,
        "fatal dangling, ambiguous, or cyclic",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.window.stories[]": (
        "stories",
        _SEMANTIC,
        _DANGLING,
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.window.scripts[]": (
        "scripts",
        _SEMANTIC,
        "fatal dangling or outside referenced stories",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.window.events[]": (
        "events",
        _SEMANTIC,
        "fatal dangling or outside referenced scripts",
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.window.workflows[]": (
        "workflows",
        _SEMANTIC,
        _DANGLING,
        _OBJECTIVE_SEMANTICS,
    ),
    "objectives.*.window.steps[]": (
        "workflow_steps",
        _SEMANTIC,
        "fatal malformed, dangling, or outside referenced workflows",
        _OBJECTIVE_SEMANTICS,
    ),
    "workflows.*.start": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling step",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.when.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.when.objectives[]": (
        "objectives",
        _SEMANTIC,
        _DANGLING,
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.when.steps.*.step": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, self-referential, non-executable, or unavailable before evaluation",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.cases.*.when.assertions[]": (
        "assertions",
        _SEMANTIC,
        "fatal dangling, ambiguous, or non-precondition role",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.cases.*.when.objectives[]": (
        "objectives",
        _SEMANTIC,
        _DANGLING,
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.cases.*.when.steps.*.step": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, self-referential, non-executable, or unavailable before evaluation",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.objective": (
        "objectives",
        _SEMANTIC,
        _DANGLING,
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.procedure_ref": (
        "action_contracts",
        _SEMANTIC,
        "fatal dangling or non-procedure granularity",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.scaffold_refs[]": (
        "observation_boundaries",
        _SEMANTIC,
        "fatal dangling or scaffold-incompatible boundary",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.allowed_action_families[]": (
        "action_contracts",
        _SEMANTIC,
        "fatal dangling or non-aggregate granularity",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.next": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.on_success": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.on_failure": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.on_exhausted": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.then": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.else": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.cases.*.next": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.default": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, cyclic, or unreachable",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.branches[]": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling or outside a closed parallel branch",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.join": (
        "workflow_steps",
        _SEMANTIC,
        "fatal dangling, non-join, multiply owned, or outside branch closure",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.workflow": (
        "workflows",
        _SEMANTIC,
        "fatal dangling or cyclic",
        _WORKFLOW_SEMANTICS,
    ),
    "workflows.*.steps.*.compensate_with": (
        "workflows",
        _SEMANTIC,
        "fatal dangling, cyclic, or invalid as a compensation target",
        _WORKFLOW_SEMANTICS,
    ),
}


class CatalogParseError(ValueError):
    """A normative catalog table is absent or malformed."""


@dataclass(frozen=True)
class TopLevelRow:
    field: str
    kind: str
    shape: str
    lifecycle: tuple[str, ...]
    presence: str
    identity: str
    references: str
    owner: str
    line_no: int


@dataclass(frozen=True)
class ReferenceRow:
    source_path: str
    domain: str
    phase: str
    failure: str
    normative_owner: str
    evidence: str
    line_no: int

    @property
    def key(self) -> tuple[str, str]:
        parts = self.source_path.replace("[]", "").split(".")
        return parts[0], parts[-1]


@dataclass(frozen=True)
class RuntimeRow:
    key: str
    collection: str
    primary_id: str
    child_paths: tuple[str, ...]
    owner: str
    line_no: int


@dataclass(frozen=True)
class PhaseMemberRow:
    member: str
    normalized: str
    expanded: str
    instantiated: str
    transfer: str
    line_no: int


def _cells(line: str) -> list[str]:
    parts = [part.strip() for part in line.strip().split("|")]
    if parts and not parts[0]:
        parts.pop(0)
    if parts and not parts[-1]:
        parts.pop()
    return parts


def _unquote(cell: str) -> str:
    match = _BACKTICK_RE.fullmatch(cell.strip())
    return match.group(1) if match else cell.strip()


def _table(text: str, heading: str, columns: int) -> list[tuple[int, list[str]]]:
    size = len(text.encode("utf-8"))
    if size > _MAX_CATALOG_BYTES:
        raise CatalogParseError(f"catalog exceeds {_MAX_CATALOG_BYTES}-byte size limit")
    lines = text.splitlines()
    try:
        start = next(index for index, line in enumerate(lines) if line.strip() == heading) + 1
    except StopIteration as exc:
        raise CatalogParseError(f"missing catalog heading: {heading}") from exc
    table: list[tuple[int, list[str]]] = []
    started = False
    for index, line in enumerate(lines[start:], start=start):
        if line.startswith("## "):
            break
        if line.lstrip().startswith("|"):
            started = True
            table.append((index + 1, _cells(line)))
            if len(table) > _MAX_CATALOG_ROWS + 2:
                raise CatalogParseError(f"catalog exceeds {_MAX_CATALOG_ROWS}-row limit")
        elif started:
            break
    if len(table) < 3:
        raise CatalogParseError(f"catalog under {heading!r} requires a header, separator, and data rows")
    if len(table[0][1]) != columns:
        raise CatalogParseError(f"catalog under {heading!r} has {len(table[0][1])} columns; expected {columns}")
    separator = table[1][1]
    if len(separator) != columns or not all(_SEPARATOR_RE.fullmatch(cell) for cell in separator):
        raise CatalogParseError(f"catalog under {heading!r} has a malformed separator row")
    for line_no, cells in table[2:]:
        if len(cells) != columns:
            raise CatalogParseError(f"catalog row at line {line_no} has {len(cells)} columns; expected {columns}")
    return table[2:]


def _unique(rows: list[Any], key_name: str, label: str) -> None:
    seen: dict[str, int] = {}
    for row in rows:
        key = getattr(row, key_name)
        if key in seen:
            raise CatalogParseError(f"duplicate {label} {key!r} at lines {seen[key]} and {row.line_no}")
        seen[key] = row.line_no


def parse_top_level_catalog(text: str) -> list[TopLevelRow]:
    rows = [
        TopLevelRow(
            field=_unquote(cells[0]),
            kind=cells[1].lower(),
            shape=cells[2].lower(),
            lifecycle=tuple(token.strip().lower() for token in cells[3].split(",") if token.strip()),
            presence=cells[4].strip().lower(),
            identity=_unquote(cells[5]),
            references=cells[6].strip().lower(),
            owner=cells[7].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _TOP_LEVEL_HEADING, 8)
    ]
    _unique(rows, "field", "top-level field")
    return rows


def parse_reference_catalog(text: str) -> list[ReferenceRow]:
    rows = [
        ReferenceRow(
            source_path=_unquote(cells[0]),
            domain=_unquote(cells[1]),
            phase=cells[2].strip().lower(),
            failure=cells[3].strip().lower(),
            normative_owner=cells[4].strip(),
            evidence=cells[5].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _REFERENCE_HEADING, 6)
    ]
    _unique(rows, "source_path", "reference edge")
    return rows


def parse_runtime_catalog(text: str) -> list[RuntimeRow]:
    rows = [
        RuntimeRow(
            key=_unquote(cells[0]),
            collection=_unquote(cells[1]),
            primary_id=_unquote(cells[2]),
            child_paths=tuple(token.strip() for token in _unquote(cells[3]).split(",") if token.strip() != "none"),
            owner=cells[4].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _RUNTIME_HEADING, 5)
    ]
    _unique(rows, "key", "runtime family")
    return rows


def parse_phase_member_catalog(text: str) -> list[PhaseMemberRow]:
    rows = [
        PhaseMemberRow(
            member=_unquote(cells[0]),
            normalized=cells[1].strip().lower(),
            expanded=cells[2].strip().lower(),
            instantiated=cells[3].strip().lower(),
            transfer=cells[4].strip(),
            line_no=line_no,
        )
        for line_no, cells in _table(text, _PHASE_HEADING, 5)
    ]
    _unique(rows, "member", "phase-specific member")
    return rows


def _failure(rule_id: str, message: str, path: str) -> PolicyFailure:
    return PolicyFailure(rule_id, message, path)


def _expected_kind(field: str) -> str:
    if field in _METADATA_FIELDS:
        return "metadata"
    if field in _COMPOSITION_FIELDS:
        return "composition"
    return "section"


def _schema_shape(schema: dict[str, Any]) -> str:
    schema_type = schema.get("type")
    if schema_type == "string":
        return "scalar"
    if schema_type == "array":
        return "list"
    if schema_type == "object":
        return "map"
    if schema_type is None and schema.get("default") is None:
        return "mapping"
    return "unknown"


def _expected_presence(field: str) -> str:
    model_field = Scenario.model_fields[field]
    if model_field.is_required():
        return "required"
    value = model_field.default_factory() if model_field.default_factory is not None else model_field.default
    if value == "*":
        return "optional; default `*`"
    if value == "":
        return "optional; default empty string"
    if value is None:
        return "optional; default null"
    if value == []:
        return "optional; default empty list"
    if value == {}:
        return "optional; default empty map"
    return f"optional; default `{value}`"


def _expected_identity(field: str, shape: str) -> str:
    if field == "name":
        return "scenario_name"
    if field == "module":
        return "module.id"
    if field == "imports":
        return "namespace"
    if field == "forwarding_agents":
        return "forwarding_agent_id"
    if shape == "map":
        return "map_key"
    return "none"


def _expected_lifecycle(field: str) -> tuple[str, ...]:
    phase_models = (
        ("normalized", Scenario),
        ("expanded", ExpandedScenario),
        ("instantiated", InstantiatedScenario),
    )
    return tuple(phase for phase, model in phase_models if field in model.model_fields)


def _flatten_children(children: tuple[RuntimeReferenceChild, ...], prefix: str = "") -> tuple[str, ...]:
    paths: list[str] = []
    for child in children:
        path = (
            f"{prefix}/{child.collection_name}:{child.id_field}"
            if prefix
            else f"{child.collection_name}:{child.id_field}"
        )
        paths.append(path)
        paths.extend(_flatten_children(child.children, path))
    return tuple(paths)


def _check_top_level(text: str, schema: dict[str, Any]) -> tuple[list[PolicyFailure], list[TopLevelRow]]:
    failures: list[PolicyFailure] = []
    try:
        rows = parse_top_level_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-parse", str(exc), SECTIONS_PATH)], []
    by_field = {row.field: row for row in rows}
    model_fields = set(Scenario.model_fields)
    schema_fields = set(schema.get("properties", {}))
    catalog_fields = set(by_field)
    if model_fields != schema_fields or catalog_fields != model_fields:
        failures.append(
            _failure(
                "sdl-catalog-field-set",
                f"field sets differ: catalog-only={sorted(catalog_fields - model_fields)}, "
                f"model-only={sorted(model_fields - catalog_fields)}, "
                f"schema-only={sorted(schema_fields - model_fields)}, model-only-vs-schema={sorted(model_fields - schema_fields)}",
                SECTIONS_PATH,
            )
        )
    for field in sorted(catalog_fields & model_fields & schema_fields):
        row = by_field[field]
        expected_shape = _schema_shape(schema["properties"][field])
        if field in HASHMAP_SECTIONS:
            expected_shape = "map"
        if row.shape != expected_shape:
            failures.append(
                _failure(
                    "sdl-catalog-field-shape",
                    f"{field!r} is {expected_shape}, catalog says {row.shape}",
                    SECTIONS_PATH,
                )
            )
        expected_presence = _expected_presence(field)
        if row.presence != expected_presence:
            failures.append(
                _failure(
                    "sdl-catalog-field-default",
                    f"{field!r} is {expected_presence}, catalog says {row.presence}",
                    SECTIONS_PATH,
                )
            )
        expected_identity = _expected_identity(field, expected_shape)
        if row.identity != expected_identity:
            failures.append(
                _failure(
                    "sdl-catalog-field-identity",
                    f"{field!r} identity is {expected_identity!r}, catalog says {row.identity!r}",
                    SECTIONS_PATH,
                )
            )
        if row.kind != _expected_kind(field) or row.kind not in _VALID_KINDS:
            failures.append(
                _failure(
                    "sdl-catalog-field-kind",
                    f"{field!r} has invalid kind {row.kind!r}",
                    SECTIONS_PATH,
                )
            )
        expected_lifecycle = _expected_lifecycle(field)
        if row.lifecycle != expected_lifecycle or not set(row.lifecycle) <= _VALID_LIFECYCLE:
            failures.append(
                _failure(
                    "sdl-catalog-lifecycle",
                    f"{field!r} lifecycle is {expected_lifecycle!r}, catalog says {row.lifecycle!r}",
                    SECTIONS_PATH,
                )
            )
        if row.shape not in _VALID_SHAPES or not row.identity or not row.owner:
            failures.append(
                _failure(
                    "sdl-catalog-row-incomplete",
                    f"{field!r} has an incomplete classification",
                    SECTIONS_PATH,
                )
            )
    map_fields = {row.field for row in rows if row.shape == "map"}
    if map_fields != set(HASHMAP_SECTIONS):
        failures.append(
            _failure(
                "sdl-catalog-map-set",
                f"map fields differ from mapping registry: {sorted(map_fields ^ set(HASHMAP_SECTIONS))}",
                SECTIONS_PATH,
            )
        )
    if not set(MODULE_HASHMAP_SECTIONS) <= map_fields:
        failures.append(
            _failure(
                "sdl-catalog-module-map-set",
                "module export maps are not a subset of catalogued maps",
                SECTIONS_PATH,
            )
        )
    summary = _SUMMARY_RE.search(text)
    actual = {
        "top": len(rows),
        "meta": sum(row.kind != "section" for row in rows),
        "sections": sum(row.kind == "section" for row in rows),
        "maps": sum(row.shape == "map" for row in rows),
        "lists": sum(row.shape == "list" and row.kind == "section" for row in rows),
    }
    if summary is None or any(int(summary.group(key)) != value for key, value in actual.items()):
        failures.append(
            _failure(
                "sdl-catalog-summary",
                f"checked summary is absent or stale; expected {actual}",
                SECTIONS_PATH,
            )
        )
    required = set(schema.get("required", []))
    model_required = {name for name, field in Scenario.model_fields.items() if field.is_required()}
    if required != model_required:
        failures.append(
            _failure(
                "sdl-catalog-schema-required",
                f"published schema required set differs from model: {sorted(required ^ model_required)}",
                SCHEMA_PATH,
            )
        )
    return failures, rows


def _check_references(text: str, top_rows: list[TopLevelRow], repo_root: Path) -> list[PolicyFailure]:
    try:
        rows = parse_reference_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-reference-parse", str(exc), REFERENCES_PATH)]
    failures: list[PolicyFailure] = []
    by_source = {row.source_path: (row.domain, row.phase, row.failure, row.evidence) for row in rows}
    if by_source != _REFERENCE_EDGE_EXPECTATIONS:
        differing = sorted(
            source
            for source in by_source.keys() | _REFERENCE_EDGE_EXPECTATIONS.keys()
            if by_source.get(source) != _REFERENCE_EDGE_EXPECTATIONS.get(source)
        )
        failures.append(
            _failure(
                "sdl-catalog-reference-row",
                f"reference-edge contract differs for: {differing}",
                REFERENCES_PATH,
            )
        )
    for key, domain in sorted(REFERENCE_COMPLETION_TARGETS.items()):
        matching = [row for row in rows if row.key == key and row.domain == domain]
        if not matching:
            actual = sorted({row.domain for row in rows if row.key == key}) or None
            failures.append(
                _failure(
                    "sdl-catalog-reference-domain",
                    f"{key!r} expects domain {domain!r}, catalog says {actual!r}",
                    REFERENCES_PATH,
                )
            )
    for row in rows:
        if not _reference_source_path_exists(row.source_path):
            failures.append(
                _failure(
                    "sdl-catalog-reference-path",
                    f"{row.source_path!r} does not traverse the typed SDL model",
                    REFERENCES_PATH,
                )
            )
        if not _is_normative_reference_owner(row.normative_owner, repo_root):
            failures.append(
                _failure(
                    "sdl-catalog-reference-owner",
                    f"{row.source_path!r} has no normative prose/ADR owner",
                    REFERENCES_PATH,
                )
            )
    behavior_expectations = {
        source: expected
        for source, expected in _REFERENCE_EDGE_EXPECTATIONS.items()
        if source.startswith("behavior_specifications.*.")
    }
    for source, expected in behavior_expectations.items():
        if by_source.get(source) != expected:
            failures.append(
                _failure(
                    "sdl-catalog-behavior-edge",
                    f"{source} must match its behavior reference contract",
                    REFERENCES_PATH,
                )
            )
    source_sections = {row.key[0] for row in rows}
    top_by_field = {row.field: row for row in top_rows}
    for section in source_sections:
        top = top_by_field.get(section)
        if top is None or top.references != "catalogued":
            failures.append(
                _failure(
                    "sdl-catalog-reference-coverage",
                    f"reference source section {section!r} is not marked catalogued",
                    SECTIONS_PATH,
                )
            )
    for row in top_rows:
        if row.references == "catalogued" and row.field not in source_sections:
            failures.append(
                _failure(
                    "sdl-catalog-reference-coverage",
                    f"{row.field!r} is marked catalogued but has no edge row",
                    REFERENCES_PATH,
                )
            )
    return failures


def _annotation_members(annotation: Any) -> tuple[Any, ...]:
    if get_origin(annotation) is Annotated:
        return _annotation_members(get_args(annotation)[0])
    if get_origin(annotation) in (Union, types.UnionType):
        return tuple(member for option in get_args(annotation) for member in _annotation_members(option))
    return (annotation,)


def _unwrap_reference_container(annotation: Any) -> tuple[Any, ...]:
    members: list[Any] = []
    for option in _annotation_members(annotation):
        origin = get_origin(option)
        if not isinstance(origin, type):
            continue
        arguments = get_args(option)
        if issubclass(origin, Mapping) and len(arguments) == 2:
            members.append(arguments[1])
        elif issubclass(origin, Sequence) and origin is not str and arguments:
            members.append(arguments[0])
    return tuple(members)


def _model_field_annotations(annotation: Any, field_name: str) -> tuple[Any, ...]:
    annotations: list[Any] = []
    for option in _annotation_members(annotation):
        if not isinstance(option, type) or not issubclass(option, BaseModel):
            continue
        for model_name, field in option.model_fields.items():
            aliases = {model_name}
            for alias in (field.alias, field.serialization_alias):
                if isinstance(alias, str):
                    aliases.add(alias)
            if field_name in aliases:
                annotations.append(field.annotation)
    return tuple(annotations)


def _reference_source_path_exists(source_path: str) -> bool:
    annotations: tuple[Any, ...] = (Scenario,)
    segments = source_path.split(".")
    for index, segment in enumerate(segments):
        if segment == "$key":
            return index == len(segments) - 1 and index > 0 and segments[index - 1] == "*"
        if segment == "*":
            annotations = tuple(
                member for annotation in annotations for member in _unwrap_reference_container(annotation)
            )
        else:
            is_collection = segment.endswith("[]")
            field_name = segment[:-2] if is_collection else segment
            annotations = tuple(
                member for annotation in annotations for member in _model_field_annotations(annotation, field_name)
            )
            if is_collection:
                annotations = tuple(
                    member for annotation in annotations for member in _unwrap_reference_container(annotation)
                )
        if not annotations:
            return False
    return True


def _is_normative_reference_owner(owner: str, repo_root: Path) -> bool:
    targets = [match.group("target").strip() for match in _MARKDOWN_LINK_RE.finditer(owner)]
    if len(targets) != 1:
        return False
    target = targets[0]
    if target.startswith("#"):
        relative = REFERENCES_PATH
    elif target.startswith(("http://", "https://", "mailto:")):
        return False
    else:
        target_path = target.split("#", 1)[0]
        root = repo_root.resolve()
        resolved = (root / Path(REFERENCES_PATH).parent / target_path).resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            return False
    return relative.startswith("specs/") or relative.startswith("docs/decisions/adrs/")


def _check_runtime(text: str) -> list[PolicyFailure]:
    try:
        rows = parse_runtime_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-runtime-parse", str(exc), RUNTIME_PATH)]
    actual = {row.key: (row.collection, row.primary_id, row.child_paths) for row in rows}
    expected = {
        family.key: (
            family.collection_name,
            family.id_field,
            _flatten_children(family.child_refs),
        )
        for family in RUNTIME_SERVICE_FAMILIES
    }
    if actual != expected:
        differing = sorted(key for key in actual.keys() | expected.keys() if actual.get(key) != expected.get(key))
        return [
            _failure(
                "sdl-catalog-runtime-family",
                f"runtime-family catalog differs for: {differing}",
                RUNTIME_PATH,
            )
        ]
    return []


def _phase_status(model: type[ScenarioContent], member: str) -> str:
    field = model.model_fields.get(member)
    if field is None:
        return "forbidden"
    return "required" if field.is_required() else "optional"


def _check_phase_members(text: str) -> list[PolicyFailure]:
    try:
        rows = parse_phase_member_catalog(text)
    except CatalogParseError as exc:
        return [_failure("sdl-catalog-phase-parse", str(exc), PHASES_PATH)]

    phase_models: tuple[tuple[str, type[ScenarioContent]], ...] = (
        ("normalized", Scenario),
        ("expanded", ExpandedScenario),
        ("instantiated", InstantiatedScenario),
    )
    shared = set(ScenarioContent.model_fields)
    expected_members = set().union(*(set(model.model_fields) - shared for _phase, model in phase_models))
    by_member = {row.member: row for row in rows}
    failures: list[PolicyFailure] = []
    if set(by_member) != expected_members:
        failures.append(
            _failure(
                "sdl-catalog-phase-members",
                "phase-specific member set differs: "
                f"catalog-only={sorted(set(by_member) - expected_members)}, "
                f"model-only={sorted(expected_members - set(by_member))}",
                PHASES_PATH,
            )
        )

    for member in sorted(set(by_member) & expected_members):
        row = by_member[member]
        actual = (row.normalized, row.expanded, row.instantiated)
        expected = tuple(_phase_status(model, member) for _phase, model in phase_models)
        if actual != expected:
            failures.append(
                _failure(
                    "sdl-catalog-phase-membership",
                    f"{member!r} phase membership is {expected!r}, catalog says {actual!r}",
                    PHASES_PATH,
                )
            )
        if not row.transfer:
            failures.append(
                _failure(
                    "sdl-catalog-phase-transfer",
                    f"{member!r} has no phase-transfer disposition",
                    PHASES_PATH,
                )
            )

    realization = by_member.get("realization")
    if realization is not None:
        designation_fields = (
            ("expansion_provenance", ExpansionProvenance),
            ("instantiation_provenance", InstantiationProvenance),
        )
        required_paths = {
            f"{provenance_field}.{field_name}"
            for provenance_field, model in designation_fields
            for field_name in model.model_fields
            if field_name == "realization_designations"
        }
        missing = sorted(path for path in required_paths if f"`{path}`" not in realization.transfer)
        if missing:
            failures.append(
                _failure(
                    "sdl-catalog-phase-transfer",
                    f"realization transfer omits portable designation paths: {missing}",
                    PHASES_PATH,
                )
            )
    return failures


def _check_internal_links(repo_root: Path, relative_paths: tuple[str, ...]) -> list[PolicyFailure]:
    root = repo_root.resolve()
    failures: list[PolicyFailure] = []
    for relative in relative_paths:
        source = repo_root / relative
        text = source.read_text(encoding="utf-8")
        for match in _MARKDOWN_LINK_RE.finditer(text):
            target = match.group("target").strip()
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            target_path = target.split("#", 1)[0]
            if not target_path:
                continue
            resolved = (source.parent / target_path).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                exists = False
            else:
                exists = resolved.exists()
            if not exists:
                line_no = text.count("\n", 0, match.start()) + 1
                failures.append(
                    _failure(
                        "sdl-catalog-link-target",
                        f"internal Markdown target at line {line_no} does not exist: {target_path}",
                        relative,
                    )
                )
    return failures


def _check_diagnostic_normative_layer(text: str) -> list[PolicyFailure]:
    failures: list[PolicyFailure] = []
    in_implementation_evidence = False
    for line_no, line in enumerate(text.splitlines(), start=1):
        is_quote = line.startswith(">")
        if is_quote and "Implementation evidence (non-normative)" in line:
            in_implementation_evidence = True
        elif not is_quote:
            in_implementation_evidence = False
        if _IMPLEMENTATION_TERM_RE.search(line) and not (is_quote and in_implementation_evidence):
            failures.append(
                _failure(
                    "sdl-catalog-normative-layer",
                    f"implementation-specific diagnostic term at line {line_no} is not marked non-normative",
                    DIAGNOSTICS_PATH,
                )
            )
    return failures


def evaluate_sdl_catalog_parity(repo_root: Path) -> list[PolicyFailure]:
    """Return deterministic parity failures for the normative SDL catalogs."""
    prose_paths = (
        SECTIONS_PATH,
        REFERENCES_PATH,
        RUNTIME_PATH,
        DOCUMENT_MODEL_PATH,
        VARIABLES_PATH,
        DIAGNOSTICS_PATH,
        PHASES_PATH,
    )
    required_paths = (*prose_paths, SCHEMA_PATH)
    missing = [relative for relative in required_paths if not (repo_root / relative).is_file()]
    if missing:
        return [
            _failure(
                "sdl-catalog-missing",
                f"required catalog authority is missing: {relative}",
                relative,
            )
            for relative in missing
        ]
    try:
        schema = json.loads((repo_root / SCHEMA_PATH).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [_failure("sdl-catalog-schema-parse", str(exc), SCHEMA_PATH)]
    sections_text = (repo_root / SECTIONS_PATH).read_text(encoding="utf-8")
    top_failures, top_rows = _check_top_level(sections_text, schema)
    failures = list(top_failures)
    failures.extend(
        _check_references(
            (repo_root / REFERENCES_PATH).read_text(encoding="utf-8"),
            top_rows,
            repo_root,
        )
    )
    failures.extend(_check_runtime((repo_root / RUNTIME_PATH).read_text(encoding="utf-8")))
    failures.extend(_check_phase_members((repo_root / PHASES_PATH).read_text(encoding="utf-8")))
    failures.extend(_check_diagnostic_normative_layer((repo_root / DIAGNOSTICS_PATH).read_text(encoding="utf-8")))
    failures.extend(_check_internal_links(repo_root, prose_paths))
    return failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate normative SDL catalog parity.")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON failures.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    failures = evaluate_sdl_catalog_parity(args.repo_root)
    exceptions_path = args.repo_root / "tools" / "policy" / "exceptions.yaml"
    if exceptions_path.is_file():
        failures = apply_exceptions(failures, load_exceptions(args.repo_root))
    if failures:
        if args.json:
            print(failures_to_json(failures))
        else:
            for failure in failures:
                print(failure.render(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
