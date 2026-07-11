# SDL Document Model

This file defines how an SDL document is encoded, how its top-level surfaces are
organised, what is required, how user-defined identifiers are formed, how the
document is structurally closed, and the phases a document passes through from
authoring to instantiation.

See [`sections.md`](sections.md) for the per-section catalog,
[`references.md`](references.md) for reference resolution, and
[`variables-and-instantiation.md`](variables-and-instantiation.md) for variable
and instantiation rules.

## 1. Encoding

1. An SDL document **MUST** be a YAML 1.1/1.2 document whose top-level value is a
   mapping. A document whose root is a sequence, scalar, or null is not a valid
   SDL document.
2. Every mapping key **MUST** denote a string. In particular, SDL treats an
   implicitly typed YAML 1.1 spelling such as `on`, `off`, `yes`, or `no` as
   the authored string spelling when it occurs in key position; it does not
   allow the YAML loader to turn that spelling into a boolean map key. A
   non-scalar or explicitly non-string key is rejected.
3. A document **MUST** be loadable by a safe YAML loader. Constructor tags that
   instantiate arbitrary types **MUST NOT** be honoured.
4. Every authored mapping entry **MUST** remain distinguishable until the SDL
   parser has checked key uniqueness. An exact duplicate key at any depth is a
   parse/structural error; a loader **MUST NOT** construct a last-write-wins
   dictionary first.

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

> **Reconciliation note.** Earlier descriptions of the SDL spoke of "21 named
> sections, all dicts." That count is stale. The live authoring contract has a
> larger section set and is **not** uniformly map-keyed: `forwarding_agents` is
> list-valued, and the participant surfaces (`action_contracts`,
> `observation_boundaries`, `outcome_interpretation_rules`) are present. The
> section catalog states the live set; this specification reconciles the
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
4. YAML anchors and aliases remain authoring conveniences, but they do not
   weaken closure or uniqueness. A merge key (`<<`) is valid only when the
   effective entries contributed by every merge source and every local entry
   remain unique after the scope-appropriate key rules in §5 are applied. A
   merge conflict is a parse/structural error rather than an implicit precedence
   rule. This is a deliberate ACES restriction over the YAML 1.1 merge-key
   working draft, which otherwise defines source and local override precedence
   ([YAML 1.1 merge type](https://yaml.org/type/merge.html)). Cyclic alias
   graphs are invalid.

> *Implementation evidence (non-normative): the reference models set
> `extra="forbid"` on the shared SDL base model.*

## 5. Field and value normalisation

1. Enum-valued fields accept their value case-insensitively, and accept a hyphen
   as an alias for an underscore in the value text, so that an authoring value
   such as `search-index` and `search_index` denote the same enum member. This
   is an authoring convenience; the normalised (canonical) form is what the
   document means.
2. Structural field keys retain the authoring aliases established by ADR-001:
   matching is case-insensitive and `-` is accepted as an alias for `_`.
   Therefore `semantic-version` and `semantic_version` both address the
   canonical field `semantic_version`.
3. Field-key aliases do not create a precedence rule. If two keys in one
   effective mapping address the same canonical field, including through a YAML
   merge, the mapping is ambiguous and **MUST** fail during parsing before model
   construction. The diagnostic contract is defined in
   [diagnostics.md §6](diagnostics.md).
4. Field-key normalisation applies only while traversing a schema-defined
   structural mapping. It **MUST NOT** be applied to user-defined identifier
   maps, extension maps, or native option/label maps. Keys in those maps are
   preserved verbatim, including case, hyphens, underscores, and YAML 1.1
   boolean-like spellings; only exact duplicate identifiers are rejected.
5. A field that holds a variable placeholder (`${…}`) is **not** normalised as an
   enum value; the placeholder is preserved until instantiation
   ([variables-and-instantiation.md](variables-and-instantiation.md)).

Formally, let `c_scope(k)` lowercase a key and replace hyphens with underscores
in a structural mapping, and be the identity function in a literal mapping. For every
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

## 7. Document phases

An SDL document passes through up to three forms. Each form is a superset shape
of the authored document with progressively fewer unresolved constructs:

1. **Authored.** The document as written. It **MAY** contain module imports and
   `${…}` variable placeholders. Full semantic validation
   ([references.md](references.md), [diagnostics.md](diagnostics.md)) applies to
   the authored document, treating unresolved placeholders per §5.5.
2. **Expanded.** If the document declares a module or imports
   ([sections.md](sections.md) — `module`, `imports`), module composition is
   applied **before** full semantic validation, producing an expanded document
   in which imported content has been merged under its namespace
   ([ADR-053](../../docs/decisions/adrs/adr-053-sdl-module-composition-for-inventory-backed-scenarios.md)).
3. **Instantiated.** Instantiation resolves variables against supplied
   parameters and defaults, producing a concrete document with no surviving
   variable definitions or unresolved placeholders
   ([variables-and-instantiation.md](variables-and-instantiation.md)).

The authored → expanded → instantiated progression is the two-phase
authoring/instantiation model of
[ADR-001](../../docs/decisions/adrs/adr-001-scenario-description-language.md) and
the runtime-layering boundary of
[ADR-004](../../docs/decisions/adrs/adr-004-sdl-runtime-layer.md) and
[ADR-036](../../docs/decisions/adrs/adr-036-sdl-processor-runtime-module-boundaries.md):
delivery-level realisation is downstream of, and out of scope for, the authoring
model.
