"""
FastAPI Server - REST API + WebSocket for the SkillForge platform.
Serves the workspace frontend and provides real-time agent event streaming.

v2.0: Added file upload, monitoring endpoints, metrics middleware.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from skillforge.app import SkillForgeApp
from skillforge.models import (
    OrchestrationResult,
    SkillCategory,
    SkillDefinition,
    SkillValidationResult,
    UserRequest,
)
from skillforge.monitoring.collector import MetricsCollector
from skillforge.monitoring.middleware import MetricsMiddleware

logger = logging.getLogger(__name__)

# ── App Instance ──
app_instance: SkillForgeApp | None = None

# ── Upload config ──
_project_root = Path(__file__).resolve().parent.parent.parent.parent
UPLOAD_DIR = _project_root / "uploads"
MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXTENSIONS = {
    ".txt", ".csv", ".json", ".md", ".xlsx", ".pdf",
    ".yaml", ".yml", ".py", ".html", ".xml", ".tsv",
    ".log", ".conf", ".ini", ".toml",
}


def get_app() -> SkillForgeApp:
    global app_instance
    if app_instance is None:
        skills_dir = _project_root / "skills"
        app_instance = SkillForgeApp(
            skills_dir=str(skills_dir) if skills_dir.exists() else None,
        )
        app_instance.initialize()
    return app_instance


# ── FastAPI Setup ──
api = FastAPI(
    title="SkillForge API",
    description="Multi-Agent System with Agentic Loop & Skill Store",
    version="2.0.0",
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Metrics middleware - must be added after CORS
api.add_middleware(MetricsMiddleware)


# ── Request/Response Models ──

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    user_id: str = "default"
    attachments: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    session_id: str
    response: str
    plan_summary: str | None = None
    iterations: int = 1
    total_tokens: int = 0
    total_time_ms: int = 0
    quality_score: float | None = None
    success: bool = True
    error: str | None = None
    skills_used: list[str] = Field(default_factory=list)


class SkillExecuteRequest(BaseModel):
    inputs: dict[str, Any] = {}
    session_id: str | None = None
    user_id: str = "default"


class SkillCreateRequest(BaseModel):
    id: str
    name: str
    version: str = "1.0.0"
    category: str = "other"
    description: str = ""
    icon: str = "doc"
    prompt_template: str = ""
    inputs: list[dict] = []
    outputs: list[dict] = []
    settings: dict = {}
    tags: list[str] = []


class StatsResponse(BaseModel):
    total_skills: int
    total_sessions: int
    memory_stats: dict
    registry_stats: dict


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size: int
    mime_type: str
    content_preview: str = ""


# ═══════════════════════════════════════
# File Upload Endpoint
# ═══════════════════════════════════════

@api.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile, session_id: str = "default"):
    """
    Upload a file attachment. The file content will be injected into the
    next chat message as context for the AI agents.

    Supported: .txt, .csv, .json, .md, .xlsx, .pdf, .yaml, .py, .html, etc.
    Max size: 10MB
    """
    # Validate extension
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    # Read file content
    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(400, f"File too large. Max: {MAX_UPLOAD_SIZE // (1024*1024)}MB")

    # Save to uploads directory
    file_id = str(uuid.uuid4())[:12]
    session_dir = UPLOAD_DIR / session_id
    session_dir.mkdir(parents=True, exist_ok=True)

    safe_name = f"{file_id}_{file.filename or 'file'}"
    file_path = session_dir / safe_name
    file_path.write_bytes(content)

    # Try to extract text preview
    content_preview = ""
    text_extensions = {".txt", ".csv", ".json", ".md", ".yaml", ".yml", ".py", ".html",
                       ".xml", ".tsv", ".log", ".conf", ".ini", ".toml"}
    if ext in text_extensions:
        try:
            text = content.decode("utf-8", errors="replace")
            content_preview = text[:2000]
        except Exception:
            content_preview = "(binary)"

    logger.info("File uploaded: %s (%d bytes) → %s", file.filename, len(content), file_path)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "file",
        size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        content_preview=content_preview,
    )


@api.get("/api/v1/upload/{file_id}")
async def get_upload_info(file_id: str, session_id: str = "default"):
    """Get info about an uploaded file."""
    session_dir = UPLOAD_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(404, "File not found")

    for f in session_dir.iterdir():
        if f.name.startswith(file_id):
            ext = f.suffix.lower()
            content_preview = ""
            text_extensions = {".txt", ".csv", ".json", ".md", ".yaml", ".yml", ".py", ".html"}
            if ext in text_extensions:
                try:
                    content_preview = f.read_text(encoding="utf-8", errors="replace")[:2000]
                except Exception:
                    pass
            return {
                "file_id": file_id,
                "filename": f.name.split("_", 1)[1] if "_" in f.name else f.name,
                "size": f.stat().st_size,
                "content_preview": content_preview,
                "path": str(f),
            }

    raise HTTPException(404, "File not found")


# ═══════════════════════════════════════
# Orchestration Endpoints
# ═══════════════════════════════════════

def _build_attachment_context(attachments: list[str], session_id: str) -> str:
    """Read uploaded files and build context string for the agentic loop."""
    if not attachments:
        return ""

    parts = []
    sid = session_id or "default"
    session_dir = UPLOAD_DIR / sid

    if not session_dir.exists():
        return ""

    for file_id in attachments:
        for f in session_dir.iterdir():
            if f.name.startswith(file_id):
                ext = f.suffix.lower()
                text_extensions = {".txt", ".csv", ".json", ".md", ".yaml", ".yml",
                                   ".py", ".html", ".xml", ".tsv", ".log"}
                if ext in text_extensions:
                    try:
                        text = f.read_text(encoding="utf-8", errors="replace")
                        name = f.name.split("_", 1)[1] if "_" in f.name else f.name
                        parts.append(f"\n\n[Attached file: {name}]\n{text[:8000]}")
                    except Exception as exc:
                        parts.append(f"\n\n[Attached file: {f.name} - read error: {exc}]")
                else:
                    name = f.name.split("_", 1)[1] if "_" in f.name else f.name
                    parts.append(f"\n\n[Attached file: {name} ({f.stat().st_size} bytes, {ext})]")
                break

    return "".join(parts)


@api.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint - processes user input through the Agentic Loop."""
    sf = get_app()
    mc = MetricsCollector()

    # Build full message with attachments
    full_message = request.message
    if request.attachments:
        attachment_context = _build_attachment_context(
            request.attachments, request.session_id or "default"
        )
        full_message += attachment_context

    result: OrchestrationResult = await sf.loop.run(
        user_input=full_message,
        session_id=request.session_id,
        user_id=request.user_id,
    )

    # Record metrics
    mc.record_request(
        latency_ms=result.total_time_ms,
        success=result.success,
        tokens=result.total_tokens,
        iterations=result.iterations,
    )
    if result.quality_review:
        mc.record_quality_score(result.quality_review.overall_score)
    if not result.success and result.error:
        mc.record_error(
            code="CHAT_ERROR",
            message=result.error,
            session_id=result.session_id,
        )

    plan_summary = None
    skills_used = []
    if result.plan:
        plan_summary = " → ".join(
            f"{t.agent_role.value}:{t.skill_id or 'task'}"
            for t in result.plan.tasks
        )
        skills_used = [t.skill_id for t in result.plan.tasks if t.skill_id]

    return ChatResponse(
        session_id=result.session_id,
        response=result.final_output,
        plan_summary=plan_summary,
        iterations=result.iterations,
        total_tokens=result.total_tokens,
        total_time_ms=result.total_time_ms,
        quality_score=result.quality_review.overall_score if result.quality_review else None,
        success=result.success,
        error=result.error,
        skills_used=skills_used,
    )


