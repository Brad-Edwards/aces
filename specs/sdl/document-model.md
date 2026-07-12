# SDL Document Model

This file defines how an SDL document is encoded, how its top-level surfaces are
organised, what is required, how user-defined identifiers are formed, how the
document is structurally closed, and the phases a document passes through from
authoring to instantiation.

See [`sections.md`](sections.md) for the per-section catalog,
[`references.md`](references.md) for reference resolution, and
[`variables-and-instantiation.md`](variables-and-instantiation.md) for variable
and instantiation rules.

## 1. Source profile: `sdl-yaml/v1`

Canonical SDL source uses the versioned profile `sdl-yaml/v1`. A conforming
strict decoder **MUST** apply all of the following rules before model
construction:

1. The byte stream **MUST** be valid UTF-8 and contain exactly one YAML 1.2.2
   document. Its root **MUST** be a mapping. A sequence, scalar, null root, or
   multi-document stream is invalid.
2. Untagged plain scalars **MUST** resolve with the YAML 1.2.2 Core schema
   ([§10.3](https://yaml.org/spec/1.2.2/#103-core-schema)). Thus `true`, `FALSE`,
   `null`, `0o12`, and `0x0a` are typed Core values, while `yes`, `on`, a date
   spelling, `1_000`, and `-0x0a` are strings. This rule applies in key position:
   unquoted `true` is a boolean key and is invalid, while unquoted `on` is a
   string identifier.
3. Every mapping key **MUST** construct as a string. Complex keys and scalars
   resolved to null, boolean, integer, or float are invalid as keys. Quoting a
   Core-looking identifier is sufficient to keep it a string.
4. Explicit tags and YAML directives **MUST NOT** appear. Only safe standard
   construction of implicitly resolved Core values is permitted. Document
   start/end markers are presentation syntax, not directives, and **MAY** appear.
5. Constructed values **MUST** be in the JSON data domain: null, boolean,
   arbitrary-precision integer, finite binary64-compatible float, Unicode
   string, sequence, or string-keyed mapping. Timestamps, sets, language-native
   objects, non-finite floats, and other tag-specific values are invalid.
6. Anchors and aliases **MAY** share acyclic representation nodes; their names
   and sharing carry no SDL meaning. Cyclic aliases are invalid. The YAML 1.1
   `<<` merge extension is not YAML 1.2.2 Core syntax and is invalid canonical
   SDL; §5 defines its explicit migration treatment.
7. Every authored mapping entry **MUST** remain distinguishable until key
   uniqueness is checked. Exact duplicates and canonical-field collisions are
   invalid; a decoder **MUST NOT** construct a last-write-wins mapping first.
8. No Unicode normalization is performed. Code-point sequences remain as
   authored after YAML escape processing.

The profile has fixed denial-of-service bounds: at most 8 MiB of UTF-8 source,
1 MiB in one scalar, depth 128, 100,000 unique representation nodes, 256 alias
occurrences, and 250,000 nodes of alias-expanded traversal work. Exceeding any
bound is a source error. A future syntax, scalar policy, or incompatible limit
set requires a new source-profile identifier.

This uniqueness rule follows the YAML 1.2.2 representation model, in which a
mapping is an unordered association of unique keys and non-unique keys are a
loading failure ([YAML 1.2.2 §§3.2.1.1, 3.3](https://yaml.org/spec/1.2.2/)).

## 2. Top-level organisation

The top-level fields divide into two kinds, which **MUST** be kept distinct:

- **Metadata and composition fields** describe the document itself and how it
  composes with other documents. They are not authoring sections.
- **Authoring sections** carry the scenario content. Most are **maps** keyed by
  user-defined identifiers; one is a **list** (see [`sections.md`](sections.md)).

The complete, authoritative enumeration of top-level fields, their kinds, value
shapes, and requiredness is the [section catalog](sections.md), which is written
to match `contracts/schemas/sdl/sdl-authoring-input-v1.json`.

> **Reconciliation note.** Earlier descriptions treated the authoring surface
> as uniformly map-keyed. The live contract is **not** uniform:
> `forwarding_agents` is list-valued, and the participant surfaces (`action_contracts`,
> `observation_boundaries`, `outcome_interpretation_rules`) are present. The
> section catalog states and mechanically checks the live set; this specification reconciles the
> language to the published schema rather than freezing a historical count.

## 3. Requiredness

1. `name` is the only **REQUIRED** top-level field. A document without `name` is
   invalid.
2. Every other top-level field is **OPTIONAL**. An omitted authoring section is
   equivalent to an empty one (an empty map, or an empty list for the
   list-valued section); an omitted metadata field takes its documented default.
3. Requiredness **within** a section's elements (for example, a field that a
   `node` or a runtime family element must carry) is governed by that section's
   schema and, for runtime families, by the owning family ADR
   ([runtime-inventory.md](runtime-inventory.md)).

## 4. Structural closure (fail-closed)

1. SDL models are **closed**: an unknown key — at the top level or anywhere
   within a nested model — **MUST** be rejected, not ignored. There is no
   permissive "extra fields allowed" mode.
2. Rejection of an unknown or malformed key is a **parse/structural** failure
   (see [`diagnostics.md`](diagnostics.md)); it occurs before semantic
   validation and is fatal.
3. Closure exists so that a typo in a field name (`vulnerabilites`) fails the
   document rather than silently dropping content. Authors **MUST NOT** rely on
   undeclared keys to carry data.
4. Anchors and aliases do not weaken closure or uniqueness. Migration-mode
   merge input is accepted only when every inherited and local effective field
   is disjoint; override precedence is never SDL semantics.

> *Implementation evidence (non-normative): the reference models set
> `extra="forbid"` on the shared SDL base model.*

## 5. Canonical fields, literal keys, and migration

1. Enum-valued fields accept their value case-insensitively, and accept a hyphen
   as an alias for an underscore in the value text, so that an authoring value
   such as `search-index` and `search_index` denote the same enum member. This
   is an authoring convenience; the normalised (canonical) form is what the
   document means.
2. A structural field key **MUST** use its exact lower-case `snake_case` schema
   spelling. `semantic_version` is canonical; `semantic-version`,
   `Semantic_Version`, and `SEMANTIC_VERSION` are not canonical SDL source.
3. A tool **MAY** offer an explicit migration operation that recognizes legacy
   case and hyphen spellings and `<<` merges. Migration is never implicit: the
   strict/default policy rejects each construct. An accepting migration policy
   **MUST** emit a source-ranged advisory for every rewritten field or merge,
   and its output **MUST** pass strict `sdl-yaml/v1` decoding. Unrecognized
   fields remain errors.
4. Migration aliases do not create a precedence rule. If two keys in one
   effective mapping address the same canonical field, including through a YAML
   merge, the mapping is ambiguous and **MUST** fail during parsing before model
   construction. The diagnostic contract is defined in
   [diagnostics.md §6](diagnostics.md).
5. Field recognition applies only while traversing a schema-defined
   structural mapping. It **MUST NOT** be applied to user-defined identifier
   maps, extension maps, or native option/label maps. Keys in those maps are
   preserved verbatim, including case, hyphens, and underscores; only exact
   duplicate identifiers are rejected. Core scalar resolution still applies,
   so boolean/null/numeric-looking identifiers must be quoted when necessary.
6. A field that holds a variable placeholder (`${…}`) is **not** normalised as an
   enum value; the placeholder is preserved until instantiation
   ([variables-and-instantiation.md](variables-and-instantiation.md)).

Formally, let `c_scope(k)` lowercase a key and replace hyphens with underscores
in a structural mapping, and be the identity function in a literal mapping.
Canonical source additionally requires `c_scope(k) = k`. For every
pair of distinct entries `i` and `j` in an effective mapping (including merge
contributions), well-formedness requires
`c_scope(key_i) != c_scope(key_j)`. This injectivity condition is checked over
the authored node graph; mapped values do not participate in the comparison or
its diagnostics.

## 6. Identifier rules for user-defined keys

A user-defined key in a map-valued section is the **identifier** by which an
element is referenced from elsewhere ([references.md](references.md)). The
following rules govern identifiers:

1. **Preservation.** A map key is preserved verbatim as the element identifier;
   it is not lowercased, trimmed, or otherwise rewritten.
2. **Uniqueness.** An identifier **MUST** be unique within its collection. Map
   semantics make duplicate keys within one section ill-formed; runtime-family
   `<noun>_id` values **MUST** likewise be unique within their collection
   ([runtime-inventory.md](runtime-inventory.md)).
3. **No placeholders in defining keys.** An identifier-defining key **MUST NOT**
   be a variable placeholder. Variables parameterise *values*, never the
   identity of an element. (`${x}: …` as a section entry is invalid.)
4. **Node identifiers** **MUST** be at most 35 characters. A node identifier
   **MAY** contain `.` — dotted node identifiers such as `wazuh.manager` are
   used to name service families — and reference resolution accounts for dotted
   node names ([references.md](references.md)).
5. **Workflow step identifiers** **MUST NOT** contain `.`, because `.` is the
   path separator used to address a step from an objective window
   (`<workflow>.<step>`).
6. **Runtime `<noun>_id` values** are stable, symbol-shaped handles: they
   identify an element across references and **MUST NOT** carry whitespace or
   quoting that would make them unaddressable in a qualified path.

Beyond these rules, identifier *spelling* is the author's choice; the language
does not impose a global identifier grammar on ordinary section keys.

## 7. Document phases and schema boundary

An SDL document passes through up to four forms. Each form is a derived shape
of the authored document with progressively fewer unresolved constructs:

1. **Source.** The YAML presentation governed by `sdl-yaml/v1`. Presentation
   details, anchors, aliases, and migration spellings exist only at this phase.
2. **Normalised authoring object.** The source is safely constructed, canonical
   fields are recognized, documented shorthands are expanded, enum/scalar
   fields are typed, and structural closure is enforced. It **MAY** contain
   imports and `${…}` placeholders. The published
   `sdl-authoring-input-v1.json` schema validates this JSON-compatible object,
   not raw YAML bytes or presentation syntax. Its title and
   `x-aces-document-phase` annotation identify this boundary. Canonical shipped
   examples deliberately use longhand normalized values so their strict decoded
   object also validates directly against the schema.
3. **Expanded authoring object.** If the document declares imports, module
   composition is applied **before** full semantic validation, producing an
   expanded authoring object in which imported content has been merged under
   its namespace
   ([ADR-053](../../docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md)).
   Full semantic validation
   ([references.md](references.md), [diagnostics.md](diagnostics.md)) applies to
   this expanded object, treating unresolved placeholders per §5.6.
4. **Instantiated scenario.** Instantiation resolves variables against supplied
   parameters and defaults, producing a concrete document with no surviving
   variable definitions or unresolved placeholders
   ([variables-and-instantiation.md](variables-and-instantiation.md)).

The source → normalized → expanded → instantiated progression refines the two-phase
authoring/instantiation model of
[ADR-001](../../docs/decisions/adrs/adr-001-scenario-description-language.md) and
the runtime-layering boundary of
[ADR-004](../../docs/decisions/adrs/adr-004-sdl-runtime-layer.md) and
[ADR-036](../../docs/decisions/adrs/adr-036-sdl-processor-runtime-module-boundaries.md):
delivery-level realisation is downstream of, and out of scope for, the authoring
model.

## 8. Canonical semantic identity

The canonicalization profile `aces-sdl-semantic/v1` identifies one semantically
validated, expanded authoring scenario independently of YAML layout, map order,
recognized migration spelling, and documented shorthand spelling. It does not
identify raw source, an instantiated scenario, a compiled runtime model, a
module bundle, evidence, or a run.

The canonical input is the following JSON object:

```json
{
  "profile": "aces-sdl-semantic/v1",
  "scenario": {},
  "module_variable_specs": {},
  "module_node_variable_refs": {}
}
```

`scenario` is the validated expanded authoring object serialized with canonical
wire field names while omitting fields that were not authored or introduced by
normalization/composition. The two module maps are the variable specifications
and node-variable references retained as provenance side channels when imported
module variables no longer appear in the merged scenario object. Array order
is significant; object member order is not. Authored omission is significant,
so an omitted optional field and an explicitly authored default are distinct.

The envelope **MUST** satisfy the I-JSON input constraints and be serialized
with the JSON Canonicalization Scheme (JCS), RFC 8785. JCS preserves Unicode
code points without normalization, sorts object properties by UTF-16 code
units, preserves array order, emits UTF-8, and rejects non-finite or out-of-domain
numbers. The profile digest is SHA-256 over those bytes and is rendered
`sha256:<64 lower-case hexadecimal digits>`. A change to the envelope,
presence rule, or canonicalization algorithm requires a new profile identifier.
