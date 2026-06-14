package main

import rego.v1


test_legacy_root_is_blocked if {
  failures := deny with input as {
    "changed": ["schemas/backend-manifest.json"],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": ["schemas"],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": [],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 1
  some failure in failures
  failure.rule_id == "legacy-top-level-root"
}


test_schema_edit_requires_manifest_update if {
  failures := deny with input as {
    "changed": ["contracts/schemas/backend-manifest/backend-manifest-v2.json"],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {
        "generated_roots": ["contracts/schemas"],
        "manifest_path": "contracts/schema-publication-manifest.json",
      },
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": [],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 1
  some failure in failures
  failure.rule_id == "schema-change-missing-manifest"
}


test_schema_edit_passes_with_manifest_update if {
  failures := deny with input as {
    "changed": [
      "contracts/schemas/backend-manifest/backend-manifest-v2.json",
      "contracts/schema-publication-manifest.json",
    ],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {
        "generated_roots": ["contracts/schemas"],
        "manifest_path": "contracts/schema-publication-manifest.json",
      },
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": [],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 0
}


test_schema_readme_edit_does_not_require_manifest if {
  failures := deny with input as {
    "changed": ["contracts/schemas/README.md"],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {
        "generated_roots": ["contracts/schemas"],
        "manifest_path": "contracts/schema-publication-manifest.json",
      },
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": [],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 0
}


test_reserved_concept_authority_paths_are_enforced if {
  failures := deny with input as {
    "changed": ["docs/drafts/concept-authority-notes.md"],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {
        "reserved_path_tokens": ["concept-authority"],
        "allowed_paths": ["docs/explain/reference/shared-concept-model.md"],
      },
      "source_roots": [],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 1
  some failure in failures
  failure.rule_id == "concept-authority-reserved-path"
}


test_changelog_is_required_for_source_changes if {
  failures := deny with input as {
    "changed": ["implementations/python/packages/aces_processor/runtime.py"],
    "check_set": "full",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": ["implementations/python/packages"],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 1
  some failure in failures
  failure.rule_id == "changelog-required"
}


test_changelog_fragment_satisfies_source_changes if {
  failures := deny with input as {
    "changed": [
      "implementations/python/packages/aces_processor/runtime.py",
      "changelog.d/132.added.md",
    ],
    "check_set": "full",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": ["implementations/python/packages"],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 0
}


test_changelog_readme_does_not_satisfy_source_changes if {
  failures := deny with input as {
    "changed": [
      "implementations/python/packages/aces_processor/runtime.py",
      "changelog.d/README.md",
    ],
    "check_set": "full",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": ["implementations/python/packages"],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 1
  some failure in failures
  failure.rule_id == "changelog-required"
}


test_file_local_mode_skips_changelog if {
  failures := deny with input as {
    "changed": ["implementations/python/packages/aces_processor/runtime.py"],
    "check_set": "file-local",
    "policy": {
      "legacy_top_level_roots": [],
      "generated_contracts": {"generated_roots": []},
      "concept_authority": {"reserved_path_tokens": [], "allowed_paths": []},
      "source_roots": ["implementations/python/packages"],
      "changelog_path": "CHANGELOG.md",
      "changelog_fragment_dir": "changelog.d",
    },
  }
  count(failures) == 0
}
