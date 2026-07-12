# SDL Lineage Source Audit - 2026-07-12

This bounded audit records the external identity and license checks used to
populate `contracts/provenance/sdl-lineage-ledger-v1.json`. It is evidence for
the ledger, not normative SDL authority and not a legal opinion. The checked-in
ledger and its offline gate preserve the reviewed results without making CI
depend on live services.

## Method

- Git sources were resolved through the public GitHub commit and contents APIs.
- Publication identity was checked against DOI registry metadata and the DOI's
  publisher destination; title, authors, year, container, and DOI were compared
  as separate fields.
- OASIS standards were checked against their canonical immutable version URLs.
- Current ACES paths were compared with the initial extracted SDL commit
  `2e73ee6ce11ef42fef10e1837ee2bb96570d030d`; explicit port statements were
  treated as derivation evidence, not inferred from similar names alone.

## Open Cyber Range SDL

- Project: Open Cyber Range SDL Parser.
- Release: v0.21.2.
- Full revision: `fe83e8281fc4b954967fbaa5a0d099007ddcb06c`.
- Revision date: 2024-12-20.
- Revision record: <https://github.com/Open-Cyber-Range/SDL-parser/commit/fe83e8281fc4b954967fbaa5a0d099007ddcb06c>.
- Source boundary: `sdl-parser/src/*.rs` at that revision, narrowed per ledger
  claim to the named Rust model file and ACES model boundary.
- License at the reviewed revision: MIT, copyright 2022 CR14,
  <https://github.com/Open-Cyber-Range/SDL-parser/blob/fe83e8281fc4b954967fbaa5a0d099007ddcb06c/LICENSE>.
- ACES derivation evidence: the initial extracted `scenario.py` identifies its
  OCR-derived top-level sections, and `nodes.py` states that it ports OCR
  `Node`/`VM`/`Switch`/`Resources`/`Role` structures. Current
  explanatory prose also used "direct port" for several OCR families. The
  audit therefore adopts the conservative disposition that the upstream MIT
  notice is required and includes it in `THIRD_PARTY_NOTICES.md`.
- Compatibility: partial syntax ancestry only. ACES does not claim drop-in
  parser, schema, validation, or runtime compatibility with OCR v0.21.2.

## CACAO v2.0

OASIS publishes *CACAO Security Playbooks Version 2.0*, Committee
Specification 01, at
<https://docs.oasis-open.org/cacao/security-playbooks/v2.0/security-playbooks-v2.0.html>.
ACES adapts selected variable and workflow-graph concerns; it does not claim to
implement the CACAO object model or wire format.

## STIX v2.1

OASIS publishes *STIX Version 2.1* at
<https://docs.oasis-open.org/cti/stix/v2.1/stix-v2.1.html>. The ACES
relationship family adapts the typed directed-edge pattern; it is not a STIX
Relationship SRO and is not STIX serialization-compatible.

## CyRIS

The verified publication used by the ledger is Razvan Beuran et al.,
*Cybersecurity Education and Training Support System: CyRIS*, IEICE
Transactions on Information and Systems (2018),
<https://doi.org/10.1587/transinf.2017EDP7207>. An earlier candidate DOI,
`10.1007/978-3-319-24018-3_18`, was rejected because it resolves to an
unrelated publication. ACES adapts the account/content placement concerns, not
CyRIS code or deployment syntax.

## CybORG

The ledger uses Standen et al., *CybORG: A Gym for the Development of
Autonomous Cyber Agents*, arXiv:2108.09118 (2021),
<https://arxiv.org/abs/2108.09118>. It supports the participant/agent concern;
the ACES agent and participant contracts are ACES-native models rather than a
copy of the CybORG API or scenario schema.

## CRACK Publications

Two related works by Russo, Costa, and Armando are distinct and must not share
one title/year label:

- *Scenario Design and Validation for Next Generation Cyber Ranges*, IEEE NCA
  2018, <https://doi.org/10.1109/NCA.2018.8548324>.
- *Building next generation Cyber Ranges with CRACK*, Computers & Security 95
  (2020), <https://doi.org/10.1016/j.cose.2020.101837>.

The first is the scenario-design/validation paper. The second is the later
CRACK system paper. Neither is a source-code derivation claim for ACES.

## Notice And Distribution Disposition

`THIRD_PARTY_NOTICES.md` reproduces the OCR MIT notice required by the
conservative derivation disposition. The source distribution includes that
file, and the wheel build maps the same source notice into the packaged
contract corpus. No separate source-code derivation claim is made for CACAO,
STIX, CyRIS, CybORG, or CRACK, so their citations do not create a copied-code
notice disposition in this audit.

## Current Documentation Link Audit

On 2026-07-12, the URLs in the current SDL lineage, precedent, and related-work
pages were checked as a bounded audit rather than a CI dependency. Four stale
targets were corrected to current primary or archival records: NIST SP 800-61
Revision 3, PettingZoo, Fidge's logical-time paper, and Adya's dissertation.
The two CRACK DOI identities were checked separately as described above.

Some official sites reject automated requests even when the cited page remains
available. Such responses were not recorded as proof that a source is dead.
The offline checker therefore validates recorded identifiers, pins, and
internal evidence, but does not claim that every external server will remain
available or answer an automated request.
