# Participant Interactive Access: Lineage And Design Synthesis

This bounded review supports issue #805 and DSL-117. It asks how a portable
scenario language should state that one role-neutral participant may be offered
interactive access to one scenario VM, without turning authored intent into a
backend locator, credential, runtime session, or proof of realization.

## Selection criteria

Sources were included when they exposed at least one relevant concern: an
explicit range entry host, a participant-local host/session binding, a protocol
class, or a separation between authored access and transport realization.
Source code was reviewed at exact Git revisions recorded in the SDL lineage
ledger. Standards interpret protocol classes; they do not import wire contracts
into SDL.

## Primary analogues

### CyRIS 1.2

CyRIS marks an exercise guest with `entry_point: yes`. Its realization code
then selects TCP 3389 for `windows.7` and TCP 22 otherwise while building
tunnels and entry accounts. This is a useful precedent for explicit entry-host
eligibility, but not for channel semantics: OS inference makes authored intent
implicit and its addresses, ports, tunnels, and generated credentials are
deployment facts. ACES therefore adapts only the explicit-selection concern.

Reviewed revision:
[`5f0d7843fed3dff782f7f62da9f8bcaa9a2a7481`](https://github.com/crond-jaist/cyris/tree/5f0d7843fed3dff782f7f62da9f8bcaa9a2a7481).

### CybORG v3.0

CybORG scenario YAML places `starting_sessions` under an agent and can state a
session name, username, hostname, and `type: SSH`. That is the closest
participant-local analogue. It describes simulator state that already exists,
however, rather than permission to offer an external access carrier. ACES
adapts participant-local explicit binding while keeping session lifecycle and
runtime state out of authoring.

Reviewed revision:
[`a2d03f99e587af153ae0ac50fb94ba6272e4fff2`](https://github.com/cage-challenge/CybORG/tree/a2d03f99e587af153ae0ac50fb94ba6272e4fff2).

### Protocol standards

[RFC 4251](https://www.rfc-editor.org/rfc/rfc4251) separates the SSH transport,
user-authentication, and connection protocols. The
[MS-RDPBCGR specification](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-rdpbcgr/)
defines RDP as a protocol family. ACES uses `ssh` and `rdp` only as closed
portable protocol classes. Neither value asserts a default port, daemon,
listener, account authentication mechanism, route, or successful connection.

## Screened-out shapes

- Open Cyber Range SDL `Role` username/entity bindings model node-local login
  roles but do not identify an interactive protocol or participant-to-node
  access declaration.
- KYPO user-access Ansible roles explicitly provision SSH keys/passwords and
  RDP access per host. They are realization precedents, but mix deployment and
  credential mechanics that do not belong in backend-neutral SDL authoring.
- CRACK access patterns are scenario-graph/query paths, not participant portal
  access carriers.
- Shifter's `{target_ref, channel}` declaration is a motivating consumer shape,
  not external language authority. Its realization adds addresses, ports, and
  credential references only after authoring, reinforcing the phase boundary.

## ACES synthesis

ACES uses a keyed `agents.*.interactive_access` registry. Stable local keys
support composition, diagnostics, future evidence linkage, and evolution
without assigning meaning to list order. Each closed value contains a VM
`target_ref`, an `ssh` or `rdp` channel, and an optional authored `account_ref`.

The optional account must belong to the target VM and already be present in the
participant's `starting_accounts`; the access declaration does not become a
second implicit credential grant. A target/channel pair is unique within one
participant after canonical reference resolution, while different participants
may independently receive the same carrier.

The declaration is authored availability only. It does not imply operating
scope, action authority, a shell tool affordance, apparatus support, caller
authentication, credential delivery, listener presence, runtime session state,
or realization evidence. Absence means no authored interactive access, and no
other SDL or runtime fact creates one by inference.