@api.post("/api/v1/session")
async def create_session(user_id: str = "default"):
    """Create a new session."""
    sf = get_app()
    session_id = sf.memory.start_session(user_id)
    return {"session_id": session_id, "user_id": user_id}


@api.delete("/api/v1/session/{session_id}")
async def end_session(session_id: str):
    """End a session and save to episodic memory."""
    sf = get_app()
    try:
        sf.memory.end_session(session_id)
    except Exception as exc:
        logger.warning("Failed to end session %s: %s", session_id, exc)
        raise HTTPException(404, f"Session not found or already ended: {session_id}")
    return {"status": "ended", "session_id": session_id}


@api.get("/api/v1/session/{session_id}/messages")
async def get_messages(session_id: str, last_n: int | None = None):
    """Get messages for a session."""
    sf = get_app()
    try:
        msgs = sf.memory.get_messages(session_id, last_n)
    except Exception:
        return {"session_id": session_id, "messages": [], "count": 0}
    return {
        "session_id": session_id,
        "messages": [m.model_dump(mode="json") for m in msgs],
        "count": len(msgs),
    }


@api.get("/api/v1/sessions")
async def list_sessions(user_id: str = "default"):
    """List all active sessions."""
    sf = get_app()
    sessions = sf.memory.working.list_sessions()
    session_list = []
    for sid, state in sessions.items():
        if state.user_id == user_id or user_id == "default":
            session_list.append({
                "session_id": sid,
                "user_id": state.user_id,
                "message_count": len(state.messages),
                "preview": state.messages[-1].content[:100] if state.messages else "",
                "created_at": state.messages[0].timestamp.isoformat() if state.messages else None,
            })
    return {"sessions": session_list, "count": len(session_list)}


