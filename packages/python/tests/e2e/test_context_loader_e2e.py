"""E2E: context loader — MCP schema search, instance query, data verification.

Requires at least one existing knowledge network with built and indexed data.
Tests the full MCP chain: kn_search → query_object_instance → data verification.
Read-only tests (non-destructive).
"""
from __future__ import annotations

import json

import pytest

from kweaver import KWeaverClient
from kweaver.cli.main import cli
from kweaver.resources.context_loader import ContextLoaderResource

pytestmark = pytest.mark.e2e

# cli_runner fixture is defined in tests/e2e/conftest.py


@pytest.fixture(scope="module")
def cl_context(kweaver_client: KWeaverClient, e2e_env: dict):
    """Set up Context Loader with a KN that has indexed data.

    Returns dict with: kn, ot, cl (ContextLoaderResource), sample_instance.
    """
    kns = kweaver_client.knowledge_networks.list()
    for kn in kns:
        try:
            ots = kweaver_client.object_types.list(kn.id)
        except Exception:
            continue
        for ot in ots:
            if ot.status and ot.status.doc_count > 0 and ot.properties:
                # Get a real instance via REST to use as test data
                result = kweaver_client.query.instances(kn.id, ot.id, limit=1)
                if result.data and result.data[0].get("_instance_identity"):
                    # Build context loader
                    token = kweaver_client._http._auth.auth_headers().get(
                        "Authorization", ""
                    ).removeprefix("Bearer ").strip()
                    base_url = str(kweaver_client._http._client.base_url).rstrip("/")
                    cl = ContextLoaderResource(base_url, token, kn_id=kn.id)
                    return {
                        "kn": kn,
                        "ot": ot,
                        "cl": cl,
                        "sample": result.data[0],
                    }
    pytest.skip("No KN with indexed data and instance identities found")


# ── CLI baseline ────────────────────────────────────────────────────────


