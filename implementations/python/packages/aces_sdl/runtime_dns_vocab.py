"""Enum vocabulary for DNS runtime inventory models."""

from enum import Enum

__all__ = [
    "DnsForwarderTransport",
    "DnsForwardingPolicy",
    "DnsRecordClass",
    "DnsRecordProvenance",
    "DnsRecordType",
    "DnsServerImplementation",
    "DnsServiceRole",
    "DnsSettingProvenance",
    "DnsZoneKind",
    "DnsZonePurpose",
    "DnssecValidationMode",
]


class DnsServerImplementation(str, Enum):
    """Portable implementation family for the observed DNS service."""

    BIND = "bind"
    COREDNS = "coredns"
    POWERDNS = "powerdns"
    KNOT_DNS = "knot_dns"
    NSD = "nsd"
    WINDOWS_DNS = "windows_dns"
    DNSMASQ = "dnsmasq"
    UNBOUND = "unbound"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsServiceRole(str, Enum):
    """Role the DNS service performs for participants or peers."""

    AUTHORITATIVE = "authoritative"
    RECURSIVE_RESOLVER = "recursive_resolver"
    FORWARDING_RESOLVER = "forwarding_resolver"
    CACHING_RESOLVER = "caching_resolver"
    STUB_RESOLVER = "stub_resolver"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsZoneKind(str, Enum):
    """Portable zone role independent of one server's configuration grammar."""

    PRIMARY = "primary"
    SECONDARY = "secondary"
    STUB = "stub"
    FORWARD = "forward"
    HINT = "hint"
    CATALOG = "catalog"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsZonePurpose(str, Enum):
    """Semantic purpose of a zone name."""

    FORWARD = "forward"
    REVERSE = "reverse"
    SERVICE_DISCOVERY = "service_discovery"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsRecordClass(str, Enum):
    """DNS RR class."""

    IN = "in"
    CH = "ch"
    HS = "hs"
    NONE = "none"
    ANY = "any"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsRecordType(str, Enum):
    """Common DNS RR types plus an escape hatch for IANA extensions."""

    A = "a"
    AAAA = "aaaa"
    CNAME = "cname"
    NS = "ns"
    MX = "mx"
    PTR = "ptr"
    SOA = "soa"
    SRV = "srv"
    TXT = "txt"
    CAA = "caa"
    DS = "ds"
    DNSKEY = "dnskey"
    RRSIG = "rrsig"
    NSEC = "nsec"
    NSEC3 = "nsec3"
    TLSA = "tlsa"
    SVCB = "svcb"
    HTTPS = "https"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsRecordProvenance(str, Enum):
    """Where an observed DNS record or zone fact came from."""

    AXFR = "axfr"
    IXFR = "ixfr"
    QUERY = "query"
    CONFIGURATION_FILE = "configuration_file"
    ZONE_FILE = "zone_file"
    PROVIDER_API = "provider_api"
    RUNTIME_DEFAULT = "runtime_default"
    OPERATOR_OVERRIDE = "operator_override"
    UNKNOWN = "unknown"
    OTHER = "other"


class DnsForwarderTransport(str, Enum):
    """Transport used to contact a recursive upstream."""

    UDP = "udp"
    TCP = "tcp"
    TLS = "tls"
    HTTPS = "https"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnsForwardingPolicy(str, Enum):
    """How upstream forwarders are used."""

    FIRST = "first"
    ONLY = "only"
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    SEQUENTIAL = "sequential"
    NONE = "none"
    OTHER = "other"
    UNKNOWN = "unknown"


class DnssecValidationMode(str, Enum):
    """Recursive DNSSEC validation posture."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    AUTO = "auto"
    PERMISSIVE = "permissive"
    UNKNOWN = "unknown"
    OTHER = "other"


class DnsSettingProvenance(str, Enum):
    """Where an observed DNS setting value came from."""

    CONFIGURATION_FILE = "configuration_file"
    INTROSPECTION = "introspection"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    UNKNOWN = "unknown"
    OTHER = "other"
