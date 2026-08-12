"""Policy tests for the exact-SHA release verification graph (#1125, GOV-928)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"
CANONICAL_PATH = WORKFLOWS / "canonical-verification.yml"
CI_PATH = WORKFLOWS / "ci.yml"
RELEASE_PATH = WORKFLOWS / "release-please.yml"
RELEASE_CONFIG_PATH = REPO_ROOT / "release-please-config.json"
DOCKER_INTEGRATION_PATH = (
    REPO_ROOT / "implementations" / "python" / "tests" / "test_reference_backend_docker_integration.py"
)

LOCAL_CANONICAL_WORKFLOW = "./.github/workflows/canonical-verification.yml"
FULL_SHA_USE = re.compile(r"^[^@]+@[0-9a-f]{40}$")


def _load(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    # PyYAML follows YAML 1.1 and treats the top-level GitHub key ``on`` as the
    # boolean True. Normalize only that known key after using the safe loader.
    if True in payload and "on" not in payload:
        payload["on"] = payload.pop(True)
    return payload


def _named_step(job: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [step for step in job["steps"] if step.get("name") == name]
    assert len(matches) == 1, f"expected one step named {name!r}, found {len(matches)}"
    return matches[0]


def _uses(workflow: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for job in workflow["jobs"].values():
        if "uses" in job:
            refs.append(job["uses"])
        refs.extend(step["uses"] for step in job.get("steps", []) if "uses" in step)
    return refs


def _run_pypi_identity_revalidation(
    tmp_path: Path,
    *,
    release_json: str,
    ref_json: str,
    tag_json: str = "",
) -> subprocess.CompletedProcess[str]:
    if shutil.which("bash") is None or shutil.which("jq") is None:
        pytest.skip("the release identity shell policy requires bash and jq")
    script = _named_step(
        _load(RELEASE_PATH)["jobs"]["publish-pypi"],
        "Revalidate release identity immediately before PyPI",
    )["run"]
    gh_stub = tmp_path / "gh"
    gh_stub.write_text(
        """#!/bin/sh
