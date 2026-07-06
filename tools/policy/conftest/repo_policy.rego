package main

import rego.v1


deny contains result if {
  path := input.changed[_]
  top_level_root(path) == input.policy.legacy_top_level_roots[_]
  result := {
    "msg": "legacy top-level roots are not authoritative; place the artifact under specs/, contracts/, docs/, or implementations/",
    "rule_id": "legacy-top-level-root",
    "path": path,
  }
}


deny contains result if {
  path := input.changed[_]
  path_matches_any(path, input.policy.generated_contracts.generated_roots)
  endswith(path, ".json")
  not manifest_touched
  result := {
    "msg": "published schemas under contracts/schemas/ are hand-governed normative authority (ADR-009 section 7); a schema change must update contracts/schema-publication-manifest.json with a contract-facing change-ledger entry",
    "rule_id": "schema-change-missing-manifest",
    "path": path,
  }
}


deny contains result if {
  path := input.changed[_]
  contains_reserved_token(path)
  not path_matches_any(path, input.policy.concept_authority.allowed_paths)
  result := {
    "msg": "concept-authority artifacts must stay in the approved authority surfaces",
    "rule_id": "concept-authority-reserved-path",
    "path": path,
  }
}


manifest_touched if {
  input.policy.generated_contracts.manifest_path in input.changed
}


contains_reserved_token(path) if {
  token := input.policy.concept_authority.reserved_path_tokens[_]
  contains(path, token)
}


path_matches_any(path, prefixes) if {
  some prefix in prefixes
  path_matches_prefix(path, prefix)
}


path_matches_prefix(path, prefix) if {
  normalized_path := trim(path, "/")
  normalized_prefix := trim(prefix, "/")
  normalized_path == normalized_prefix
}


path_matches_prefix(path, prefix) if {
  normalized_path := trim(path, "/")
  normalized_prefix := trim(prefix, "/")
  startswith(normalized_path, sprintf("%s/", [normalized_prefix]))
}


top_level_root(path) := root if {
  segments := split(path, "/")
  root := segments[0]
}
