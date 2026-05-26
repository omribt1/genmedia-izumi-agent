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

"""Pipeline checkpoint tools for the stateful ads co-director."""

import datetime
import logging

from google.adk.tools import ToolContext

from ..utils.common_utils import (
    APPROVAL_FEEDBACK_KEY,
    PENDING_APPROVAL_KEY,
    PIPELINE_HISTORY_KEY,
    PIPELINE_STEP_KEY,
    ToolResult,
    tool_failure,
    tool_success,
)
from ..utils.pipeline_steps import (
    GATE_TO_AWAITING_STEP,
    GATE_TO_ROLLBACK_STEP,
    validate_transition,
)

logger = logging.getLogger(__name__)


def advance_pipeline(
    tool_context: ToolContext,
    next_step: str,
    approval_notes: str,
) -> ToolResult:
    """Advances the pipeline to the next step after user approval.

    Args:
        next_step: The pipeline step to advance to.
        approval_notes: Summary of the user's approval or feedback.
    """
    current_step = tool_context.state.get(PIPELINE_STEP_KEY, "")

    if not validate_transition(current_step, next_step):
        return tool_failure(
            f"Cannot transition from '{current_step}' to '{next_step}'."
        )

    history = tool_context.state.get(PIPELINE_HISTORY_KEY, [])
    history.append({
        "from": current_step,
        "to": next_step,
        "notes": approval_notes,
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    })
    tool_context.state[PIPELINE_HISTORY_KEY] = history
    tool_context.state[PIPELINE_STEP_KEY] = next_step
    tool_context.state[PENDING_APPROVAL_KEY] = {}
    tool_context.state[APPROVAL_FEEDBACK_KEY] = {}

    logger.info(
        f"Pipeline advanced: {current_step} -> {next_step} | Notes: {approval_notes}"
    )

    return tool_success(f"Pipeline advanced from {current_step} to {next_step}.")


def request_revision(
    tool_context: ToolContext,
    gate_name: str,
    revision_feedback: str,
) -> ToolResult:
    """Records user revision feedback and resets the pipeline to re-run the rejected step.

    Args:
        gate_name: Which approval gate triggered the revision (creative_direction, creative_brief, keyframes, video).
        revision_feedback: The user's specific feedback on what to change.
    """
    rollback_step = GATE_TO_ROLLBACK_STEP.get(gate_name)
    if not rollback_step:
        return tool_failure(
            f"Unknown gate name: '{gate_name}'. "
            f"Valid gates: {list(GATE_TO_ROLLBACK_STEP.keys())}"
        )

    current_step = tool_context.state.get(PIPELINE_STEP_KEY, "")

    tool_context.state[APPROVAL_FEEDBACK_KEY] = {
        "gate": gate_name,
        "feedback": revision_feedback,
        "action": "revise",
    }
    tool_context.state[PIPELINE_STEP_KEY] = rollback_step
    tool_context.state[PENDING_APPROVAL_KEY] = {}

    history = tool_context.state.get(PIPELINE_HISTORY_KEY, [])
    history.append({
        "from": current_step,
        "to": rollback_step,
        "notes": f"Revision requested for {gate_name}: {revision_feedback}",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    })
    tool_context.state[PIPELINE_HISTORY_KEY] = history

    logger.info(
        f"Revision requested at gate '{gate_name}': {current_step} -> {rollback_step}"
    )

    return tool_success(
        f"Revision requested for '{gate_name}'. "
        f"Pipeline will re-run from {rollback_step}."
    )


def present_for_approval(
    tool_context: ToolContext,
    gate_name: str,
    summary: str,
) -> ToolResult:
    """Presents a pipeline artifact to the user and transitions to the approval-waiting state.

    Args:
        gate_name: Which approval gate (creative_direction, creative_brief, keyframes, video).
        summary: A formatted summary of what the user should review.
    """
    awaiting_step = GATE_TO_AWAITING_STEP.get(gate_name)
    if not awaiting_step:
        return tool_failure(
            f"Unknown gate name: '{gate_name}'. "
            f"Valid gates: {list(GATE_TO_AWAITING_STEP.keys())}"
        )

    current_step = tool_context.state.get(PIPELINE_STEP_KEY, "")

    tool_context.state[PIPELINE_STEP_KEY] = awaiting_step
    tool_context.state[PENDING_APPROVAL_KEY] = {
        "gate": gate_name,
        "summary": summary,
    }

    history = tool_context.state.get(PIPELINE_HISTORY_KEY, [])
    history.append({
        "from": current_step,
        "to": awaiting_step,
        "notes": f"Awaiting approval for {gate_name}",
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
    })
    tool_context.state[PIPELINE_HISTORY_KEY] = history

    logger.info(f"Pipeline paused at gate '{gate_name}': {awaiting_step}")

    # Force the agent to end its turn and wait for user input
    tool_context.actions.escalate = True

    return tool_success(
        f"STOP. Awaiting user approval for: {gate_name}. "
        "Do NOT call any more tools. Wait for the user to respond."
    )
