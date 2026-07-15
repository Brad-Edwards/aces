"""Relationship models — typed directed edges between scenario elements.

Adapted from STIX 2.1 Relationship SROs and OCR's dependency patterns.
Provides a general-purpose mechanism for expressing how services,
nodes, and accounts relate to each other — authentication chains,
trust relationships, federation, and connectivity.

This is how identity emerges in the SDL: accounts describe *who*,
features describe *what provides auth*, and relationships describe
*how they connect*.
"""

from enum import Enum

from pydantic import Field, field_validator

from ._base import SDLModel, normalize_enum_value
from .identity_domains import RelationshipDomainController, RelationshipDomainJoin
from .runtime_application import RelationshipProxyUpstream
from .runtime_database import RelationshipDatabaseAccess
from .runtime_forwarding_agent import RelationshipForwardingEdge
from .runtime_mail_service import RelationshipMailAccess
from .runtime_platform_application import RelationshipServiceIntegration


class RelationshipType(str, Enum):
    """How two scenario elements relate to each other."""

    AUTHENTICATES_WITH = "authenticates_with"
    TRUSTS = "trusts"
    FEDERATES_WITH = "federates_with"
    CONNECTS_TO = "connects_to"
    DEPENDS_ON = "depends_on"
    MANAGES = "manages"
    REPLICATES_TO = "replicates_to"
    DOMAIN_CONTROLLER_FOR = "domain_controller_for"
    JOINS_DOMAIN = "joins_domain"


class Relationship(SDLModel):
    """A typed directed edge between two named scenario elements.

    Source and target can reference any named element in the scenario:
    nodes, features, accounts, entities, or infrastructure entries.
    The validator checks that both endpoints resolve.

    The ``properties`` dict carries type-specific metadata (e.g.,
    ``trust_type: parent-child`` for AD trusts, ``protocol: SAML``
    for federation). It's a flat dict rather than typed sub-models
    because relationship properties vary widely and we don't want
    to gate expressiveness on pre-modeling every variant.

    ``database_access`` and ``mail_access`` are typed exceptions where
    protocol/auth details need structural validation rather than prose.
    ``forwarding_edge``, ``service_integration``, and ``proxy_upstream`` are
    the same kind of typed exception for, respectively, a forwarding /
    intel-sync agent's inter-node trust edge (SCN-010 §5.7), a platform
    consumer-to-engine service integration, and a reverse-proxy/gateway
    route-to-origin upstream hop. Each keeps protocol/auth/topology facts
    structurally validated and cross-referable rather than buried in prose.
    """

    type: RelationshipType
    source: str
    target: str
    description: str = ""
    properties: dict[str, str] = Field(default_factory=dict)
    database_access: RelationshipDatabaseAccess | None = None
    mail_access: RelationshipMailAccess | None = None
    forwarding_edge: RelationshipForwardingEdge | None = None
    service_integration: RelationshipServiceIntegration | None = None
    proxy_upstream: RelationshipProxyUpstream | None = None
    domain_controller: RelationshipDomainController | None = None
    domain_join: RelationshipDomainJoin | None = None

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        return normalize_enum_value(v)
