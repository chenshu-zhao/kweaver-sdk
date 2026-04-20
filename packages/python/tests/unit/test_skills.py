"""Unit tests for skill resource support."""

from __future__ import annotations

import io
import zipfile

import httpx

from kweaver import KWeaverClient
from kweaver.resources.skills import install_skill_archive


def _transport(handler):
    return httpx.MockTransport(handler)


def test_skills_list_unwraps_data():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/agent-operator-integration/v1/skills"
        assert request.url.params["page_size"] == "30"
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "total_count": 1,
                    "data": [{"skill_id": "skill-1", "name": "demo"}],
                },
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        result = client.skills.list()
        assert result["data"][0]["skill_id"] == "skill-1"
    finally:
        client.close()


def test_skills_get_and_read_file():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files/read"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "skill_id": "skill-1",
                        "rel_path": "refs/guide.md",
                        "url": "https://download.example/guide.md",
                    },
                },
            )
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"skill_id": "skill-1", "name": "demo", "status": "published"},
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        info = client.skills.get("skill-1")
        file_info = client.skills.read_file("skill-1", "refs/guide.md")
        assert info["skill_id"] == "skill-1"
        assert file_info["rel_path"] == "refs/guide.md"
    finally:
        client.close()


def test_skills_get_market_and_history():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/history"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": [{"skill_id": "skill-1", "version": "v1", "status": "published"}],
                },
            )
        assert request.url.path.endswith("/skills/market/skill-1")
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"skill_id": "skill-1", "name": "demo-market"},
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        market = client.skills.get_market("skill-1")
        history = client.skills.history("skill-1")
        assert market["skill_id"] == "skill-1"
        assert history[0]["version"] == "v1"
    finally:
        client.close()


def test_skills_update_metadata_and_publish_history():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/metadata"):
            assert request.method == "PUT"
            assert request.read() == b'{"name":"Demo","description":"Demo skill","category":"system","source":"internal","extend_info":{"owner":"sdk"}}'
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"skill_id": "skill-1", "version": "v2", "status": "editing"},
                },
            )
        assert request.url.path.endswith("/history/publish")
        assert request.method == "POST"
        assert request.read() == b'{"version":"v1"}'
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"skill_id": "skill-1", "version": "v1", "status": "published"},
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        metadata = client.skills.update_metadata(
            "skill-1",
            name="Demo",
            description="Demo skill",
            category="system",
            source="internal",
            extend_info={"owner": "sdk"},
        )
        publish = client.skills.publish_history("skill-1", "v1")
        assert metadata["status"] == "editing"
        assert publish["version"] == "v1"
    finally:
        client.close()


def test_skills_update_package_content_and_republish_history():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/package"):
            assert request.method == "PUT"
            assert request.read() == b'{"file_type":"content","file":"# demo\\n"}'
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {"skill_id": "skill-1", "version": "v3", "status": "editing"},
                },
            )
        assert request.url.path.endswith("/history/republish")
        assert request.method == "POST"
        assert request.read() == b'{"version":"v2"}'
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"skill_id": "skill-1", "version": "v2", "status": "editing"},
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        package_result = client.skills.update_package_content("skill-1", "# demo\n")
        republish = client.skills.republish_history("skill-1", "v2")
        assert package_result["version"] == "v3"
        assert republish["status"] == "editing"
    finally:
        client.close()


def test_skills_update_package_zip_uses_put_multipart():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PUT"
        assert request.url.path.endswith("/skills/skill-1/package")
        assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {"skill_id": "skill-1", "version": "v3", "status": "editing"},
            },
        )

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        result = client.skills.update_package_zip("skill-1", "demo.zip", b"PK")
        assert result["version"] == "v3"
    finally:
        client.close()


def test_skills_download_returns_filename():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"PK")

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        filename, data = client.skills.download("skill-1")
        assert filename == "skill-1.zip"
        assert data == b"PK"
    finally:
        client.close()


def test_skills_fetch_content_uses_shared_http_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/content"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "skill_id": "skill-1",
                        "url": "https://download.example/skill.md",
                    },
                },
            )
        assert str(request.url) == "https://download.example/skill.md"
        assert "authorization" not in request.headers
        return httpx.Response(200, text="# demo")

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        content = client.skills.fetch_content("skill-1")
        assert content == "# demo"
    finally:
        client.close()


def test_skills_fetch_file_uses_shared_http_client():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/files/read"):
            return httpx.Response(
                200,
                json={
                    "code": 0,
                    "data": {
                        "skill_id": "skill-1",
                        "rel_path": "refs/guide.md",
                        "url": "https://download.example/guide.md",
                    },
                },
            )
        assert str(request.url) == "https://download.example/guide.md"
        assert "authorization" not in request.headers
        return httpx.Response(200, content=b"guide")

    client = KWeaverClient(base_url="https://mock", token="tok", transport=_transport(handler))
    try:
        content = client.skills.fetch_file("skill-1", "refs/guide.md")
        assert content == b"guide"
    finally:
        client.close()


def test_install_skill_archive_extracts_zip(tmp_path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("SKILL.md", "# demo")
        zf.writestr("refs/guide.md", "guide")

    target = tmp_path / "demo-skill"
    install_skill_archive(buf.getvalue(), str(target))

    assert (target / "SKILL.md").read_text(encoding="utf-8") == "# demo"
    assert (target / "refs" / "guide.md").read_text(encoding="utf-8") == "guide"
