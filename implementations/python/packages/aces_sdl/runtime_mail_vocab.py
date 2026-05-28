"""Controlled vocabularies for runtime mail-service inventory."""

from enum import Enum

__all__ = [
    "RuntimeMailAuthMechanism",
    "RuntimeMailComponentKind",
    "RuntimeMailCredentialClassification",
    "RuntimeMailDomainRole",
    "RuntimeMailListenerRole",
    "RuntimeMailMailboxRole",
    "RuntimeMailMailboxStatus",
    "RuntimeMailMailboxStoreKind",
    "RuntimeMailProtocol",
    "RuntimeMailQueueKind",
    "RuntimeMailQueueStability",
    "RuntimeMailRoutingKind",
    "RuntimeMailSettingProvenance",
    "RuntimeMailTlsMode",
]


class RuntimeMailProtocol(str, Enum):
    """Portable protocol family for a runtime mail listener or relationship."""

    SMTP = "smtp"
    ESMTP = "esmtp"
    SUBMISSION = "submission"
    SMTPS = "smtps"
    IMAP = "imap"
    IMAPS = "imaps"
    POP3 = "pop3"
    POP3S = "pop3s"
    LMTP = "lmtp"
    SIEVE = "sieve"
    OTHER = "other"


class RuntimeMailListenerRole(str, Enum):
    """Observed role a mail listener plays for the node-scoped mail service."""

    INBOUND_MX = "inbound_mx"
    SUBMISSION = "submission"
    MAIL_ACCESS = "mail_access"
    LOCAL_DELIVERY = "local_delivery"
    RELAY = "relay"
    LMTP = "lmtp"
    SIEVE = "sieve"
    MONITORING = "monitoring"
    OTHER = "other"


class RuntimeMailTlsMode(str, Enum):
    """Observed TLS/STARTTLS posture for a mail listener or relationship."""

    NONE = "none"
    STARTTLS_AVAILABLE = "starttls_available"
    STARTTLS_REQUIRED = "starttls_required"
    IMPLICIT_TLS = "implicit_tls"
    TLS_TERMINATED_UPSTREAM = "tls_terminated_upstream"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeMailAuthMechanism(str, Enum):
    """Portable mail authentication mechanism vocabulary."""

    NONE = "none"
    PLAIN = "plain"
    LOGIN = "login"
    CRAM_MD5 = "cram_md5"
    DIGEST_MD5 = "digest_md5"
    SCRAM_SHA_1 = "scram_sha_1"
    SCRAM_SHA_256 = "scram_sha_256"
    OAUTHBEARER = "oauthbearer"
    EXTERNAL = "external"
    ANONYMOUS = "anonymous"
    OTHER = "other"


class RuntimeMailComponentKind(str, Enum):
    """Portable component kind inside a runtime mail service."""

    MTA = "mta"
    MDA = "mda"
    IMAP_SERVER = "imap_server"
    POP3_SERVER = "pop3_server"
    SUBMISSION_AGENT = "submission_agent"
    MAILBOX_STORE = "mailbox_store"
    SPAM_FILTER = "spam_filter"
    ANTIVIRUS = "antivirus"
    QUEUE_MANAGER = "queue_manager"
    RELAY = "relay"
    POLICY_SERVICE = "policy_service"
    OTHER = "other"


class RuntimeMailDomainRole(str, Enum):
    """Role of a domain known to the mail service."""

    LOCAL_DELIVERY = "local_delivery"
    VIRTUAL = "virtual"
    RELAY = "relay"
    ALIAS = "alias"
    CATCH_ALL = "catch_all"
    OUTBOUND = "outbound"
    OTHER = "other"


class RuntimeMailMailboxStoreKind(str, Enum):
    """Observed mailbox storage backing kind."""

    MAILDIR = "maildir"
    MBOX = "mbox"
    DATABASE = "database"
    OBJECT_STORE = "object_store"
    REMOTE = "remote"
    OTHER = "other"


class RuntimeMailMailboxRole(str, Enum):
    """Portable role/classification of a service-local mailbox."""

    USER = "user"
    ADMIN = "admin"
    SERVICE = "service"
    SHARED = "shared"
    POSTMASTER = "postmaster"
    ABUSE = "abuse"
    AUTOMATED = "automated"
    OTHER = "other"


class RuntimeMailMailboxStatus(str, Enum):
    """Observed account status for a service-local mailbox."""

    ENABLED = "enabled"
    DISABLED = "disabled"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeMailCredentialClassification(str, Enum):
    """Semantic classification of a mailbox credential, never its raw value."""

    NO_CREDENTIAL = "no_credential"
    WEAK = "weak"
    DEFAULT_OR_TRIVIAL = "default_or_trivial"
    FIXTURE = "fixture"
    STRONG = "strong"
    REDACTED = "redacted"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeMailRoutingKind(str, Enum):
    """Portable mail routing/aliasing rule kind."""

    ALIAS = "alias"
    FORWARD = "forward"
    VIRTUAL_ALIAS = "virtual_alias"
    RELAY = "relay"
    LOCAL_DELIVERY = "local_delivery"
    CATCH_ALL = "catch_all"
    LIST = "list"
    OTHER = "other"


class RuntimeMailQueueKind(str, Enum):
    """Observed mail queue kind."""

    INCOMING = "incoming"
    ACTIVE = "active"
    DEFERRED = "deferred"
    HOLD = "hold"
    BOUNCE = "bounce"
    CORRUPT = "corrupt"
    MAILDROP = "maildrop"
    MAILBOX = "mailbox"
    OTHER = "other"


class RuntimeMailQueueStability(str, Enum):
    """Stability class for dynamic mail queue facts."""

    STEADY_STATE = "steady_state"
    DYNAMIC = "dynamic"
    VOLATILE = "volatile"
    LOG_DERIVED = "log_derived"
    UNKNOWN = "unknown"
    OTHER = "other"


class RuntimeMailSettingProvenance(str, Enum):
    """Origin/provenance class for a mail-service configuration setting."""

    CONFIGURATION_FILE = "configuration_file"
    COMMAND_OUTPUT = "command_output"
    IMAGE_DEFAULT = "image_default"
    OPERATOR_OVERRIDE = "operator_override"
    RUNTIME_DEFAULT = "runtime_default"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"
    OTHER = "other"
