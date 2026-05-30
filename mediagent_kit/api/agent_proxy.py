# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Proxy routes that forward ADK API calls to Agent Runtime.

Used in sidecar mode (DEPLOYMENT_MODE=agent_runtime) so the frontend chat UI
can talk to the deployed agent via the same origin.
"""

import asyncio
import json
import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from google.adk.sessions.base_session_service import BaseSessionService

from mediagent_kit.services.aio.agent_runtime_client import get_agent_runtime_client
from mediagent_kit.services.aio.session_service_factory import (
    get_session_service as _get_session_service_impl,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Agent Proxy"])


def _get_session_service() -> BaseSessionService:
    return _get_session_service_impl()


@router.get("/list-apps")
async def list_apps() -> list[str]:
    return ["ads_codirector"]


@router.get("/apps/{app_name}/users/{user_id}/sessions")
async def list_sessions(
    app_name: str,
    user_id: str,
    session_service: Annotated[BaseSessionService, Depends(_get_session_service)],
) -> list[dict[str, Any]]:
    response = await session_service.list_sessions(
        app_name=app_name, user_id=user_id
    )
    return [
        {
            "id": s.id,
            "app_name": s.app_name,
            "user_id": s.user_id,
            "state": s.state,
            "last_update_time": s.last_update_time,
            "sessionName": s.state.get("session_name", ""),
        }
        for s in response.sessions
    ]


@router.post("/apps/{app_name}/users/{user_id}/sessions")
async def create_session(
    app_name: str,
    user_id: str,
    session_service: Annotated[BaseSessionService, Depends(_get_session_service)],
) -> dict[str, Any]:
    session = await session_service.create_session(
        app_name=app_name, user_id=user_id
    )
    return {"id": session.id, "appName": session.app_name, "userId": session.user_id}


class RenamePayload(BaseModel):
    name: str


@router.patch("/apps/{app_name}/users/{user_id}/sessions/{session_id}/rename")
async def rename_session(
    app_name: str,
    user_id: str,
    session_id: str,
    payload: RenamePayload,
    session_service: Annotated[BaseSessionService, Depends(_get_session_service)],
) -> dict[str, str]:
    """Rename a session by storing the name in session state."""
    from datetime import datetime, timezone

    import vertexai

    engine_id = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "").split("/")[-1]
    client = vertexai.Client(
        project=os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        location="us-central1",
    )
    await client.aio.agent_engines.sessions.events.append(
        name=f"reasoningEngines/{engine_id}/sessions/{session_id}",
        author="system",
        invocation_id=f"rename-{int(datetime.now().timestamp())}",
        timestamp=datetime.now(timezone.utc),
        config={
            "actions": {
                "state_delta": {"session_name": payload.name},
            }
        },
    )
    return {"status": "renamed", "session_name": payload.name}


@router.get("/apps/{app_name}/users/{user_id}/sessions/{session_id}")
async def get_session(
    app_name: str,
    user_id: str,
    session_id: str,
    session_service: Annotated[BaseSessionService, Depends(_get_session_service)],
) -> dict[str, Any]:
    session = await session_service.get_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    if not session:
        return {"events": []}
    events = []
    for event in session.events:
        e: dict[str, Any] = {"author": event.author}
        if event.content:
            parts = []
            for part in event.content.parts:
                if part.text:
                    parts.append({"text": part.text})
                elif part.inline_data:
                    parts.append({
                        "inlineData": {
                            "mimeType": part.inline_data.mime_type,
                            "data": "",
                        }
                    })
            e["content"] = {"role": event.content.role, "parts": parts}
        if event.actions and event.actions.state_delta:
            e["actions"] = {"stateDelta": event.actions.state_delta}
        events.append(e)
    return {"events": events}


async def _process_message(
    new_message: dict[str, Any], user_id: str
) -> str:
    """Extract text and upload inline files as assets, returning a combined message."""
    parts = new_message.get("parts", [])
    texts = []
    asset_refs = []

    for part in parts:
        if "text" in part and part["text"]:
            texts.append(part["text"])
        elif "inlineData" in part:
            inline = part["inlineData"]
            mime_type = inline.get("mimeType", "application/octet-stream")
            data_b64 = inline.get("data", "")
            display_name = inline.get("displayName", "uploaded_file")

            if data_b64:
                import base64

                blob = base64.b64decode(data_b64)
                asset_service = (
                    await _get_async_asset_service()
                )
                asset = await asset_service.save_asset(
                    user_id=user_id,
                    file_name=display_name,
                    blob=blob,
                    mime_type=mime_type,
                )
                asset_refs.append(f"<asset://{display_name}>")
                logger.info(
                    f"Uploaded asset {display_name} -> {asset.id} for Agent Runtime"
                )

    message = " ".join(texts)
    if asset_refs:
        message += "\n" + "\n".join(asset_refs)
    return message


async def _get_async_asset_service():
    import mediagent_kit.services.aio

    return mediagent_kit.services.aio.get_asset_service()


@router.post("/run_sse")
async def run_sse(request: Request) -> StreamingResponse:
    body = await request.json()
    user_id = body.get("userId", "")
    session_id = body.get("sessionId", "")
    new_message = body.get("newMessage", {})

    try:
        message_text = await _process_message(new_message, user_id)
    except Exception as e:
        logger.error(f"Failed to process message: {e}", exc_info=True)
        message_text = " ".join(
            p.get("text", "") for p in new_message.get("parts", []) if p.get("text")
        )

    logger.info(f"run_sse: user={user_id}, session={session_id}, msg={message_text[:100]}")
    client = get_agent_runtime_client()

    async def event_generator():
        try:
            stream = client.stream_message(
                user_id=user_id,
                session_id=session_id,
                message=message_text,
            )
            aiter = stream.__aiter__()
            while True:
                try:
                    event = await asyncio.wait_for(aiter.__anext__(), timeout=15)
                    event["partial"] = True
                    yield f"data: {json.dumps(event)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                except StopAsyncIteration:
                    break

            yield f"data: {json.dumps({'partial': False, 'author': 'orchestrator_agent'})}\n\n"
        except Exception as e:
            logger.error(f"Agent Runtime stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
