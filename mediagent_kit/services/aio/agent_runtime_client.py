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

"""Client for communicating with a deployed Agent Runtime instance.

Uses the :streamQuery REST API directly because the vertexai SDK (1.143.0)
doesn't expose async_stream_query on AgentEngine yet.
"""

import json
import logging
import os
from collections.abc import AsyncGenerator
from typing import Any

import aiohttp
import google.auth
import google.auth.transport.requests

logger = logging.getLogger(__name__)

_client_instance: "AgentRuntimeClient | None" = None


class AgentRuntimeClient:
    """Calls Agent Runtime's :streamQuery REST API directly."""

    def __init__(self, resource_name: str):
        self._resource_name = resource_name
        parts = resource_name.split("/")
        location = parts[3] if len(parts) == 6 else "us-central1"
        self._url = (
            f"https://{location}-aiplatform.googleapis.com/v1/"
            f"{resource_name}:streamQuery"
        )
        logger.info(f"AgentRuntimeClient initialized: {self._url}")

    def _get_token(self) -> str:
        creds, _ = google.auth.default()
        creds.refresh(google.auth.transport.requests.Request())
        return creds.token

    async def send_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> list[dict[str, Any]]:
        """Send a message and collect all response events."""
        events = []
        async for event in self.stream_message(user_id, session_id, message):
            events.append(event)
        return events

    async def stream_message(
        self,
        user_id: str,
        session_id: str,
        message: str,
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Yield events from Agent Runtime via :streamQuery REST API."""
        headers = {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "input": {
                "message": message,
                "user_id": user_id,
            }
        }
        if session_id:
            payload["input"]["session_id"] = session_id

        timeout = aiohttp.ClientTimeout(total=3600, sock_read=3600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self._url, json=payload, headers=headers
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.error(f"Agent Runtime error {resp.status}: {body[:500]}")
                    yield {"error": body, "code": resp.status}
                    return

                async for line in resp.content:
                    decoded = line.decode().strip()
                    if not decoded:
                        continue
                    try:
                        event = json.loads(decoded)
                        yield event
                    except json.JSONDecodeError:
                        logger.warning(f"Non-JSON line from Agent Runtime: {decoded[:100]}")


def get_agent_runtime_client() -> AgentRuntimeClient:
    """Returns a singleton AgentRuntimeClient."""
    global _client_instance
    if _client_instance is None:
        resource_name = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")
        if not resource_name:
            raise ValueError("AGENT_ENGINE_RESOURCE_NAME env var not set")
        _client_instance = AgentRuntimeClient(resource_name)
    return _client_instance
