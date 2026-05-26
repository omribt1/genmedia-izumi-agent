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

"""Progress event utilities for streaming pipeline status to the UI."""

import logging
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.utils.context_utils import Aclosing
from google.genai import types as genai_types

logger = logging.getLogger(__name__)


def create_progress_event(
    author: str,
    message: str,
    step: str,
    progress_pct: int | None = None,
    invocation_id: str | None = None,
) -> Event:
    """Creates a progress event for streaming to the UI."""
    return Event(
        invocation_id=invocation_id,
        author=author,
        content=genai_types.Content(
            role="model",
            parts=[genai_types.Part(text=message)],
        ),
        partial=True,
        custom_metadata={
            "event_type": "pipeline_progress",
            "step": step,
            "progress_pct": progress_pct,
        },
    )


class ProgressWrapper(BaseAgent):
    """Wraps an agent and emits progress events before and after execution.

    Usage:
        wrapped = ProgressWrapper(
            name="keyframe_progress",
            start_message="Generating keyframes...",
            end_message="Keyframes complete.",
            step_name="keyframes",
            sub_agents=[keyframe_agent],
        )
    """

    start_message: str = ""
    end_message: str = ""
    step_name: str = ""

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        if not self.sub_agents:
            return

        if self.start_message:
            yield create_progress_event(
                author=self.name,
                message=self.start_message,
                step=self.step_name,
                invocation_id=ctx.invocation_id,
            )

        sub_agent = self.sub_agents[0]
        async with Aclosing(sub_agent.run_async(ctx)) as agen:
            async for event in agen:
                yield event

        if self.end_message:
            yield create_progress_event(
                author=self.name,
                message=self.end_message,
                step=self.step_name,
                progress_pct=100,
                invocation_id=ctx.invocation_id,
            )
