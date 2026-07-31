# Issue 85 / AUT-802 human CLI preflight

Date: 2026-07-31

Issue: #85. Requirement payload: none. The issue title, body, acceptance
criteria, and non-goals are the authoritative contract.

This note fixes architecture guardrails for the RAES semantic CLI. It does not
implement commands or prescribe an implementation sequence. No new ADR is
needed: ADR-008, ADR-009, ADR-036, ADR-053, ADR-061, ADR-075, ADR-078, and the
SDL diagnostics specification already decide the relevant ownership,
authority, phase, evolution, and error boundaries.

## Decisions and boundaries

### The CLI is an adapter, not a second semantic engine

`raes_cli` owns argument handling, input/output selection, rendering, and exit
status. It must call the public owning APIs in `raes`, `raes_processor`,
`raes_contracts`, and `raes_conformance`; it must not reproduce parsing,
normalization, reference resolution, compilation, contract admission, or
conformance logic in command handlers.

Each invocation produces one typed, command-specific result before rendering.
Human and JSON renderers consume that same object, including the same status,
selected versions/profiles, provenance, payload, and diagnostic records. Do not
create parallel “human” and “JSON” execution paths or a universal ecosystem
result schema. Existing published domain models remain authoritative for their
payloads; CLI result metadata must not reinterpret them as a new portable
artifact family.

Machine mode writes exactly one deterministic JSON document and a trailing
newline to stdout. Human mode writes the requested artifact or summary to
stdout and diagnostics to stderr. Progress, banners, tracebacks, and logging
never contaminate machine stdout. Canonical artifact bytes remain the output of
the existing RFC 8785 canonicalization APIs; pretty, stable CLI JSON is not
silently relabelled as canonical JSON.

The exit taxonomy is centralized and non-overlapping:

| Status | Exit |
|---|---:|
| Operation completed successfully, including a supported negative analysis conclusion such as unsatisfiable | 0 |
| Authored or portable input is rejected by parse, structural, semantic, admission, or conformance checks | 1 |
| CLI usage, selector, or mutually-exclusive-option error | 2 |
| Typed `unsupported` outcome under the selected operation/profile | 3 |
| Bounded input/output or other expected operational failure | 4 |
| Sanitized unexpected internal failure | 70 |

Existing analysis commands currently use exit `2` for typed unsupported
results, which collides with Typer usage errors. AUT-802 must not preserve that
ambiguity as the stable surface. Any compatibility treatment follows ADR-075;
do not keep two meanings for one code.

### Operation names do not collapse phase concepts

- **Parse** performs bounded decoding, source-profile checks, structural
  closure, canonical field recognition, typed construction, and no implied
  semantic-validity claim. For SDL it yields the existing normalized authoring
  phase, not an instantiated or compiled artifact.
- **Validate** runs the owning admission/semantic checks for the explicitly
  selected input contract and validation profile. Schema/Pydantic validity,
  SDL semantic validity, context-dependent semantic admission, and conformance
  are distinct outcomes and must be disclosed with the exact validation
  strength.
- **Normalize** emits the deterministic normalized representation of an
  admitted input and reports the source format, migration policy, normalization
  profile, source diagnostics, and any semantic/canonical digest that actually
  applies. It does not mean source formatting, migration, reference resolution,
  instantiation, canonical byte serialization, or provider-name sanitization.
- **Resolve** performs RAES-owned reference/module composition under an
  explicit resolution policy. Reference lookup must reuse the declaration
  index and semantic resolver. Module acquisition, registry lookup, lockfile
  creation, and pack discovery are not hidden inside this verb.
  `ExpandedScenario` remains an internal trusted phase, not a stable wire
  artifact; resolve may return typed resolution/provenance data or feed a later
  phase, but must not serialize that private representation as a new contract.
- **Compile** uses `compile_scenario_runtime_model()` after normal SDL phase
  admission. It stops before backend planning or apply. `RuntimeModel` is an
  internal dataclass graph, not a published wire contract: never expose
  `asdict()`, `__dict__`, `default=str`, or MCP summary dictionaries as the
  stable compiled artifact. A full machine-readable compile artifact requires
  one governed typed projection; until such a contract exists, the stable
  result may only claim compilation status and a bounded typed inspection
  summary.
