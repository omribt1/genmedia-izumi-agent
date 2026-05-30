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

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from google.adk.sessions.session import Session

from google.adk.sessions.base_session_service import BaseSessionService

from mediagent_kit.services.aio.session_service_factory import (
    get_session_service as _get_session_service_impl,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Source: https://github.com/google/adk-python/blob/0094eea3cadf5fe2e960cc558e467dd2131de1b7/src/google/adk/cli/cli_eval.py#L52
EVAL_SESSION_ID_PREFIX = "___eval___session___"


def get_session_service() -> BaseSessionService:
    return _get_session_service_impl()


@router.get(
    "/users/{user_id}/sessions",
    tags=["Sessions"],
)
async def list_sessions(
    user_id: str,
    session_service: Annotated[BaseSessionService, Depends(get_session_service)],
) -> list[dict]:
    """
    Lists all sessions for a specific user.
    """
    response = await session_service.list_sessions(
        app_name="ads_codirector", user_id=user_id
    )

    results = []
    for session in response.sessions:
        if session.id.startswith(EVAL_SESSION_ID_PREFIX):
            continue
        results.append({
            "id": session.id,
            "appName": session.app_name,
            "lastUpdateTime": session.last_update_time,
            "sessionName": session.state.get("session_name", ""),
        })

    return results
