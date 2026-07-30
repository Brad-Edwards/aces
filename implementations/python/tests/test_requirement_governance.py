from __future__ import annotations

import shutil
import sys
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError, URLError

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_requirement_governance import governed_requirement_paths, is_dev_to_main_promotion
from tools.policy import requirement_governance
from tools.policy.requirement_governance import (
    GroundControlHttpClient,
    detect_requirement_uid,
    evaluate_requirement_governance,
    requirement_uid_from_context,
)


class FakeClient:
    def __init__(self, requirements: dict[str, dict], traceability: dict[str, list[dict]]) -> None:
        self.requirements = requirements
        self.traceability = traceability

    def get_requirement(self, project: str, uid: str) -> dict:
        return self.requirements[uid]

    def get_traceability(self, requirement_id: str) -> list[dict]:
        return self.traceability.get(requirement_id, [])


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def setup_policy_repo(tmp_path: Path) -> Path:
    policy_dir = tmp_path / "tools" / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REPO_ROOT / "tools" / "policy" / "requirement_order.yaml", policy_dir / "requirement_order.yaml")
    return tmp_path


def make_client(*, requirement_status: str = "DRAFT", api_412_status: str = "DRAFT") -> FakeClient:
    requirements = {
        "GOV-918": {"id": "req-gov-918", "uid": "GOV-918", "status": requirement_status},
        "API-412": {"id": "req-api-412", "uid": "API-412", "status": api_412_status},
        "RUN-300": {"id": "req-run-300", "uid": "RUN-300", "status": "ACTIVE"},
        "RUN-311": {"id": "req-run-311", "uid": "RUN-311", "status": "ACTIVE"},
        "RUN-313": {"id": "req-run-313", "uid": "RUN-313", "status": "DRAFT"},
        "EXP-701": {"id": "req-exp-701", "uid": "EXP-701", "status": "ACTIVE"},
        "GOV-917": {"id": "req-gov-917", "uid": "GOV-917", "status": "ACTIVE"},
        "GOV-919": {"id": "req-gov-919", "uid": "GOV-919", "status": "ACTIVE"},
        "GOV-920": {"id": "req-gov-920", "uid": "GOV-920", "status": "ACTIVE"},
        "GOV-921": {"id": "req-gov-921", "uid": "GOV-921", "status": "ACTIVE"},
        "GOV-922": {"id": "req-gov-922", "uid": "GOV-922", "status": "ACTIVE"},
    }
    traceability = {
        "req-gov-918": [
            {
                "artifact_identifier": "implementations/python/packages/raes_processor/bindings.py",
                "artifact_type": "CODE_FILE",
                "link_type": "IMPLEMENTS",
            },
            {
                "artifact_identifier": "implementations/python/tests/test_concept_authority.py",
                "artifact_type": "TEST",
                "link_type": "TESTS",
            },
        ],
        "req-api-412": [
            {
                "artifact_identifier": "implementations/python/packages/raes_processor/manifest.py",
                "artifact_type": "CODE_FILE",
                "link_type": "IMPLEMENTS",
            }
        ],
        "req-run-313": [],
        "req-exp-701": [
            {
                "artifact_identifier": "implementations/python/packages/raes_contracts/contracts.py",
                "artifact_type": "CODE_FILE",
                "link_type": "IMPLEMENTS",
            },
            {
                "artifact_identifier": "implementations/python/tests/test_runtime_contracts.py",
                "artifact_type": "TEST",
                "link_type": "TESTS",
            },
        ],
    }
    return FakeClient(requirements=requirements, traceability=traceability)


def test_detect_requirement_uid_from_branch_name() -> None:
    assert detect_requirement_uid("feature/GOV-918-cross-artifact-binding") == "GOV-918"
    assert detect_requirement_uid("15-gov-918-cross-artifact-concept-binding") == "GOV-918"
    assert detect_requirement_uid("feature/no-uid-here") is None


