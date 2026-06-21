from __future__ import annotations

from aces_sdl.agent_guidance import agent_guidance


def test_agent_guidance_exposes_required_categories() -> None:
    payload = agent_guidance()

    assert payload["status"] == "ok"
    assert payload["profile"] == "aces-agent-guidance"
    assert "AUT-811" in payload["requirement_refs"]
    assert set(payload["guidance"]) == {
        "scope_boundaries",
        "invariants",
        "review_priorities",
        "safe_operating_expectations",
    }


def test_agent_guidance_filters_operator_entries() -> None:
    payload = agent_guidance(audience="operator")

    assert payload["status"] == "ok"
    assert payload["audience"] == "operator"
    for entries in payload["guidance"].values():
        assert entries
        assert all("operator" in entry["audience"] for entry in entries)


def test_agent_guidance_rejects_unknown_audience() -> None:
    payload = agent_guidance(audience="auditor")

    assert payload["status"] == "invalid"
    assert payload["diagnostics"][0]["code"] == "agent_guidance.audience"
