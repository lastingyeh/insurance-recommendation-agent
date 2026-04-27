from __future__ import annotations

import json
from importlib import import_module

from fastapi.testclient import TestClient
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types as genai_types

from app.api.dependencies import reset_dependency_caches
from app.config import AppRuntimeConfig
from app.container import create_session_store


def create_test_client(monkeypatch, tmp_path):
    session_db_path = tmp_path / "adk_sessions_test.db"

    monkeypatch.setenv("ADK_APP_NAME", "app")
    monkeypatch.setenv("ADK_API_USER_ID", "test-user")
    monkeypatch.setenv(
        "ADK_SESSION_DB_URI",
        f"sqlite+aiosqlite:///{session_db_path}",
    )
    monkeypatch.setenv("TOOLBOX_SERVER_URL", "http://127.0.0.1:5999")
    monkeypatch.setenv("FASTAPI_CORS_ALLOW_ORIGINS", "http://localhost:3000")

    reset_dependency_caches()
    main_module = import_module("app.api.main")
    app = main_module.create_app()
    return TestClient(app)


def parse_sse_frames(response_text: str) -> list[dict[str, object]]:
    frames: list[dict[str, object]] = []
    for chunk in response_text.split("\n\n"):
        if not chunk.strip():
            continue
        lines = [line for line in chunk.splitlines() if line.startswith("data: ")]
        if not lines:
            continue
        payload = "\n".join(line[6:] for line in lines)
        frames.append(json.loads(payload))
    return frames


def test_healthz_returns_ok(monkeypatch, tmp_path):
    client = create_test_client(monkeypatch, tmp_path)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "appName": "app"}


def test_session_crud_round_trip(monkeypatch, tmp_path):
    client = create_test_client(monkeypatch, tmp_path)

    response = client.get("/api/agent/sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": []}

    create_response = client.post(
        "/api/agent/sessions",
        json={
            "sessionId": "session-123",
            "state": {
                "_ui_title": "新對話",
                "_ui_subtitle": "開始新的對話",
                "user:age": 30,
            },
        },
    )
    assert create_response.status_code == 200
    assert create_response.json() == {"ok": True}

    list_response = client.get("/api/agent/sessions")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload["sessions"]) == 1
    session = payload["sessions"][0]
    assert session["id"] == "session-123"
    assert session["title"] == "新對話"
    assert session["subtitle"] == "開始新的對話"
    assert session["status"] == "idle"
    assert session["state"] == {"user:age": "30"}

    delete_response = client.delete("/api/agent/sessions/session-123")
    assert delete_response.status_code == 200
    assert delete_response.json() == {"ok": True}

    final_list_response = client.get("/api/agent/sessions")
    assert final_list_response.status_code == 200
    assert final_list_response.json() == {"sessions": []}


def test_create_session_store_uses_sqlite_service_for_sqlite_plus_aiosqlite_uri():
    config = AppRuntimeConfig(
        app_name="app",
        api_user_id="test-user",
        toolbox_server_url="http://127.0.0.1:5999",
        session_db_uri="sqlite+aiosqlite:///./db/adk_sessions.db",
        memory_mode="in_memory",
        model_name="gemini-3-flash-preview",
        fastapi_host="127.0.0.1",
        fastapi_port=8080,
        fastapi_reload=False,
        cors_allow_origins=("http://localhost:3000",),
    )

    session_store = create_session_store(config)

    assert isinstance(session_store, SqliteSessionService)


def test_run_stream_returns_sse_envelopes(monkeypatch, tmp_path):
    client = create_test_client(monkeypatch, tmp_path)
    run_module = import_module("app.api.routes.run")

    class FakeRunner:
        async def run_async(
            self,
            *,
            user_id,
            session_id,
            invocation_id=None,
            new_message=None,
            state_delta=None,
            run_config=None,
        ):
            yield Event(
                invocation_id="inv-1",
                author="app",
                content=genai_types.Content(
                    role="model",
                    parts=[
                        genai_types.Part(
                            function_call=genai_types.FunctionCall(
                                name="search_medical_products",
                                args={"age": 30},
                            )
                        )
                    ],
                ),
            )
            yield Event(
                invocation_id="inv-1",
                author="app",
                content=genai_types.Content(
                    role="model",
                    parts=[
                        genai_types.Part(
                            function_response=genai_types.FunctionResponse(
                                name="search_medical_products",
                                response={"top_product": "安心醫療"},
                            )
                        )
                    ],
                ),
            )
            yield Event(
                invocation_id="inv-1",
                author="app",
                partial=True,
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text="先根據你的預算")],
                ),
            )
            yield Event(
                invocation_id="inv-1",
                author="app",
                actions=EventActions(
                    state_delta={"user:last_recommended_product_name": "安心醫療"}
                ),
                content=genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(text="推薦安心醫療，保障與預算較匹配。")],
                ),
            )

    monkeypatch.setattr(run_module, "get_runner", lambda: FakeRunner())

    response = client.post(
        "/api/agent/run",
        json={
            "prompt": "我 30 歲，年預算 15000，想加強醫療保障",
            "sessionId": "session-run-1",
            "sessionState": {"user:age": "30", "user:budget": "15000"},
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    frames = parse_sse_frames(response.text)
    assert frames[0]["type"] == "meta"
    assert any(
        frame.get("type") == "timeline" and frame["event"]["kind"] == "tool-call"
        for frame in frames
    )
    assert any(
        frame.get("type") == "timeline" and frame["event"]["kind"] == "tool-result"
        for frame in frames
    )
    assert any(
        frame.get("type") == "message" and frame.get("mode") == "append"
        for frame in frames
    )
    assert any(
        frame.get("type") == "state"
        and frame.get("patch") == {"user:last_recommended_product_name": "安心醫療"}
        for frame in frames
    )

    done_frame = next(frame for frame in frames if frame.get("type") == "done")
    assert done_frame["finalText"] == "推薦安心醫療，保障與預算較匹配。"
    assert done_frame["state"]["user:last_recommended_product_name"] == "安心醫療"


def test_run_stream_returns_error_envelope_when_runner_fails(monkeypatch, tmp_path):
    client = create_test_client(monkeypatch, tmp_path)
    run_module = import_module("app.api.routes.run")

    class FailingRunner:
        async def run_async(
            self,
            *,
            user_id,
            session_id,
            invocation_id=None,
            new_message=None,
            state_delta=None,
            run_config=None,
        ):
            if False:
                yield None
            raise RuntimeError("runner failed")

    monkeypatch.setattr(run_module, "get_runner", lambda: FailingRunner())

    response = client.post(
        "/api/agent/run",
        json={
            "prompt": "測試錯誤路徑",
            "sessionId": "session-run-error",
            "sessionState": {},
        },
    )

    assert response.status_code == 200
    frames = parse_sse_frames(response.text)
    assert frames[0]["type"] == "meta"
    assert frames[-1] == {"type": "error", "message": "runner failed"}