def test_kn_list_discovers_knowledge_networks(cli_runner):
    """CLI bkn list should return knowledge networks."""
    result = cli_runner.invoke(cli, ["bkn", "list"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    for kn in data:
        assert "id" in kn
        assert "name" in kn


def test_kn_export_returns_structure(kweaver_client: KWeaverClient, cli_runner):
    """CLI bkn export should return schema structure."""
    kns = kweaver_client.knowledge_networks.list()
    if not kns:
        pytest.skip("No knowledge networks available")
    result = cli_runner.invoke(cli, ["bkn", "export", kns[0].id])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert isinstance(data, dict)


def test_query_instances_returns_data(kweaver_client: KWeaverClient, cli_runner):
    """CLI query instances should return data rows."""
    kns = kweaver_client.knowledge_networks.list()
    if not kns:
        pytest.skip("No knowledge networks available")
    kn = None
    ot = None
    for candidate_kn in kns:
        try:
            ots = kweaver_client.object_types.list(candidate_kn.id)
        except Exception:
            continue
        if ots:
            kn = candidate_kn
            ot = ots[0]
            break
    if ot is None:
        pytest.skip("No object types available")
    result = cli_runner.invoke(cli, [
        "query", "instances", kn.id, ot.id, "--limit", "5",
    ])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "data" in data


# ── MCP: kn_search ──────────────────────────────────────────────────────


def test_mcp_kn_search_returns_schema(cl_context):
    """MCP kn_search should discover object types for the KN."""
    cl = cl_context["cl"]
    ot = cl_context["ot"]
    result = cl.kn_search(ot.name)
    assert isinstance(result, dict)
    # MCP returns text in 'raw' field containing object_types listing
    raw = result.get("raw", "")
    assert "object_types" in raw, f"kn_search did not return object_types in: {raw[:200]}"


def test_mcp_kn_search_only_schema(cl_context):
    """MCP kn_search with only_schema should still return schema."""
    cl = cl_context["cl"]
    ot = cl_context["ot"]
    result = cl.kn_search(ot.name, only_schema=True)
    assert isinstance(result, dict)
    raw = result.get("raw", "")
    assert raw, "kn_search only_schema returned empty"


# ── MCP: query_object_instance ──────────────────────────────────────────


def test_mcp_query_instance_with_eq(cl_context):
    """MCP query_object_instance with == should return matching instance."""
    cl = cl_context["cl"]
    ot = cl_context["ot"]
    sample = cl_context["sample"]

    # Use the primary key from the sample instance for exact match
    identity = sample["_instance_identity"]
    pk_field = list(identity.keys())[0]
    pk_value = identity[pk_field]

    result = cl.query_object_instance(
        ot.id,
        condition={
            "operation": "and",
            "sub_conditions": [
                {"field": pk_field, "operation": "==", "value_from": "const", "value": pk_value},
            ],
        },
        limit=5,
    )
    raw = result.get("raw", "")
    assert "datas[#0]" not in raw, (
        f"Expected matching instances but got 0 results for {pk_field}=={pk_value}"
    )
    # Verify the sample data appears in the response
    assert str(pk_value) in raw, (
        f"Expected pk value {pk_value} in results but not found"
    )


def test_mcp_query_instance_with_in(cl_context):
    """MCP query_object_instance with 'in' operator should work."""
    cl = cl_context["cl"]
    ot = cl_context["ot"]
    sample = cl_context["sample"]

    identity = sample["_instance_identity"]
    pk_field = list(identity.keys())[0]
    pk_value = identity[pk_field]

    result = cl.query_object_instance(
        ot.id,
        condition={
            "operation": "and",
            "sub_conditions": [
                {"field": pk_field, "operation": "in", "value_from": "const", "value": [pk_value]},
            ],
        },
        limit=5,
    )
    raw = result.get("raw", "")
    assert str(pk_value) in raw


def test_mcp_query_instance_with_match(cl_context):
    """MCP query_object_instance with 'match' (fulltext) should return results."""
    cl = cl_context["cl"]
    ot = cl_context["ot"]
    sample = cl_context["sample"]

    # Find a text field with a non-empty value to use for match
    display_value = sample.get("_display", "")
    if not display_value:
        pytest.skip("Sample instance has no _display value for match test")

    result = cl.query_object_instance(
        ot.id,
        condition={
            "operation": "and",
            "sub_conditions": [
                {"field": ot.display_key, "operation": "match", "value_from": "const", "value": display_value},
            ],
        },
        limit=5,
    )
    raw = result.get("raw", "")
    assert "datas[#0]" not in raw, (
        f"Expected results for match '{display_value}' but got 0"
    )


# ── Cross-validation: MCP vs REST ──────────────────────────────────────


def test_mcp_rest_data_consistency(kweaver_client: KWeaverClient, cl_context):
    """Data from MCP query_object_instance should match REST query.instances."""
    ot = cl_context["ot"]
    kn = cl_context["kn"]
    cl = cl_context["cl"]
    sample = cl_context["sample"]

    identity = sample["_instance_identity"]
    pk_field = list(identity.keys())[0]
    pk_value = identity[pk_field]

    # Query via REST
    from kweaver.types import Condition
    rest_result = kweaver_client.query.instances(
        kn.id, ot.id,
        condition=Condition(field=pk_field, operation="==", value=pk_value),
        limit=1,
    )

    # Query via MCP
    mcp_result = cl.query_object_instance(
        ot.id,
        condition={
            "operation": "and",
            "sub_conditions": [
                {"field": pk_field, "operation": "==", "value_from": "const", "value": pk_value},
            ],
        },
        limit=1,
    )

    # REST should return data
    assert rest_result.data, f"REST returned no data for {pk_field}={pk_value}"
    rest_display = rest_result.data[0].get("_display", "")

    # MCP should return data containing the same display value
    mcp_raw = mcp_result.get("raw", "")
    assert "datas[#0]" not in mcp_raw, "MCP returned 0 results"
    if rest_display:
        assert rest_display in mcp_raw, (
            f"REST _display='{rest_display}' not found in MCP result"
        )