- **Transform** is a closed selector over transformations RAES already owns,
  such as explicit source migration/formatting, instantiation, and canonical
  snapshot production. It is not a generic plugin, script, patch, backend
  translation, or pack conversion facility. Each transformation names its
  input phase, output phase, profile, and provenance.
- **Inspect** queries admitted typed objects and the canonical declaration,
  address, and reference indexes. The MCP inspection helpers under
  `raes_mcp.tools.inspection` are presentation-specific, incomplete
  best-effort maps that can render raw values; they are not semantic authority
  and must not become the shared CLI implementation.
- **Conformance** invokes RAES-owned local contract/fixture checks and returns
  the existing typed reports and diagnostics. It does not start a target,
  invoke a backend, mutate runtime state, or elevate fixture-only evidence into
  native conformance.

Defaults may exist, but the result always records the effective contract id,
source format, migration policy, normalization/transform profile, validation
profile or strength, and processor/conformance profile. Portable-contract
input requires an explicit contract id; selection must never be guessed from a
filename, a permissive union, or the first model that accepts the payload.

### Files and streams share one bounded ingress

Every input-taking operation accepts either one path or `-` for stdin. Both
routes feed the same bounded byte decoder and typed operation. A stream with
relative imports has no implicit base directory; it requires an explicit safe
base/resolution input or returns typed unsupported. Pack layout, current
working-directory search, parent-directory search, and catalog discovery are
never inferred.

Ordinary parse, validate, normalize, compile, transform, and inspect are
read-only. Writes occur only for an explicit output destination or explicit
in-place transform, with no implicit overwrite. Lockfiles, caches, OCI layouts,
evidence archives, runtime stores, and temporary project trees are not
incidental outputs.

File-backed `parse_sdl_file()` currently composes imports, and OCI composition
can perform network requests and extract into `.raes/module-cache`. The current
`raes sdl resolve` writes `raes.lock.json`; `raes sdl publish` writes an OCI
layout. The AUT-802 path therefore needs an explicit offline resolution policy
at the parser/composition seam and must not wrap those handlers directly.
Remote acquisition, lock generation, publication, and pack-aware orchestration
belong to env-packs. A separately and explicitly selected handoff may invoke an
installed env-packs tool, but RAES does not import or duplicate its authority.

The existing top-level `libvirt` and `corpus` commands exercise backend,
lifecycle, and evidence workflows. They are outside the stable RAES semantic
surface and must be migrated to their owning backend/tooling entry points under
ADR-075 rather than being relabelled as semantic operations. The same applies
to `sdl publish`.

## Canonical incumbents to reuse

- **SDL ingress:** `read_sdl_source()`, `SDLSourceParseOptions`,
  `SDLParserLimits`, `load_sdl_yaml()`, mapping-key preflight,
  `_load_normalized_data()`, `parse_sdl()` / `parse_sdl_file()`, closed
  `Scenario` models, and `SemanticValidator`.
- **Phases and transformations:** `format_sdl_source()`,
  `instantiate_scenario()`, `admit_instantiated_scenario()`,
  `canonical_sdl_bytes()` / `canonical_sdl_digest()`, and
  `canonical_instantiated_sdl_bytes()` /
  `canonical_instantiated_sdl_digest()`. Preserve the normalized, expanded,
  instantiated, and snapshot distinctions from ADR-078.
- **Resolution:** `build_declaration_index()` and the canonical reference
  resolver for semantic references; ADR-053 composition, `TrustPolicy`,
  lock/digest/signature checks, OCI bounds, and safe archive extraction only
  when an explicit non-CLI acquisition workflow owns those effects.
- **Portable contracts:** `ContractModel(extra="forbid")`,
  `parse_bounded_json_object()` for object-root contracts, the models and
  version constants in `raes_contracts`, `schema_bundle()`, published
  schemas/fixtures, and the schema-publication manifest. Published schemas
  remain normative; Python models prove parity. Event-stream contracts have
  array roots, so extend the same bounded, duplicate-rejecting JSON ingress
  boundary for the root shapes named by the contract registry rather than
  bypassing it with `json.loads()`.
