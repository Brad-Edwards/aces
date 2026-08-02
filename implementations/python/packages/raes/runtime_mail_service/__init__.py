"""Runtime mail-service inventory models for SDL nodes.

This surface expresses participant-observable mail-server logical state under
``Node.runtime``. Transport exposure remains in ``Node.services``; mail records
reference same-node services and add typed protocol, mailbox, routing, queue,
and configuration facts that do not fit HTTP routes, filesystem entries, or
generic scenario accounts.

This package is a thin facade over cohesive subdomains:

* :mod:`._elements` - the typed leaf records (components, listeners, domains,
  mailbox stores, mailboxes, aliases, routing rules, queues, settings).
* :mod:`._service` - the :class:`RuntimeMailService` aggregate and
  :class:`RelationshipMailAccess`.

The vocabulary enums re-exported below remain owned by :mod:`raes.runtime_mail_vocab`.
"""

from ..runtime_mail_vocab import (
    RuntimeMailAuthMechanism,
    RuntimeMailComponentKind,
    RuntimeMailCredentialClassification,
    RuntimeMailDomainRole,
    RuntimeMailListenerRole,
    RuntimeMailMailboxRole,
    RuntimeMailMailboxStatus,
    RuntimeMailMailboxStoreKind,
    RuntimeMailProtocol,
    RuntimeMailQueueKind,
    RuntimeMailQueueStability,
    RuntimeMailRoutingKind,
    RuntimeMailSettingProvenance,
    RuntimeMailTlsMode,
)
from ._elements import (
    RuntimeMailAlias,
    RuntimeMailComponent,
    RuntimeMailDomain,
    RuntimeMailListener,
    RuntimeMailMailbox,
    RuntimeMailMailboxStore,
    RuntimeMailQueue,
    RuntimeMailRoutingRule,
    RuntimeMailSetting,
)
from ._service import RelationshipMailAccess, RuntimeMailService

__all__ = [
    "RelationshipMailAccess",
    "RuntimeMailAlias",
    "RuntimeMailAuthMechanism",
    "RuntimeMailComponent",
    "RuntimeMailComponentKind",
    "RuntimeMailCredentialClassification",
    "RuntimeMailDomain",
    "RuntimeMailDomainRole",
    "RuntimeMailListener",
    "RuntimeMailListenerRole",
    "RuntimeMailMailbox",
    "RuntimeMailMailboxRole",
    "RuntimeMailMailboxStatus",
    "RuntimeMailMailboxStore",
    "RuntimeMailMailboxStoreKind",
    "RuntimeMailProtocol",
    "RuntimeMailQueue",
    "RuntimeMailQueueKind",
    "RuntimeMailQueueStability",
    "RuntimeMailRoutingKind",
    "RuntimeMailRoutingRule",
    "RuntimeMailService",
    "RuntimeMailSetting",
    "RuntimeMailSettingProvenance",
    "RuntimeMailTlsMode",
]