def test_ground_control_http_client_bounds_external_requests(monkeypatch) -> None:
    observed: dict[str, float] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self) -> bytes:
            return b'{"status":"ACTIVE"}'

    def fake_urlopen(request, *, timeout: float):
        observed["timeout"] = timeout
        return Response()

    monkeypatch.setattr(requirement_governance, "urlopen", fake_urlopen)

    client = GroundControlHttpClient("http://ground-control.invalid")

    assert client.get_requirement("project", "ASR-535") == {"status": "ACTIVE"}
    assert observed["timeout"] == 5.0


@pytest.mark.parametrize(
    ("error", "message"),
    (
        (HTTPError("http://ground-control.invalid", 503, "unavailable", None, BytesIO(b"offline")), "503: offline"),
        (URLError("connection refused"), "connection refused"),
        (TimeoutError(), "request timed out"),
    ),
)
def test_ground_control_http_client_maps_transport_failures_to_runtime_error(
    monkeypatch,
    error: Exception,
    message: str,
) -> None:
    def failing_urlopen(_request, *, timeout: float):
        assert timeout == 5.0
        raise error

    monkeypatch.setattr(requirement_governance, "urlopen", failing_urlopen)

    with pytest.raises(RuntimeError, match=message):
        GroundControlHttpClient("http://ground-control.invalid").get_requirement("project", "ASR-535")


def test_requirement_uid_context_precedence(monkeypatch) -> None:
    monkeypatch.setenv("RAES_REQUIREMENT_UID", "API-412")

    assert requirement_uid_from_context("feature/GOV-918-work", "ASR-535") == "ASR-535"
    assert requirement_uid_from_context("feature/GOV-918-work", None) == "API-412"

    monkeypatch.delenv("RAES_REQUIREMENT_UID")
    assert requirement_uid_from_context("feature/GOV-918-work", None) == "GOV-918"


def test_governed_requirement_paths_excludes_exempt_tooling_files() -> None:
    assert governed_requirement_paths(
        [
            "implementations/python/packages/raes_processor/manifest.py",
            "implementations/python/tests/test_repo_policy_tools.py",
            ".pre-commit-config.yaml",
            "tools/check_json_artifacts.py",
        ]
    ) == ["implementations/python/packages/raes_processor/manifest.py"]