- **Contract/conformance admission:** the public
  `raes_conformance.conformance.validate_contract_payload()` registry,
  `_fixture_case_diagnostics()` / semantic dispatch behavior,
  `run_fixture_suite()`, `BackendConformanceReport`, and
  `backend_conformance_report_payload()`. Do not add a third contract-id
  switch in `raes_cli`. The existing structural-only and
  semantic-context-required distinctions must be retained in the result.
- **Compilation:** `compile_scenario_runtime_model()` and
  `compile_runtime_model()`. Do not route compile through
  `run_reference_processor()`, because that adds backend-manifest selection and
  planning. Reuse `raes_contracts.plan_projection` only for the separate
  existing plan-inspection compatibility surface; a plan is not a compile
  result.
- **Diagnostics:** `SDLParseDiagnostic`, `SDLParseError`,
  `SDLValidationError`, `SDLInstantiationError`,
  `raes_contracts.diagnostics.Diagnostic` / `DiagnosticModel`, parser
  diagnostic projection, and the value-free Pydantic sanitization in
  `raes_conformance.conformance.diagnostics.sanitized_failure_message()`.
  Promote/reuse that sanitization behavior at a public owning seam rather than
  copying another exception renderer.
- **CLI and tests:** the `raes_cli.main` Typer root, `CliRunner`, current
  deterministic JSON tests, invalid-input redaction tests, installed console
  script tests, stdin/subprocess tests, and output contract round-trip tests.
- **Governance/workflow:** `specs/sdl/diagnostics.md`,
  `specs/formal/sdl-phases/README.md`, ADR-014, ADR-036, ADR-061, ADR-075,
  `tools/policy/adr_policy.yaml`, `.ground-control.yaml`,
  `.gc/plan-rules.md`, `noxfile.py`, and the generated-schema, authority,
  public-docs, policy, lint, unit, and integration gates.

The existing contract validator registry and `schema_bundle()` are already two
lists of supported contract ids with different purposes and incomplete
overlap. CLI support must extend or project from an owning registry and add a
parity test; a third handwritten map would guarantee drift. The extension seam
is a contract-id descriptor that selects the existing bounded decoder, owning
typed model, semantic/context admission, supported operations, and effective
profile. Adding a future contract or validation profile changes that seam, not
every renderer and command.

## Cross-cutting security and runtime layers

