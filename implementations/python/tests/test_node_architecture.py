"""Issue #674: target-node CPU architecture semantics.

Layer 1 — governed vocabulary, ``Node.architecture`` field, package-artifact
architecture normalization. Compatibility (semantic-validator) coverage lives in
``test_node_architecture_compat`` classes further below once the validator pass
is wired.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from raes.architectures import (
    NodeArchitecture,
    architectures_compatible,
    normalize_architecture,
)
from raes.nodes import Node
from raes.runtime_configuration import RuntimePackage


class TestNodeArchitectureVocabulary:
    def test_canonical_values(self):
        assert NodeArchitecture.X86_64.value == "x86_64"
        assert NodeArchitecture.AARCH64.value == "aarch64"

    @pytest.mark.parametrize(
        ("raw", "canonical"),
        [
            ("x86_64", NodeArchitecture.X86_64),
            ("X86_64", NodeArchitecture.X86_64),
            ("amd64", NodeArchitecture.X86_64),
            ("AMD64", NodeArchitecture.X86_64),
            ("x64", NodeArchitecture.X86_64),
            ("x86-64", NodeArchitecture.X86_64),
            ("aarch64", NodeArchitecture.AARCH64),
            ("arm64", NodeArchitecture.AARCH64),
            ("ARM64", NodeArchitecture.AARCH64),
        ],
    )
    def test_aliases_normalize_to_canonical(self, raw, canonical):
        assert normalize_architecture(raw) is canonical

    def test_none_stays_none(self):
        assert normalize_architecture(None) is None

    def test_variable_reference_passthrough(self):
        assert normalize_architecture("${node_arch}") == "${node_arch}"

    def test_governed_extension_admitted_as_exact_token(self):
        assert normalize_architecture("x-nvidia:grace") == "x-nvidia:grace"
        # canonical lowercase form is produced from mixed case
        assert normalize_architecture("X-NVIDIA:GRACE") == "x-nvidia:grace"

    @pytest.mark.parametrize(
        "bad",
        [
            "x86",  # ambiguous family label (no width)
            "arm",  # ambiguous family label (no variant)
            "noarch",  # package portability classifier, not a CPU arch
            "any",
            "all",
            "other",  # no catch-all sentinel; absence expresses "no requirement"
            "unknown",
            "sparc",  # not in the governed set and not a governed extension
            "x-Bad Owner:term",  # extension must match the governed pattern
        ],
    )
    def test_unknown_values_fail_closed(self, bad):
        with pytest.raises(ValueError, match="architecture"):
            normalize_architecture(bad)

    def test_non_string_rejected(self):
        with pytest.raises(ValueError, match="architecture"):
            normalize_architecture(123)


class TestNodeArchitectureField:
    def test_vm_node_accepts_canonical(self):
        n = Node(type="vm", architecture="x86_64", resources={"ram": "1 gib", "cpu": 1})
        assert n.architecture is NodeArchitecture.X86_64

    def test_vm_node_accepts_alias(self):
        n = Node(type="vm", architecture="arm64", resources={"ram": "1 gib", "cpu": 1})
        assert n.architecture is NodeArchitecture.AARCH64

    def test_absent_architecture_is_none(self):
        n = Node(type="vm", resources={"ram": "1 gib", "cpu": 1})
        assert n.architecture is None

    def test_variable_placeholder(self):
        n = Node(type="vm", architecture="${arch}", resources={"ram": "1 gib", "cpu": 1})
        assert n.architecture == "${arch}"

    def test_unknown_architecture_rejected(self):
        with pytest.raises(ValidationError, match="architecture"):
            Node(type="vm", architecture="sparc", resources={"ram": "1 gib", "cpu": 1})

    def test_switch_node_rejects_architecture(self):
        with pytest.raises(ValidationError, match="architecture"):
            Node(type="switch", architecture="x86_64")


class TestRuntimePackageArchitecture:
    def test_empty_stays_empty(self):
        pkg = RuntimePackage(manager="apk", name="musl", version="1.2.4-r2")
        assert pkg.architecture == ""

    def test_canonical_token_normalized(self):
        pkg = RuntimePackage(manager="apk", name="musl", version="1", architecture="amd64")
        assert pkg.architecture == "x86_64"

    def test_governed_extension_token(self):
        pkg = RuntimePackage(manager="apk", name="x", version="1", architecture="x-nvidia:grace")
        assert pkg.architecture == "x-nvidia:grace"

    def test_unknown_package_architecture_rejected(self):
        with pytest.raises(ValidationError, match="architecture"):
            RuntimePackage(manager="apk", name="x", version="1", architecture="sparc")


def _scenario(node_arch: str | None, package_arch: str | None) -> str:
    lines = ["name: arch-compat", "nodes:", "  worker:", "    type: vm"]
    if node_arch is not None:
        lines.append(f"    architecture: {node_arch}")
    lines.append("    resources: {ram: 1 gib, cpu: 1}")
    if package_arch is not None:
        lines += [
            "    runtime:",
            "      packages:",
            "        - manager: apk",
            "          name: musl",
            "          version: '1'",
            f"          architecture: {package_arch}",
        ]
    return "\n".join(lines) + "\n"


class TestNodeArchitectureCompatibility:
    """Semantic-validator compatibility rules (issue #674, rules 1-4)."""

    def test_node_absent_package_empty_valid(self):
        from raes import parse_sdl

        parse_sdl(_scenario(node_arch=None, package_arch=None))

    def test_node_present_package_empty_valid(self):
        from raes import parse_sdl

        parse_sdl(_scenario(node_arch="x86_64", package_arch=None))

    def test_node_present_package_matching_valid(self):
        from raes import parse_sdl

        # aliases on either side normalize to the same canonical token
        parse_sdl(_scenario(node_arch="amd64", package_arch="x86_64"))

    def test_node_present_package_mismatch_invalid(self):
        from raes import SDLValidationError, parse_sdl

        with pytest.raises(SDLValidationError, match="architecture"):
            parse_sdl(_scenario(node_arch="x86_64", package_arch="aarch64"))

    def test_node_absent_package_present_invalid(self):
        from raes import SDLValidationError, parse_sdl

        with pytest.raises(SDLValidationError, match="architecture"):
            parse_sdl(_scenario(node_arch=None, package_arch="x86_64"))

    def test_variable_node_architecture_defers(self):
        from raes import parse_sdl

        # a variable-valued node architecture defers compatibility to binding
        parse_sdl(
            "name: arch-var\n"
            "variables:\n"
            "  arch: {type: string, default: aarch64, allowed_values: [aarch64]}\n"
            "nodes:\n"
            "  worker:\n"
            "    type: vm\n"
            "    architecture: '${arch}'\n"
            "    resources: {ram: 1 gib, cpu: 1}\n"
            "    runtime:\n"
            "      packages:\n"
            "        - {manager: apk, name: musl, version: '1', architecture: aarch64}\n"
        )


_ARCH_NODE_SCENARIO = (
    "name: arch-compile\nnodes:\n  web:\n    type: vm\n    architecture: x86_64\n    resources: {ram: 1 gib, cpu: 1}\n"
)


class TestNodeArchitectureCompilation:
    def test_node_runtime_carries_architecture(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model

        model = compile_runtime_model(parse_sdl(_ARCH_NODE_SCENARIO))
        node = next(iter(model.node_deployments.values()))
        assert node.architecture == "x86_64"

    def test_architecture_becomes_realization_requirement(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model

        model = compile_runtime_model(parse_sdl(_ARCH_NODE_SCENARIO))
        by_field = {req.field_path: req for req in model.realization_requirements}
        assert "nodes.web.architecture" in by_field
        assert by_field["nodes.web.architecture"].requirement_kind == "node-architecture"

    def test_absent_architecture_emits_no_requirement(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model

        model = compile_runtime_model(
            parse_sdl("name: no-arch\nnodes:\n  web:\n    type: vm\n    resources: {ram: 1 gib, cpu: 1}\n")
        )
        fields = {req.field_path for req in model.realization_requirements}
        assert "nodes.web.architecture" not in fields


def _architecture_manifest(supported_node_architectures: frozenset[str]):
    from raes_backend_protocols.capabilities import BackendManifest, ProvisionerCapabilities
    from raes_contracts.apparatus import ConceptBinding, RealizationSupportDeclaration
    from raes_contracts.vocabulary import RealizationSupportMode

    return BackendManifest(
        name="arch-limited",
        version="0.0.1",
        supported_contract_versions=frozenset({"backend-manifest-v2"}),
        compatible_processors=frozenset({"raes-reference-processor"}),
        realization_support=(
            RealizationSupportDeclaration(
                domain="runtime-realization",
                support_mode=RealizationSupportMode.CONSTRAINED,
                supported_constraint_kinds=frozenset({"node-type", "os-family", "node-architecture"}),
                supported_exact_requirement_kinds=frozenset({"declared-capability-match"}),
                disclosure_kinds=frozenset({"runtime-snapshot-v1"}),
            ),
        ),
        concept_bindings=(ConceptBinding(scope="capabilities.provisioner.supported_node_types", family="assets"),),
        provisioner=ProvisionerCapabilities(
            name="arch-limited-provisioner",
            supported_node_types=frozenset({"vm"}),
            supported_os_families=frozenset({"linux"}),
            supported_node_architectures=supported_node_architectures,
        ),
    )


class TestNodeArchitecturePlannerAdmission:
    def test_supported_architecture_passes(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model
        from raes_processor.planner import plan

        model = compile_runtime_model(parse_sdl(_ARCH_NODE_SCENARIO))
        execution_plan = plan(model, _architecture_manifest(frozenset({"x86_64"})))
        codes = {d.code for d in execution_plan.diagnostics}
        assert "provisioner.unsupported-node-architecture" not in codes

    def test_unsupported_architecture_fails_closed(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model
        from raes_processor.planner import plan

        model = compile_runtime_model(parse_sdl(_ARCH_NODE_SCENARIO))
        execution_plan = plan(model, _architecture_manifest(frozenset({"aarch64"})))
        codes = {d.code for d in execution_plan.diagnostics}
        assert "provisioner.unsupported-node-architecture" in codes
        assert not execution_plan.is_valid

    def test_empty_support_fails_architecture_requirement(self):
        from raes import parse_sdl
        from raes_processor.compiler import compile_runtime_model
        from raes_processor.planner import plan

        model = compile_runtime_model(parse_sdl(_ARCH_NODE_SCENARIO))
        execution_plan = plan(model, _architecture_manifest(frozenset()))
        codes = {d.code for d in execution_plan.diagnostics}
        assert "provisioner.unsupported-node-architecture" in codes


class TestNodeArchitectureSemanticDiff:
    """Semantic-comparison coverage (issue #674, criterion 5)."""

    @staticmethod
    def _digest(node_arch: str | None):
        from raes import parse_sdl
        from raes.canonical import canonical_sdl_digest

        arch_line = f"    architecture: {node_arch}\n" if node_arch is not None else ""
        return canonical_sdl_digest(
            parse_sdl(
                "name: arch-diff\nnodes:\n  web:\n    type: vm\n" + arch_line + "    resources: {ram: 1 gib, cpu: 1}\n"
            )
        )

    def test_alias_only_change_is_semantically_equal(self):
        assert self._digest("amd64") == self._digest("x86_64")

    def test_distinct_canonical_values_are_a_semantic_change(self):
        assert self._digest("x86_64") != self._digest("aarch64")

    def test_presence_versus_absence_is_a_semantic_change(self):
        assert self._digest("x86_64") != self._digest(None)


class TestNodeArchitectureSchemaGovernance:
    """The published schema encodes the governed vocabulary (issue #674, criterion 2/5).

    Regression guard: the ``Node.architecture`` schema must not carry an
    unrestricted string branch that would let a schema-only consumer bypass the
    governed CPU-architecture vocabulary.
    """

    @staticmethod
    def _node_architecture_schema():
        import jsonschema
        from raes.scenario import Scenario

        full = Scenario.model_json_schema()
        schema = full["$defs"]["Node"]["properties"]["architecture"]
        return {**schema, "$defs": full["$defs"]}, jsonschema

    def test_no_unrestricted_string_branch(self):
        schema, _ = self._node_architecture_schema()
        for branch in schema["anyOf"]:
            if branch.get("type") == "string":
                assert "pattern" in branch, "string branch must constrain to the governed vocabulary"

    @pytest.mark.parametrize("value", ["x86_64", "aarch64", "amd64", "arm64", "x-nvidia:grace", "${arch}"])
    def test_schema_accepts_governed_values(self, value):
        schema, jsonschema = self._node_architecture_schema()
        jsonschema.validate(value, schema)

    @pytest.mark.parametrize("value", ["sparc", "x86", "arm", "noarch", "anything"])
    def test_schema_rejects_ungoverned_values(self, value):
        schema, jsonschema = self._node_architecture_schema()
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(value, schema)


class TestArchitecturesCompatible:
    def test_exact_canonical_equal(self):
        assert architectures_compatible(NodeArchitecture.X86_64, "x86_64") is True

    def test_alias_and_canonical_equal(self):
        # both sides are already normalized to canonical before comparison
        assert architectures_compatible(NodeArchitecture.AARCH64, "aarch64") is True

    def test_distinct_canonical_incompatible(self):
        assert architectures_compatible(NodeArchitecture.X86_64, "aarch64") is False

    def test_extension_tokens_exact_match(self):
        assert architectures_compatible("x-nvidia:grace", "x-nvidia:grace") is True
        assert architectures_compatible("x-nvidia:grace", "x86_64") is False
