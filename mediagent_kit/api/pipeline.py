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

"""Pipeline status and approval webhook endpoints for the dashboard."""

import logging
import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from google.adk.sessions.base_session_service import BaseSessionService

from mediagent_kit.services.aio.session_service_factory import (
    get_session_service as _get_session_service_impl,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Pipeline"])

EVAL_SESSION_ID_PREFIX = "___eval___session___"

PIPELINE_STEP_KEY = "pipeline_step"
PENDING_APPROVAL_KEY = "pending_approval"
MAB_ITERATION_KEY = "mab_iteration"
NUM_TARGET_ITERATIONS_KEY = "num_target_iterations"
PIPELINE_HISTORY_KEY = "pipeline_history"


class PipelineStatusResponse(BaseModel):
    session_id: str
    app_name: str
    pipeline_step: str
    pending_approval: dict[str, Any] | None
    mab_iteration: int
    num_target_iterations: int
    last_update_time: float
    session_name: str = ""


class ApprovalPayload(BaseModel):
    approval_notes: str = ""


class RevisionPayload(BaseModel):
    gate_name: str
    revision_feedback: str


def _get_session_service() -> BaseSessionService:
    return _get_session_service_impl()


@router.get(
    "/users/{user_id}/pipeline_status",
    response_model=list[PipelineStatusResponse],
)
async def get_pipeline_status(
    user_id: str,
    session_service: Annotated[
        BaseSessionService, Depends(_get_session_service)
    ],
) -> list[PipelineStatusResponse]:
    """Returns all sessions for a user with their pipeline state."""
    response = await session_service.list_sessions(
        app_name="ads_codirector", user_id=user_id
    )

    results = []
    for session in response.sessions:
        if session.id.startswith(EVAL_SESSION_ID_PREFIX):
            continue

        pipeline_step = session.state.get(PIPELINE_STEP_KEY)
        if not pipeline_step:
            continue

        pending = session.state.get(PENDING_APPROVAL_KEY)
        if isinstance(pending, dict) and not pending:
            pending = None

        results.append(
            PipelineStatusResponse(
                session_id=session.id,
                app_name=session.app_name,
                pipeline_step=pipeline_step,
                pending_approval=pending,
                mab_iteration=session.state.get(MAB_ITERATION_KEY, -1),
                num_target_iterations=session.state.get(
                    NUM_TARGET_ITERATIONS_KEY, 1
                ),
                last_update_time=session.last_update_time,
                session_name=session.state.get("session_name", ""),
            )
        )

    return results


@router.post("/users/{user_id}/sessions/{session_id}/approve")
async def approve_from_dashboard(
    user_id: str,
    session_id: str,
    payload: ApprovalPayload,
    request: Request,
    session_service: Annotated[
        BaseSessionService, Depends(_get_session_service)
    ],
) -> dict[str, str]:
    """Approve a pipeline gate from the dashboard and resume the agent."""
    from demos.backend.ads_codirector.utils.pipeline_steps import (
        VALID_TRANSITIONS,
        is_awaiting_step,
    )

    session = await session_service.get_session(
        app_name="ads_codirector",
        user_id=user_id,
        session_id=session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_step = session.state.get(PIPELINE_STEP_KEY, "")
    if not is_awaiting_step(current_step):
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in an approval state. Current: {current_step}",
        )

    valid_next = VALID_TRANSITIONS.get(current_step, [])
    if not valid_next:
        raise HTTPException(
            status_code=400,
            detail=f"No valid transitions from {current_step}.",
        )

    next_step = valid_next[0]
    message = f"[Dashboard Approval] Approved. {payload.approval_notes}"

    logger.info(
        f"Dashboard approval: {current_step} -> {next_step} "
        f"(user={user_id}, session={session_id})"
    )

    deployment_mode = os.environ.get("DEPLOYMENT_MODE", "local")

    if deployment_mode == "agent_runtime":
        from mediagent_kit.services.aio.agent_runtime_client import (
            get_agent_runtime_client,
        )

        client = get_agent_runtime_client()
        await client.send_message(
            user_id=user_id,
            session_id=session_id,
            message=message,
        )
    else:
        from google.genai import types as genai_types

        adk_server = request.app.state.adk_server
        runner = await adk_server.get_runner_async("ads_codirector")

        state_delta = {
            PIPELINE_STEP_KEY: next_step,
            PENDING_APPROVAL_KEY: {},
        }

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=message)],
            ),
            state_delta=state_delta,
        ):
            logger.info(f"Dashboard resume event: {event.author}")

    return {
        "status": "approved",
        "previous_step": current_step,
        "next_step": next_step,
    }


@router.post("/users/{user_id}/sessions/{session_id}/revise")
async def revise_from_dashboard(
    user_id: str,
    session_id: str,
    payload: RevisionPayload,
    request: Request,
    session_service: Annotated[
        BaseSessionService, Depends(_get_session_service)
    ],
) -> dict[str, str]:
    """Request revision from dashboard and resume the agent."""
    from demos.backend.ads_codirector.utils.pipeline_steps import (
        GATE_TO_ROLLBACK_STEP,
        is_awaiting_step,
    )

    session = await session_service.get_session(
        app_name="ads_codirector",
        user_id=user_id,
        session_id=session_id,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    current_step = session.state.get(PIPELINE_STEP_KEY, "")
    if not is_awaiting_step(current_step):
        raise HTTPException(
            status_code=400,
            detail=f"Session is not in an approval state. Current: {current_step}",
        )

    rollback_step = GATE_TO_ROLLBACK_STEP.get(payload.gate_name)
    if not rollback_step:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown gate: {payload.gate_name}. "
            f"Valid: {list(GATE_TO_ROLLBACK_STEP.keys())}",
        )

    message = f"[Dashboard Revision] {payload.gate_name}: {payload.revision_feedback}"
    deployment_mode = os.environ.get("DEPLOYMENT_MODE", "local")

    if deployment_mode == "agent_runtime":
        from mediagent_kit.services.aio.agent_runtime_client import (
            get_agent_runtime_client,
        )

        client = get_agent_runtime_client()
        await client.send_message(
            user_id=user_id,
            session_id=session_id,
            message=message,
        )
    else:
        from google.genai import types as genai_types

        state_delta = {
            PIPELINE_STEP_KEY: rollback_step,
            PENDING_APPROVAL_KEY: {},
            "approval_feedback": {
                "gate": payload.gate_name,
                "feedback": payload.revision_feedback,
                "action": "revise",
            },
        }

        adk_server = request.app.state.adk_server
        runner = await adk_server.get_runner_async("ads_codirector")

        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=message)],
            ),
            state_delta=state_delta,
        ):
            logger.info(f"Dashboard revision event: {event.author}")

    return {
        "status": "revision_requested",
        "previous_step": current_step,
        "rollback_step": rollback_step,
        "gate": payload.gate_name,
    }
