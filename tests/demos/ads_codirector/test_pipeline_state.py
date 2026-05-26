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

"""Tests for pipeline step constants, transitions, and tools."""

from unittest.mock import MagicMock

import pytest

from demos.backend.ads_codirector.utils.pipeline_steps import (
    ALL_STEPS,
    AWAITING_STEPS,
    GATE_TO_AWAITING_STEP,
    GATE_TO_ROLLBACK_STEP,
    PipelineStep,
    VALID_TRANSITIONS,
    is_awaiting_step,
    validate_transition,
)
from demos.backend.ads_codirector.tools.pipeline_tools import (
    advance_pipeline,
    present_for_approval,
    request_revision,
)


class TestPipelineSteps:
    def test_all_steps_are_unique(self):
        step_values = [
            getattr(PipelineStep, attr)
            for attr in dir(PipelineStep)
            if not attr.startswith("_")
        ]
        assert len(step_values) == len(set(step_values))

    def test_all_steps_set_matches_class(self):
        step_values = {
            getattr(PipelineStep, attr)
            for attr in dir(PipelineStep)
            if not attr.startswith("_")
        }
        assert step_values == ALL_STEPS

    def test_awaiting_steps_are_subset(self):
        assert AWAITING_STEPS.issubset(ALL_STEPS)
        for step in AWAITING_STEPS:
            assert step.startswith("AWAITING_")

    def test_valid_transitions_cover_non_terminal_steps(self):
        non_terminal = ALL_STEPS - {PipelineStep.PIPELINE_COMPLETE}
        for step in non_terminal:
            assert step in VALID_TRANSITIONS, f"Missing transitions for {step}"
            assert len(VALID_TRANSITIONS[step]) > 0, f"Empty transitions for {step}"

    def test_pipeline_complete_has_no_transitions(self):
        assert PipelineStep.PIPELINE_COMPLETE not in VALID_TRANSITIONS

    def test_validate_transition_valid(self):
        assert validate_transition(
            PipelineStep.AWAITING_BRIEF, PipelineStep.INGESTING_ASSETS
        )
        assert validate_transition(
            PipelineStep.AWAITING_BRIEF_APPROVAL,
            PipelineStep.RUNNING_STORYLINE_TO_STORYBOARD,
        )

    def test_validate_transition_invalid(self):
        assert not validate_transition(
            PipelineStep.AWAITING_BRIEF, PipelineStep.PIPELINE_COMPLETE
        )
        assert not validate_transition(
            PipelineStep.RUNNING_KEYFRAMES, PipelineStep.AWAITING_BRIEF
        )

    def test_is_awaiting_step(self):
        assert is_awaiting_step(PipelineStep.AWAITING_BRIEF)
        assert is_awaiting_step(PipelineStep.AWAITING_CREATIVE_APPROVAL)
        assert not is_awaiting_step(PipelineStep.RUNNING_KEYFRAMES)
        assert not is_awaiting_step(PipelineStep.PIPELINE_COMPLETE)

    def test_gate_maps_have_matching_keys(self):
        assert set(GATE_TO_AWAITING_STEP.keys()) == set(
            GATE_TO_ROLLBACK_STEP.keys()
        )

    def test_gate_awaiting_steps_are_valid(self):
        for gate, step in GATE_TO_AWAITING_STEP.items():
            assert step in ALL_STEPS, f"Gate {gate} maps to unknown step {step}"
            assert is_awaiting_step(step), f"Gate {gate} maps to non-awaiting step {step}"

    def test_gate_rollback_steps_are_valid(self):
        for gate, step in GATE_TO_ROLLBACK_STEP.items():
            assert step in ALL_STEPS, f"Gate {gate} rolls back to unknown step {step}"


def _make_tool_context(state=None):
    ctx = MagicMock()
    ctx.state = state or {}
    return ctx


class TestAdvancePipeline:
    def test_valid_transition(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.AWAITING_BRIEF,
            "pipeline_history": [],
        })
        result = advance_pipeline(ctx, PipelineStep.INGESTING_ASSETS, "Approved")
        assert result["status"] == "succeeded"
        assert ctx.state["pipeline_step"] == PipelineStep.INGESTING_ASSETS
        assert len(ctx.state["pipeline_history"]) == 1

    def test_invalid_transition(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.AWAITING_BRIEF,
            "pipeline_history": [],
        })
        result = advance_pipeline(ctx, PipelineStep.PIPELINE_COMPLETE, "Skip")
        assert result["status"] == "failed"
        assert ctx.state["pipeline_step"] == PipelineStep.AWAITING_BRIEF

    def test_clears_pending_approval(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.AWAITING_BRIEF,
            "pipeline_history": [],
            "pending_approval": {"gate": "test", "summary": "test"},
        })
        advance_pipeline(ctx, PipelineStep.INGESTING_ASSETS, "OK")
        assert ctx.state["pending_approval"] == {}


class TestRequestRevision:
    def test_valid_gate(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.AWAITING_BRIEF_APPROVAL,
            "pipeline_history": [],
        })
        result = request_revision(ctx, "creative_brief", "Needs more detail")
        assert result["status"] == "succeeded"
        assert ctx.state["pipeline_step"] == PipelineStep.RUNNING_CREATIVE_BRIEF
        assert ctx.state["approval_feedback"]["feedback"] == "Needs more detail"

    def test_invalid_gate(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.AWAITING_BRIEF_APPROVAL,
            "pipeline_history": [],
        })
        result = request_revision(ctx, "nonexistent_gate", "feedback")
        assert result["status"] == "failed"

    def test_all_gates_roll_back_correctly(self):
        for gate, expected_step in GATE_TO_ROLLBACK_STEP.items():
            ctx = _make_tool_context({
                "pipeline_step": "SOME_STATE",
                "pipeline_history": [],
            })
            result = request_revision(ctx, gate, "feedback")
            assert result["status"] == "succeeded"
            assert ctx.state["pipeline_step"] == expected_step


class TestPresentForApproval:
    def test_valid_gate(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.RUNNING_CREATIVE_BRIEF,
            "pipeline_history": [],
        })
        result = present_for_approval(ctx, "creative_brief", "Brief summary here")
        assert result["status"] == "succeeded"
        assert ctx.state["pipeline_step"] == PipelineStep.AWAITING_BRIEF_APPROVAL
        assert ctx.state["pending_approval"]["gate"] == "creative_brief"
        assert ctx.state["pending_approval"]["summary"] == "Brief summary here"

    def test_invalid_gate(self):
        ctx = _make_tool_context({
            "pipeline_step": PipelineStep.RUNNING_CREATIVE_BRIEF,
            "pipeline_history": [],
        })
        result = present_for_approval(ctx, "nonexistent", "summary")
        assert result["status"] == "failed"

    def test_all_gates_transition_correctly(self):
        for gate, expected_step in GATE_TO_AWAITING_STEP.items():
            ctx = _make_tool_context({
                "pipeline_step": "SOME_STATE",
                "pipeline_history": [],
            })
            result = present_for_approval(ctx, gate, "summary")
            assert result["status"] == "succeeded"
            assert ctx.state["pipeline_step"] == expected_step
