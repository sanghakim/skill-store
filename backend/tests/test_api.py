"""
Tests for the FastAPI REST API endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport

from skillforge.api.server import api, get_app


# ═══════════════════════════════════════
# Setup
# ═══════════════════════════════════════

@pytest.fixture(autouse=True)
def reset_app():
    """Reset the app instance before each test."""
    import skillforge.api.server as srv
    srv.app_instance = None
    yield
    if srv.app_instance:
        srv.app_instance.shutdown()
        srv.app_instance = None


@pytest.fixture
async def client():
    transport = ASGITransport(app=api)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ═══════════════════════════════════════
# Health & System
# ═══════════════════════════════════════

class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_stats(self, client: AsyncClient):
        resp = await client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_skills" in data
        assert data["total_skills"] >= 14


# ═══════════════════════════════════════
# Skill Endpoints
# ═══════════════════════════════════════

class TestSkillEndpoints:
    @pytest.mark.asyncio
    async def test_list_skills(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 14
        assert len(data["skills"]) >= 14

    @pytest.mark.asyncio
    async def test_list_skills_with_query(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills?q=email")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any("email" in s["id"] for s in data["skills"])

    @pytest.mark.asyncio
    async def test_list_skills_by_category(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills?category=email")
        assert resp.status_code == 200
        data = resp.json()
        assert all(s["category"] == "email" for s in data["skills"])

    @pytest.mark.asyncio
    async def test_get_skill(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills/email-composer")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "email-composer"
        assert "inputs" in data

    @pytest.mark.asyncio
    async def test_get_skill_not_found(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills/nonexistent")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_create_skill(self, client: AsyncClient):
        new_skill = {
            "id": "api-test-skill",
            "name": "API Test Skill",
            "version": "1.0.0",
            "category": "other",
            "description": "Skill created via API for testing purposes",
            "prompt_template": "You are a test assistant. Handle: {{task}}. Respond professionally.",
            "inputs": [{"name": "task", "type": "string", "required": True}],
            "outputs": [{"name": "result", "type": "string"}],
        }
        resp = await client.post("/api/v1/skills", json=new_skill)
        assert resp.status_code == 200
        data = resp.json()
        assert data["skill_id"] == "api-test-skill"

    @pytest.mark.asyncio
    async def test_create_invalid_skill(self, client: AsyncClient):
        bad_skill = {
            "id": "BAD ID!",
            "name": "",
            "version": "nope",
            "prompt_template": "too short",
        }
        resp = await client.post("/api/v1/skills", json=bad_skill)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_skill(self, client: AsyncClient):
        # First create a skill
        new_skill = {
            "id": "to-delete",
            "name": "Delete Me",
            "version": "1.0.0",
            "category": "other",
            "description": "Skill that will be deleted during testing",
            "prompt_template": "You are a temporary assistant. Handle: {{input}}. Be helpful.",
            "inputs": [{"name": "input", "type": "string", "required": True}],
            "outputs": [{"name": "result", "type": "string"}],
        }
        await client.post("/api/v1/skills", json=new_skill)

        resp = await client.delete("/api/v1/skills/to-delete")
        assert resp.status_code == 200

        resp = await client.get("/api/v1/skills/to-delete")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_validate_skill(self, client: AsyncClient):
        resp = await client.post("/api/v1/skills/email-composer/validate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"]

    @pytest.mark.asyncio
    async def test_export_yaml(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills/email-composer/yaml")
        assert resp.status_code == 200
        data = resp.json()
        assert "yaml" in data
        assert "email-composer" in data["yaml"]

    @pytest.mark.asyncio
    async def test_list_categories(self, client: AsyncClient):
        resp = await client.get("/api/v1/skills/categories/list")
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data
        assert "document" in data


# ═══════════════════════════════════════
# Install Tracking
# ═══════════════════════════════════════

class TestInstallEndpoints:
    @pytest.mark.asyncio
    async def test_install_skill(self, client: AsyncClient):
        resp = await client.post("/api/v1/skills/email-composer/install?user_id=test-user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "installed"

    @pytest.mark.asyncio
    async def test_install_nonexistent(self, client: AsyncClient):
        resp = await client.post("/api/v1/skills/nonexistent/install")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_uninstall_skill(self, client: AsyncClient):
        await client.post("/api/v1/skills/email-composer/install?user_id=test-user")
        resp = await client.delete("/api/v1/skills/email-composer/install?user_id=test-user")
        assert resp.status_code == 200


# ═══════════════════════════════════════
# Session Endpoints
# ═══════════════════════════════════════

class TestSessionEndpoints:
    @pytest.mark.asyncio
    async def test_create_session(self, client: AsyncClient):
        resp = await client.post("/api/v1/session?user_id=test-user")
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["user_id"] == "test-user"

    @pytest.mark.asyncio
    async def test_get_session_messages(self, client: AsyncClient):
        # Create session first
        resp = await client.post("/api/v1/session?user_id=test-user")
        sid = resp.json()["session_id"]

        resp = await client.get(f"/api/v1/session/{sid}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid

    @pytest.mark.asyncio
    async def test_end_session(self, client: AsyncClient):
        resp = await client.post("/api/v1/session?user_id=test-user")
        sid = resp.json()["session_id"]

        resp = await client.delete(f"/api/v1/session/{sid}")
        assert resp.status_code == 200


# ═══════════════════════════════════════
# Chat Endpoint
# ═══════════════════════════════════════

class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat(self, client: AsyncClient):
        resp = await client.post("/api/v1/chat", json={
            "message": "이메일 작성해줘",
            "user_id": "test-user",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"]
        assert data["session_id"] is not None
        assert len(data["response"]) > 0
        assert data["iterations"] >= 1

    @pytest.mark.asyncio
    async def test_chat_with_session(self, client: AsyncClient):
        # Create session
        resp = await client.post("/api/v1/session?user_id=test-user")
        sid = resp.json()["session_id"]

        # Chat with session
        resp = await client.post("/api/v1/chat", json={
            "message": "보고서 작성해줘",
            "session_id": sid,
            "user_id": "test-user",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid

    @pytest.mark.asyncio
    async def test_execute_skill_directly(self, client: AsyncClient):
        resp = await client.post("/api/v1/skills/email-composer/execute", json={
            "inputs": {"context": "Follow-up meeting", "tone": "formal"},
            "user_id": "test-user",
        })
        assert resp.status_code == 200