# ═══════════════════════════════════════
# Skill Store Endpoints
# ═══════════════════════════════════════

@api.get("/api/v1/skills")
async def list_skills(
    category: str | None = None,
    q: str | None = None,
    sort_by: str = "downloads",
    limit: int = 50,
):
    """List and search skills."""
    sf = get_app()
    cat = SkillCategory(category) if category else None
    skills = sf.registry.search(query=q, category=cat, sort_by=sort_by, limit=limit)
    return {
        "skills": [s.model_dump(mode="json") for s in skills],
        "total": len(skills),
    }


@api.get("/api/v1/skills/{skill_id}")
async def get_skill(skill_id: str):
    """Get a single skill's details."""
    sf = get_app()
    skill = sf.registry.get(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill not found: {skill_id}")
    return skill.model_dump(mode="json")


@api.post("/api/v1/skills")
async def create_skill(request: SkillCreateRequest):
    """Publish a new skill to the store."""
    sf = get_app()
    from skillforge.engine.loader import SkillLoader
    skill = SkillLoader.from_dict(request.model_dump())
    validation = sf.validate_skill(skill)
    if not validation.valid:
        raise HTTPException(400, detail={
            "errors": validation.errors,
            "warnings": validation.warnings,
        })
    sf.registry.register(skill)
    return {"status": "published", "skill_id": skill.id, "validation": validation.model_dump()}


@api.delete("/api/v1/skills/{skill_id}")
async def delete_skill(skill_id: str):
    """Unpublish a skill."""
    sf = get_app()
    if sf.registry.unregister(skill_id):
        return {"status": "deleted", "skill_id": skill_id}
    raise HTTPException(404, f"Skill not found: {skill_id}")


@api.post("/api/v1/skills/{skill_id}/execute")
async def execute_skill(skill_id: str, request: SkillExecuteRequest):
    """Execute a skill directly."""
    sf = get_app()
    skill = sf.registry.get(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill not found: {skill_id}")

    result = await sf.loop.execute_skill(
        skill_id=skill_id,
        inputs=request.inputs,
        session_id=request.session_id,
        user_id=request.user_id,
    )
    return result


@api.post("/api/v1/skills/{skill_id}/validate")
async def validate_skill(skill_id: str):
    """Validate a skill definition."""
    sf = get_app()
    skill = sf.registry.get(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill not found: {skill_id}")
    result = sf.validate_skill(skill)
    return result.model_dump()


@api.post("/api/v1/skills/{skill_id}/install")
async def install_skill(skill_id: str, user_id: str = "default"):
    """Install a skill for a user."""
    sf = get_app()
    if sf.registry.install(user_id, skill_id):
        return {"status": "installed", "skill_id": skill_id}
    raise HTTPException(404, f"Skill not found: {skill_id}")


@api.delete("/api/v1/skills/{skill_id}/install")
async def uninstall_skill(skill_id: str, user_id: str = "default"):
    """Uninstall a skill for a user."""
    sf = get_app()
    sf.registry.uninstall(user_id, skill_id)
    return {"status": "uninstalled", "skill_id": skill_id}


@api.get("/api/v1/skills/categories/list")
async def list_categories():
    """List skill categories with counts."""
    sf = get_app()
    return sf.registry.get_categories()


@api.get("/api/v1/skills/{skill_id}/yaml")
async def export_yaml(skill_id: str):
    """Export a skill as YAML."""
    sf = get_app()
    skill = sf.registry.get(skill_id)
    if not skill:
        raise HTTPException(404, f"Skill not found: {skill_id}")
    from skillforge.engine.loader import SkillLoader
    yaml_str = SkillLoader.to_yaml(skill)
    return {"skill_id": skill_id, "yaml": yaml_str}


# ═══════════════════════════════════════
# System Endpoints
# ═══════════════════════════════════════

@api.get("/api/v1/stats", response_model=StatsResponse)
async def get_stats():
    """Get system statistics."""
    sf = get_app()
    return StatsResponse(
        total_skills=len(sf.registry.list_all()),
        total_sessions=len(sf.memory.working.list_sessions()),
        memory_stats=sf.memory.get_stats(),
        registry_stats=sf.registry.get_stats(),
    )


@api.get("/api/v1/health")
async def health():
    return {"status": "healthy", "version": "2.0.0"}


@api.get("/api/v1/system/info")
async def system_info():
    """Get system information for the workspace UI."""
    sf = get_app()
    info = sf.get_system_info()
    return info


# ═══════════════════════════════════════
# Monitoring Endpoints
# ═══════════════════════════════════════

@api.get("/api/v1/monitoring/metrics")
async def monitoring_metrics():
    """Get all system metrics."""
    mc = MetricsCollector()
    return mc.get_metrics()


@api.get("/api/v1/monitoring/health")
async def monitoring_health():
    """Detailed health check with component status."""
    sf = get_app()
    mc = MetricsCollector()

    llm_status = "unknown"
    if sf.sandbox:
        backend = sf.sandbox._llm
        llm_status = type(backend).__name__
        if hasattr(backend, "model"):
            llm_status = f"{backend.model} (active)"

    return mc.get_health(
        llm_status=llm_status,
        skills_count=len(sf.registry.list_all()) if sf.registry else 0,
        sessions_count=len(sf.memory.working.list_sessions()) if sf.memory else 0,
        memory_stats=sf.memory.get_stats() if sf.memory else {},
    )


@api.get("/api/v1/monitoring/timeline")
async def monitoring_timeline(minutes: int = 60):
    """Get time-series metrics data."""
    mc = MetricsCollector()
    return {"timeline": mc.get_timeline(minutes=minutes)}


@api.get("/api/v1/monitoring/agents")
async def monitoring_agents():
    """Get per-agent execution statistics."""
    mc = MetricsCollector()
    return {"agents": mc.get_agent_stats()}


@api.get("/api/v1/monitoring/skills")
async def monitoring_skills():
    """Get per-skill usage statistics."""
    mc = MetricsCollector()
    return {"skills": mc.get_skill_stats()}


@api.get("/api/v1/monitoring/errors")
async def monitoring_errors(limit: int = 50):
    """Get recent error log."""
    mc = MetricsCollector()
    return {"errors": mc.get_errors(limit=limit)}


@api.get("/api/v1/monitoring/quality")
async def monitoring_quality():
    """Get quality score distribution."""
    mc = MetricsCollector()
    return mc.get_quality_histogram()


# ═══════════════════════════════════════
# WebSocket - Real-time Chat with Event Streaming
# ═══════════════════════════════════════

@api.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat with agent event streaming.

    Client sends:
        {"type": "message", "message": "...", "session_id": "...", "attachments": [...]}
        {"type": "create_session", "user_id": "..."}
        {"type": "ping"}

    Server sends events in chronological order during execution:
        session_created, processing_started, intent_analyzed, plan_created,
        task_started, task_completed/task_failed, review_completed,
        iteration_complete, replanning, response, processing_complete, error
    """
    await websocket.accept()
    sf = get_app()
    mc = MetricsCollector()
    session_id = sf.memory.start_session("default")

    await websocket.send_json({
        "type": "session_created",
        "session_id": session_id,
    })

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")

            # Handle ping/pong for keepalive
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            # Handle session creation
            if msg_type == "create_session":
                user_id = data.get("user_id", "default")
                session_id = sf.memory.start_session(user_id)
                await websocket.send_json({
                    "type": "session_created",
                    "session_id": session_id,
                })
                continue

            # Handle session switching
            if msg_type == "switch_session":
                new_session_id = data.get("session_id")
                if new_session_id:
                    session_id = new_session_id
                    await websocket.send_json({
                        "type": "session_switched",
                        "session_id": session_id,
                    })
                continue

            # Handle chat message
            message = data.get("message", "")
            if not message:
                continue

            # Use session_id from message if provided
            if data.get("session_id"):
                session_id = data["session_id"]

            # Build full message with attachments
            full_message = message
            attachments = data.get("attachments", [])
            if attachments:
                attachment_context = _build_attachment_context(attachments, session_id)
                full_message += attachment_context

            # Create the event emitter callback for real-time streaming
            async def emit_event(event: dict):
                try:
                    await websocket.send_json(event)
                except RuntimeError:
                    pass  # Client disconnected mid-stream

            # Run the agentic loop with event streaming
            result = await sf.loop.run(
                user_input=full_message,
                session_id=session_id,
                user_id=data.get("user_id", "default"),
                event_callback=emit_event,
            )

            # Record metrics
            mc.record_request(
                latency_ms=result.total_time_ms,
                success=result.success,
                tokens=result.total_tokens,
                iterations=result.iterations,
            )
            if result.quality_review:
                mc.record_quality_score(result.quality_review.overall_score)
            if not result.success and result.error:
                mc.record_error(
                    code="WS_CHAT_ERROR",
                    message=result.error,
                    session_id=session_id,
                )

            # Build plan summary
            plan_summary = None
            skills_used = []
            if result.plan:
                plan_summary = " → ".join(
                    f"{t.agent_role.value}:{t.skill_id or 'task'}"
                    for t in result.plan.tasks
                )
                skills_used = [t.skill_id for t in result.plan.tasks if t.skill_id]

            # Send final response
            try:
                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "response": result.final_output,
                    "plan_summary": plan_summary,
                    "iterations": result.iterations,
                    "total_tokens": result.total_tokens,
                    "total_time_ms": result.total_time_ms,
                    "quality_score": result.quality_review.overall_score if result.quality_review else None,
                    "success": result.success,
                    "error": result.error,
                    "skills_used": skills_used,
                    "attachments": attachments,
                })
            except RuntimeError:
                pass

    except WebSocketDisconnect:
        try:
            sf.memory.end_session(session_id)
        except Exception:
            pass
        logger.info("WebSocket disconnected: %s", session_id)
    except Exception as exc:
        logger.error("WebSocket error: %s", exc)
        mc.record_error(code="WS_ERROR", message=str(exc), session_id=session_id)


# ═══════════════════════════════════════
# Static File Serving (Frontend)
# ═══════════════════════════════════════

# Serve frontend files from the project root directory
# This must be the LAST route to avoid catching API routes
_frontend_dir = Path(__file__).resolve().parent.parent.parent.parent
if (_frontend_dir / "workspace.html").exists():
    api.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
