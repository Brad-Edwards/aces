# RAES Identity Cutover

RAES is the sole current identity of the Reproducible Agentic Environments
System and its repository-owned ecosystem surfaces.

Issue #908 and GOV-944 complete the hard cut begun by issue #866. The cutover
does not retain public aliases or dual-name compatibility.

## Current Surface Map

| Surface | Current identity | Verification |
|---|---|---|
| Python distribution and imports | `raes` and the owning `raes_*` packages | installed wheel and source-boundary tests |
| CLI and MCP commands | `raes`, `raes-mcp` | CLI and MCP construction tests |
| MCP server and tools | RAES server metadata and `raes_*` tool identifiers | advertised-tool and guidance tests |
| Published schema namespace | `https://raes.dev/schemas/` | generated parity and schema-publication checks |
| Contract/profile identities | RAES contract, profile, annotation, and wire identifiers | contract models, fixtures, JSON Schema validation |
| Module artifacts | `raes.lock.json`, `raes-trust.yaml`, `.raes/module-cache`, RAES OCI media types and labels | registry, digest, signature, archive, and CLI tests |
| Runtime and evidence artifacts | RAES schema names, event/status values, evidence ids, and resource names | DTO, fixture, persistence, and backend tests |
| Authentication | RAES trusted-proxy headers | strict-default auth, role, denial-audit, and redacted-error tests |
| Environment/workflow | RAES requirement-governance and real-libvirt inputs | repository policy and opt-in integration tests |
| Host ownership | RAES OCI labels, libvirt names, guest markers, paths, and UUID namespace | conflict, discovery, teardown, guest-probe, and real-daemon tests |
| Documentation and examples | RAES terminology and paths | documentation build and whole-tree naming policy |

## Compatibility Rule

Current readers, writers, commands, and configuration accept only RAES
identities. Existing consumers must update before adopting the cutover release.
There are no aliases, shims, fallback imports, redirects, dual-read paths, or
last-one-wins resolution rules.

Published contract changes still carry their owning schema-publication and
lifecycle evidence. That evidence records what changed; it does not keep the
retired value executable.

## Historical Records

Accepted pre-cutover decisions, release history, provenance, and dated research
or design evidence remain accurate historical records. The whole-tree naming
policy permits such content only through exact path, content digest, record
class, rationale, and occurrence-count entries. It does not exempt a
documentation directory or allow historical wording to become current
guidance.

## Operator Guidance

Use `raes` and `raes-mcp` in automation. Use RAES contract, schema, module,
runtime, header, environment, and host identifiers in newly created artifacts
and deployments.

The hard cut does not automatically rewrite persisted artifacts or clean
resources created under an earlier identity. Operators should complete any
required environment cleanup before deploying the cutover release; the
repository does not discover or destroy old-name resources.