set -eu
case "$1" in
  release)
    printf '%s\n' "$RELEASE_JSON"
    ;;
  api)
    case "$*" in
      */git/ref/tags/*) printf '%s\n' "$REF_JSON" ;;
      */git/tags/*) printf '%s\n' "$TAG_JSON" ;;
      *) echo "unexpected gh api request: $*" >&2; exit 64 ;;
    esac
    ;;
  *) echo "unexpected gh request: $*" >&2; exit 64 ;;
esac
""",
        encoding="utf-8",
    )
    gh_stub.chmod(0o700)
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "GH_TOKEN": "test-token",
        "GITHUB_REPOSITORY": "OpenRAE/rae",
        "EXPECTED_SHA": "a" * 40,
        "EXPECTED_TAG": "v3.4.5",
        "EXPECTED_RELEASE_ID": "1234",
        "EXPECTED_DRAFT": "true",
        "RELEASE_JSON": release_json,
        "REF_JSON": ref_json,
        "TAG_JSON": tag_json,
    }
    return subprocess.run(
        ["bash", "-c", script],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_canonical_verifier_requires_and_checks_out_an_exact_commit_sha() -> None:
    workflow = _load(CANONICAL_PATH)
    inputs = workflow["on"]["workflow_call"]["inputs"]
    assert inputs["ref"]["required"] is True
    assert inputs["ref"]["type"] == "string"
    assert workflow["permissions"] == {"contents": "read"}

    job = workflow["jobs"]["verify"]
    checkout = job["steps"][0]
    assert checkout["with"]["fetch-depth"] == 0
    assert checkout["with"]["ref"] == "${{ inputs.ref }}"

    binding = _named_step(job, "Bind verification to the exact commit and resolve policy base")
    script = binding["run"]
    assert "^[0-9a-f]{40}$" in script
    assert 'actual_sha="$(git rev-parse HEAD)"' in script
    assert '"${actual_sha}" != "${EXPECTED_SHA}"' in script
    assert 'git cat-file -e "${base_sha}^{commit}"' in script
    assert 'git rev-parse "${EXPECTED_SHA}^"' in script


def test_canonical_verifier_preserves_proof_install_and_full_verify_graph() -> None:
    workflow = _load(CANONICAL_PATH)
    assert set(workflow["jobs"]) == {"verify"}
    job = workflow["jobs"]["verify"]
    assert job["runs-on"] == "ubuntu-22.04"

    step_names = [step.get("name") for step in job["steps"]]
    assert "Restore pinned Isabelle archive" in step_names
    assert "Install proof sandbox" in step_names
    assert "Acquire pinned Isabelle distribution" in step_names
    assert "Resolve requirement UID from branch" in step_names

    acquire = _named_step(job, "Acquire pinned Isabelle distribution")
    assert "tools.isabelle_tool acquire" in acquire["run"]
    verify = _named_step(job, "Run canonical verification graph")
    assert "nox -f noxfile.py -s verify" in verify["run"]
    assert "--skip-requirement" in verify["run"]

    coverage = _named_step(job, "Upload coverage report")
    assert coverage["if"] == "always()"
    assert coverage["with"]["path"] == "implementations/python/coverage.xml"


def test_ci_uses_the_same_canonical_verifier_for_github_sha() -> None:
    workflow = _load(CI_PATH)
    assert workflow["permissions"] == {"contents": "read", "pull-requests": "write"}
    assert "interpreters" not in workflow["jobs"]
    assert "continue-on-error" not in workflow["jobs"]["supply-chain"]
    canonical = workflow["jobs"]["canonical"]
    assert canonical["uses"] == LOCAL_CANONICAL_WORKFLOW
    assert canonical["with"]["ref"] == "${{ github.sha }}"
    assert "github.event.pull_request.base.sha" in canonical["with"]["base-rev"]
    assert canonical["with"]["requirement-branch"] == "${{ github.head_ref || github.ref_name }}"

    # dev/main branch protection requires the existing `verify` check context.
    verify = workflow["jobs"]["verify"]
    assert verify["needs"] == "canonical"
    assert verify["if"] == "always()"
    result_join = _named_step(verify, "Preserve the required canonical verification status")
    assert result_join["env"]["CANONICAL_RESULT"] == "${{ needs.canonical.result }}"
    assert '"${CANONICAL_RESULT}" != "success"' in result_join["run"]
    assert "verify" in workflow["jobs"]["sonar"]["needs"]


def test_release_resolves_and_verifies_one_immutable_release_commit() -> None:
    workflow = _load(RELEASE_PATH)
    jobs = workflow["jobs"]
    release_config = _load(RELEASE_CONFIG_PATH)
    assert release_config["draft"] is True
    assert release_config["force-tag-creation"] is True
    assert jobs["release-please"]["outputs"]["sha"] == "${{ steps.rp.outputs.sha }}"

    resolve = jobs["resolve-release"]
    assert resolve["needs"] == "release-please"
    assert "github.event_name == 'push'" in resolve["if"]
    assert "needs.release-please.result == 'success'" in resolve["if"]
    assert "needs.release-please.outputs.release_created == 'true'" in resolve["if"]
    assert resolve["permissions"] == {"contents": "read"}
    resolution = _named_step(resolve, "Resolve and bind the immutable release commit")["run"]
    assert 'expected_sha="${RELEASE_PLEASE_SHA}"' in resolution
    assert 'tag_sha="$(git rev-parse --verify "${tag}^{commit}")"' in resolution
    assert '"${tag_sha}" != "${expected_sha}"' in resolution
    assert 'git merge-base --is-ancestor "${tag_sha}" origin/main' in resolution
    assert '"${release_is_draft}" != "true"' in resolution
    assert "release_sha=${tag_sha}" in resolution
    assert "release_id=${release_id}" in resolution
    assert "release_is_draft=${release_is_draft}" in resolution

    verify = jobs["verify-release"]
    assert verify["needs"] == "resolve-release"
    assert verify["uses"] == LOCAL_CANONICAL_WORKFLOW
    assert verify["with"]["ref"] == "${{ needs.resolve-release.outputs.release_sha }}"
    assert verify["with"]["base-rev"] == "${{ needs.resolve-release.outputs.base_sha }}"


def test_release_builds_and_smokes_the_verified_sha_before_publish() -> None:
    workflow = _load(RELEASE_PATH)
    jobs = workflow["jobs"]
    build = jobs["build-release"]
    assert set(build["needs"]) == {"resolve-release", "verify-release", "integration-docker-release"}
    assert "needs.verify-release.result == 'success'" in build["if"]
    assert "needs.integration-docker-release.result == 'success'" in build["if"]
    assert build["permissions"] == {"contents": "read"}

    checkout = build["steps"][0]
    assert checkout["with"]["ref"] == "${{ needs.resolve-release.outputs.release_sha }}"
    binding = _named_step(build, "Reconfirm the exact verified release checkout")["run"]
    assert 'actual_sha="$(git rev-parse HEAD)"' in binding
    assert '"${actual_sha}" != "${EXPECTED_SHA}"' in binding

    names = [step.get("name") for step in build["steps"]]
    corpus_index = names.index("Verify the contract corpus is bundled in both distributions (#537)")
    wheel_smoke_index = names.index("Smoke-test the installed release wheel (#537)")
    sdist_smoke_index = names.index("Smoke-test the installed release sdist (#537)")
    upload_index = names.index("Upload the tested release distributions")
    assert corpus_index < wheel_smoke_index < sdist_smoke_index < upload_index

    corpus = build["steps"][corpus_index]["run"]
    assert "tarfile.open(sdists[0]" in corpus
    assert "sdist is missing corpus payload" in corpus

    for smoke_index, distribution in ((wheel_smoke_index, "wheel"), (sdist_smoke_index, "sdist")):
        smoke = build["steps"][smoke_index]["run"]
        assert "uv pip install" in smoke
        assert "env -u PYTHONPATH -u PYTHONHOME" in smoke
        assert "conformance backend --profile provisioning-only" in smoke
        assert 'installed_version = version("raes")' in smoke
        assert 'installed_version != os.environ["EXPECTED_VERSION"]' in smoke
        assert 'report.get("passed") is not True' in smoke
        assert 'not report.get("cases")' in smoke
        assert f"installed release {distribution}" in smoke


def test_release_requires_skip_free_real_docker_tests_at_the_exact_sha() -> None:
    release = _load(RELEASE_PATH)
    docker = release["jobs"]["integration-docker-release"]
    assert set(docker["needs"]) == {"resolve-release", "verify-release"}
    assert "needs.verify-release.result == 'success'" in docker["if"]
    assert docker["permissions"] == {"contents": "read"}
    assert "continue-on-error" not in docker

    checkout = docker["steps"][0]
    assert checkout["with"]["ref"] == "${{ needs.resolve-release.outputs.release_sha }}"
    binding = _named_step(docker, "Bind real-container testing to the exact release commit")["run"]
    assert 'actual_sha="$(git rev-parse HEAD)"' in binding
    assert '"${actual_sha}" != "${EXPECTED_SHA}"' in binding

    required = _named_step(docker, "Require real-container release integration")
    assert required["env"]["RAES_DOCKER_INTEGRATION_REQUIRED"] == "1"
    required_script = required["run"]
    assert "-s integration_docker -- --junitxml=" in required_script
    assert "if not cases:" in required_script
    assert "if skipped:" in required_script
    assert "collected zero tests" in required_script
    assert "skipped tests" in required_script

    fixture = DOCKER_INTEGRATION_PATH.read_text(encoding="utf-8")
    assert "RAES_DOCKER_INTEGRATION_REQUIRED" in fixture
    assert "pytest.fail" in fixture
    assert "sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc" in fixture

    optional = _load(CI_PATH)["jobs"]["integration-docker"]
    assert optional["continue-on-error"] is True
    assert "RAES_DOCKER_INTEGRATION_REQUIRED" not in str(optional)


def test_publication_is_split_retry_safe_and_finalizes_the_same_release() -> None:
    workflow = _load(RELEASE_PATH)
    jobs = workflow["jobs"]
    publish_pypi = jobs["publish-pypi"]
    assert set(publish_pypi["needs"]) == {
        "resolve-release",
        "verify-release",
        "integration-docker-release",
        "build-release",
    }
    assert "needs.verify-release.result == 'success'" in publish_pypi["if"]
    assert "needs.integration-docker-release.result == 'success'" in publish_pypi["if"]
    assert "needs.build-release.result == 'success'" in publish_pypi["if"]
    assert publish_pypi["environment"] == "pypi"
    assert publish_pypi["permissions"] == {"contents": "read", "id-token": "write"}

    for name, job in jobs.items():
        if name == "publish-pypi":
            continue
        assert job.get("environment") != "pypi"
        assert job.get("permissions", {}).get("id-token") != "write"

    upload = _named_step(jobs["build-release"], "Upload the tested release distributions")
    pypi_download = _named_step(publish_pypi, "Download the tested release distributions")
    assert upload["with"]["name"] == pypi_download["with"]["name"]
    assert pypi_download["with"]["path"] == "dist/"
    pypi_names = [step.get("name") for step in publish_pypi["steps"]]
    revalidate_index = pypi_names.index("Revalidate release identity immediately before PyPI")
    publish_index = pypi_names.index("Publish to PyPI (OIDC trusted publishing)")
    assert revalidate_index + 1 == publish_index
    assert all(not step.get("uses", "").startswith("actions/checkout@") for step in publish_pypi["steps"])
    revalidation = publish_pypi["steps"][revalidate_index]
    assert revalidation["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "EXPECTED_SHA": "${{ needs.resolve-release.outputs.release_sha }}",
        "EXPECTED_TAG": "${{ needs.resolve-release.outputs.tag }}",
        "EXPECTED_RELEASE_ID": "${{ needs.resolve-release.outputs.release_id }}",
        "EXPECTED_DRAFT": "${{ needs.resolve-release.outputs.release_is_draft }}",
    }
    revalidation_script = revalidation["run"]
    assert 'gh release view "${EXPECTED_TAG}"' in revalidation_script
    assert '"${current_release_id}" != "${EXPECTED_RELEASE_ID}"' in revalidation_script
    assert '"${current_draft}" != "${EXPECTED_DRAFT}"' in revalidation_script
    assert '"${current_ref}" != "refs/tags/${EXPECTED_TAG}"' in revalidation_script
    assert 'while [ "${current_type}" = "tag" ]' in revalidation_script
    assert '"${current_sha}" != "${EXPECTED_SHA}"' in revalidation_script

    publish_github = jobs["publish-github"]
    assert set(publish_github["needs"]) == {
        "resolve-release",
        "verify-release",
        "build-release",
        "publish-pypi",
    }
    assert "needs.publish-pypi.result == 'success'" in publish_github["if"]
    assert publish_github["permissions"] == {"contents": "write"}
    github_download = _named_step(publish_github, "Download the tested release distributions")
    assert github_download["with"]["name"] == upload["with"]["name"]
    finalization = _named_step(publish_github, "Revalidate, attach, and publish the GitHub Release")["run"]
    assert '"${current_release_id}" != "${EXPECTED_RELEASE_ID}"' in finalization
    assert '"${current_tag_sha}" != "${EXPECTED_SHA}"' in finalization
    assert finalization.index("gh release upload") < finalization.index("gh release edit")
    assert "--draft=false --verify-tag" in finalization

    sync = jobs["sync-dev"]
    assert set(sync["needs"]) == {"release-please", "publish-github"}
    assert "needs.publish-github.result == 'success'" in sync["if"]


def test_pre_pypi_identity_revalidation_dereferences_annotated_tag(tmp_path: Path) -> None:
    result = _run_pypi_identity_revalidation(
        tmp_path,
        release_json='{"databaseId":1234,"isDraft":true,"tagName":"v3.4.5"}',
        ref_json='{"ref":"refs/tags/v3.4.5","object":{"type":"tag","sha":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}}',
        tag_json='{"object":{"type":"commit","sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}',
    )

    assert result.returncode == 0, result.stderr
    assert "Revalidated Release 1234, v3.4.5" in result.stdout


def test_pre_pypi_identity_revalidation_rejects_replaced_release(tmp_path: Path) -> None:
    result = _run_pypi_identity_revalidation(
        tmp_path,
        release_json='{"databaseId":9999,"isDraft":true,"tagName":"v3.4.5"}',
        ref_json='{"ref":"refs/tags/v3.4.5","object":{"type":"commit","sha":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}}',
    )

    assert result.returncode != 0
    assert "Release object changed: expected id 1234, got 9999" in result.stderr


def test_pre_pypi_identity_revalidation_rejects_moved_tag(tmp_path: Path) -> None:
    result = _run_pypi_identity_revalidation(
        tmp_path,
        release_json='{"databaseId":1234,"isDraft":true,"tagName":"v3.4.5"}',
        ref_json='{"ref":"refs/tags/v3.4.5","object":{"type":"commit","sha":"cccccccccccccccccccccccccccccccccccccccc"}}',
    )

    assert result.returncode != 0
    assert f"Release tag moved: expected {'a' * 40}, got {'c' * 40}" in result.stderr


def test_release_gate_does_not_poll_mutable_check_or_branch_status() -> None:
    release_text = RELEASE_PATH.read_text(encoding="utf-8").lower()
    forbidden = ("gh run list", "check-runs", "/statuses/", "workflow_run")
    assert all(token not in release_text for token in forbidden)


def test_publishing_workflows_pin_every_third_party_action_to_a_full_sha() -> None:
    for path in (CANONICAL_PATH, CI_PATH, RELEASE_PATH):
        for action_ref in _uses(_load(path)):
            if action_ref.startswith("./"):
                continue
            assert FULL_SHA_USE.fullmatch(action_ref), f"{path.name}: unpinned action {action_ref!r}"