| Layer | Required behavior |
|---|---|
| Authentication/authorization | This is a local authoring process with no auth principal and no control-plane authority. Do not import `raes_runtime`, auth middleware, backend registries, or control-plane APIs. Filesystem access is only the invoking OS user's existing authority. |
| OS/process exposure | Argv may carry paths, bounded identifiers, format names, and profile/contract selectors. Parameter maps, tokens, credentials, private keys, trust-policy bodies, and source text do not belong in argv or environment variables; use bounded stdin/files and the existing `scenario-instantiation-request-v1` shape. Never spawn a shell or backend. |
| Byte/shape ingress | Bound file/stdin bytes before decode. SDL goes through UTF-8, YAML token/graph/resource limits, JSON-domain and duplicate/collision checks. Object-root portable JSON goes through `parse_bounded_json_object()`; array-root event streams need the same bounded, duplicate-rejecting decoder before their owning event model. Do not use bare `read_text()`, `json.loads()`, `yaml.safe_load()`, or direct model construction as a public ingress shortcut. |
| Config/profile shapes | Source format, migration policy, contract id, transform profile, validation profile, and resolution mode are closed selectors. Reuse `SDLSourceParseOptions`, `SDLMigrationPolicy`, contract version constants, validation-profile catalog selection, and conformance profile loading. Unknown selectors fail before work; no environment-derived hidden default. |
| Semantic/admission gates | SDL passes structural construction, semantic validation, instantiation/admission when required, and declaration/address collision checks. Portable artifacts pass their owning model and any semantic/context validator. “Structural only” and “semantic context required” remain explicit outcomes. |
| Module/network boundary | Offline/no-cache is the semantic CLI default. Local paths remain contained, locked content remains digest checked, and no OCI request, archive extraction, cache write, or trust-policy discovery occurs unless an explicit owning acquisition workflow was selected outside the semantic command. |
| Secret handling | Explicit `redacted` / `operator_secret` omission remains enforced. Diagnostics, summaries, provenance metadata, and logs never echo input values, parameter maps, `allowed_values`, source bodies, trust policies, request headers, credentials, or raw framework errors. A command explicitly emitting a normalized/transformed artifact may contain values already present in that requested artifact; do not duplicate them into diagnostics or logs. |
| Error envelope | Bound diagnostic code, stage/domain, severity, RFC 6901 address/path, safe source range, selected profiles, and count are permitted. Raw `str(exc)`, Pydantic `input`, context, docs URL, absolute cache path, traceback, and terminal control characters are not. JSON failures still use the typed result; expected invalid input is not an unstructured stderr-only exception. |
| Output/filesystem | Stdout/stderr and exit status are the default observability surface. Explicit file output must avoid accidental clobbering and partial writes and must not follow an unrelated pack layout. No lockfile, cache, database, `ControlPlaneStore`, telemetry record, audit event, or evidence archive is created. |
| Logging/telemetry | No new logging framework or telemetry is justified. If library code logs in the future, it receives only value-free operation metadata and diagnostic codes, never artifact payloads. |
| Host/runtime | No daemon, socket, browser/MCP server, backend process, container/libvirt connection, permission change, or lifecycle action is part of these commands. Hub and backend tools remain separate processes and authorities. |

## Gotchas and anti-patterns

Avoid:

- treating parse success as semantic validity, schema validity as full
  contract admission, conformance as validation, or fixture success as native
  execution evidence;
- treating source formatting, migration, normalized authoring, canonical
  semantic identity, instantiation, and generic transformation as synonyms;
- guessing contracts or versions from extensions, payload fields, or whichever
  Pydantic union branch accepts first;
- calling `parse_sdl_file()` with imports under a supposedly pure command
  without an offline resolver guard;
- reusing MCP `compile_pipeline()`, language-service plain dictionaries,
  best-effort MCP reference maps, or human strings as the CLI service contract;
- serializing internal dataclasses, private validation flags, resources maps,
  backend manifests, snapshots, or arbitrary object representations;
- duplicating schema lists, validator registries, semantic dispatch,
  diagnostic codes, exception hierarchies, profile catalogs, or workflow logic;
- accepting inline `--parameter`, credential, private-key, registry-token, or
  environment bindings that expose values in process listings;
- emitting source values, parameter values, filenames containing sensitive
  markers, exception messages, or terminal escapes in diagnostics;
- writing a lockfile/cache/output merely because the input was file-backed;
- letting human and JSON renderers rerun the operation or decide status
  independently;
- preserving the current exit-`2` collision between usage and unsupported;
- retaining the public CLI guide's current claim that `sdl resolve` prints a
  composed scenario when the implementation actually writes a lockfile;
- importing runtime, backend, env-packs, or Hub code into RAES semantic
  services, or moving pack/backend authority behind a RAES-shaped command.

## Non-goals

- A universal ecosystem CLI, generic plugin framework, or arbitrary
  transformation engine.
- Pack scaffolding, discovery, layout, lock generation, publication, catalog
  search, or pack-aware validation orchestration.
- Remote module acquisition as an implicit consequence of semantic parsing or
  validation.
- Backend translation, planning as part of compile, realization, provisioning,
  runtime control, experiment execution, evidence collection, or lifecycle
  management.
- Browser, MCP, Hub, daemon, or service presentation.
- New authentication, persistence, logging, telemetry, audit, or secret-store
  infrastructure.
- Replacing published domain schemas with a CLI envelope, exposing an internal
  `RuntimeModel` as a portable contract, or creating a duplicate validation or
  exception hierarchy.
- Implementing commands, renderers, registries, schemas, migrations, or tests
  in this preflight.
