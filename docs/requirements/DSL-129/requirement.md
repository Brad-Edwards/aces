---
id: DSL-129
title: "DNS Service Runtime Inventory"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
wave: 1
created_at: 2026-05-28T05:30:22.367829Z
updated_at: 2026-05-28T05:54:05.218529Z
---

# DSL-129 — DNS Service Runtime Inventory

## Statement

The language shall represent DNS service logical and protocol runtime state as typed node-scoped runtime inventory, including authoritative zone contents, DNS resource record sets, resolver policy, DNSSEC posture, logging posture, dynamic-update policy, and evidence references, without overloading transport services, HTTP application routes, filesystem evidence, generic content, or prose-only relationships.

## Rationale

Issue 426 identifies a downstream inventory blocker: ACES can capture the surrounding container, network, filesystem, process, package, vulnerability, and content evidence, but lacks a typed, queryable surface for DNS service logical state observed from BIND/AXFR and related DNS configuration.

## Traceability

- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/validator/__init__.py` (DNS runtime semantic validation and refs)
- TESTS → TEST `implementations/python/tests/test_sdl_models.py` (DNS runtime model tests)
- TESTS → TEST `implementations/python/tests/test_sdl_validator.py` (DNS runtime validator tests)
- TESTS → TEST `implementations/python/tests/test_sdl_parser.py` (DNS runtime parser and module alias tests)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_dns.py` (DNS service runtime inventory models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_dns_records.py` (DNS RRset and RDATA runtime models)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_dns_vocab.py` (DNS runtime inventory vocabulary)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/runtime_configuration.py` (Runtime configuration DNS service collection)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/nodes.py` (Node public DNS runtime exports)
- IMPLEMENTS → CODE_FILE `implementations/python/packages/aces_sdl/_module_symbols.py` (DNS runtime module import aliases)
- IMPLEMENTS → GITHUB_ISSUE `426` (Issue 426: DNS service runtime inventory)
- IMPLEMENTS → ADR `docs/decisions/adrs/adr-039-dns-service-runtime-inventory.md` (ADR-039: DNS service runtime inventory)
