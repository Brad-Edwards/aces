"""Semantic validation for SDL scenarios (package split of the former
validator.py). Public API is unchanged: import ``SemanticValidator``.
"""

from ._content_objectives import _ContentObjectivesMixin
from ._core import _ValidatorCore
from ._evidence_requirements import _EvidenceRequirementsMixin
from ._nodes_infra_network import _NodesInfraNetworkMixin
from ._relationships import _RelationshipsMixin
from ._relationships_proxy import _RelationshipsProxyMixin
from ._runtime_identity_data import _RuntimeIdentityDataMixin
from ._runtime_mail import _RuntimeMailMixin
from ._runtime_orchestration import _RuntimeOrchestrationMixin
from ._runtime_platform import _RuntimePlatformMixin
from ._runtime_services import _RuntimeServicesMixin
from ._sections import _SectionsMixin
from ._workflows_analysis import _WorkflowAnalysisMixin
from ._workflows_verify import _WorkflowVerifyMixin

__all__ = ["SemanticValidator"]


class SemanticValidator(
    _NodesInfraNetworkMixin,
    _RuntimeServicesMixin,
    _RuntimeIdentityDataMixin,
    _RuntimePlatformMixin,
    _RuntimeOrchestrationMixin,
    _RuntimeMailMixin,
    _RelationshipsMixin,
    _RelationshipsProxyMixin,
    _ContentObjectivesMixin,
    _EvidenceRequirementsMixin,
    _WorkflowAnalysisMixin,
    _WorkflowVerifyMixin,
    _SectionsMixin,
    _ValidatorCore,
):
    """Validates a Scenario beyond structural Pydantic checks.

    Call ``validate()`` to run all passes. Raises ``SDLValidationError``
    with all collected errors if any pass fails.
    """