def test_dev_to_main_promotion_is_detected(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_HEAD_REF", "dev")
    monkeypatch.setenv("GITHUB_BASE_REF", "main")

    assert is_dev_to_main_promotion()


def test_dev_to_non_main_is_not_a_promotion(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_HEAD_REF", "dev")
    monkeypatch.setenv("GITHUB_BASE_REF", "release")

    assert not is_dev_to_main_promotion()


def test_archived_requirements_are_rejected(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client(requirement_status="ARCHIVED")

    failures = evaluate_requirement_governance(
        repo_root,
        ["implementations/python/packages/raes_processor/bindings.py"],
        client=client,
        requirement_uid="GOV-918",
    )

    assert [failure.rule_id for failure in failures] == ["requirement-invalid-status"]


def test_blocked_phase_requires_previous_phase_completion(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client(api_412_status="DRAFT")
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes_processor" / "manifest.py",
        "VALUE = 1\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        ["implementations/python/packages/raes_processor/manifest.py"],
        client=client,
        requirement_uid="API-412",
    )

    assert [failure.rule_id for failure in failures] == ["requirement-order-blocked"]


def test_manual_release_phase_blocks_without_status_lookup(tmp_path: Path, monkeypatch) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    canonical_project = requirement_governance.load_policy(repo_root)["project"]
    policy = {
        "project": canonical_project,
        "phases": [
            {"id": "manual-gate", "manual_release": True},
            {
                "id": "governed",
                "requirements": ["GOV-918"],
                "blocked_until": ["manual-gate"],
            },
        ],
        "ownership": {},
        "traceability": {
            "required_code_roots": [],
            "required_test_roots": [],
        },
    }
    monkeypatch.setattr(requirement_governance, "load_policy", lambda _repo_root: policy)

    failures = evaluate_requirement_governance(
        repo_root,
        [],
        client=client,
        requirement_uid="GOV-918",
    )

    assert [failure.rule_id for failure in failures] == ["requirement-order-blocked"]
    assert "explicitly released" in failures[0].message


def test_unmapped_requirement_is_rejected(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    client.requirements["ASR-999"] = {"id": "req-asr-999", "uid": "ASR-999", "status": "ACTIVE"}

    failures = evaluate_requirement_governance(
        repo_root,
        [],
        client=client,
        requirement_uid="ASR-999",
    )

    assert [failure.rule_id for failure in failures] == ["requirement-policy-missing"]


def test_ownership_mismatch_is_reported(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes" / "parser.py",
        "VALUE = 1\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        ["implementations/python/packages/raes/parser.py"],
        client=client,
        requirement_uid="GOV-918",
    )

    assert {failure.rule_id for failure in failures} == {
        "requirement-ownership-mismatch",
        "traceability-missing-implements",
    }


def test_missing_traceability_links_are_reported(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes_processor" / "new_binding.py",
        "VALUE = 1\n",
    )
    write_text(
        repo_root / "implementations" / "python" / "tests" / "test_new_binding.py",
        "def test_value():\n    assert True\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        [
            "implementations/python/packages/raes_processor/new_binding.py",
            "implementations/python/tests/test_new_binding.py",
        ],
        client=client,
        requirement_uid="RUN-313",
    )

    assert {failure.rule_id for failure in failures} == {
        "traceability-missing-implements",
        "traceability-missing-tests",
    }


def test_requirement_governance_passes_for_allowed_paths_and_traceability(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes_processor" / "bindings.py",
        "VALUE = 1\n",
    )
    write_text(
        repo_root / "implementations" / "python" / "tests" / "test_concept_authority.py",
        "def test_value():\n    assert True\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        [
            "implementations/python/packages/raes_processor/bindings.py",
            "implementations/python/tests/test_concept_authority.py",
        ],
        client=client,
        requirement_uid="GOV-918",
    )

    assert failures == []


def test_experiment_core_requirement_maps_allowed_contract_paths(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    client = make_client()
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes_contracts" / "contracts.py",
        "VALUE = 1\n",
    )
    write_text(
        repo_root / "implementations" / "python" / "tests" / "test_runtime_contracts.py",
        "def test_value():\n    assert True\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        [
            "contracts/schema-publication-manifest.json",
            "contracts/schemas/backend-manifest/backend-manifest-v2.json",
            "contracts/schemas/experiment-core/experiment-task-v1.json",
            "docs/research/experiment-core/traceability-matrix-exp-701-705.md",
            "implementations/python/packages/raes_contracts/contracts.py",
            "implementations/python/tests/test_runtime_contracts.py",
            "specs/formal/experiment-core/README.md",
        ],
        client=client,
        requirement_uid="EXP-701",
    )

    assert failures == []


def test_requirement_governance_accepts_camel_case_traceability_payload(tmp_path: Path) -> None:
    repo_root = setup_policy_repo(tmp_path)
    requirements = {
        "GOV-918": {"id": "req-gov-918", "uid": "GOV-918", "status": "ACTIVE"},
    }
    client = FakeClient(
        requirements=requirements,
        traceability={
            "req-gov-918": [
                {
                    "artifactIdentifier": "implementations/python/packages/raes_contracts/contracts.py",
                    "artifactType": "CODE_FILE",
                    "linkType": "IMPLEMENTS",
                },
                {
                    "artifactIdentifier": "implementations/python/tests/test_requirement_governance.py",
                    "artifactType": "TEST",
                    "linkType": "TESTS",
                },
            ]
        },
    )
    write_text(
        repo_root / "implementations" / "python" / "packages" / "raes_contracts" / "contracts.py",
        "VALUE = 1\n",
    )
    write_text(
        repo_root / "implementations" / "python" / "tests" / "test_requirement_governance.py",
        "def test_value():\n    assert True\n",
    )

    failures = evaluate_requirement_governance(
        repo_root,
        [
            "implementations/python/packages/raes_contracts/contracts.py",
            "implementations/python/tests/test_requirement_governance.py",
        ],
        client=client,
        requirement_uid="GOV-918",
    )

    assert failures == []
