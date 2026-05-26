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

"""Unit test for agent structure and definitions."""

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent


def test_llm_agent_definitions():
    """Verify that LLM agents are defined with correct types and names."""
    from ads_codirector.agent import (
        parameters_agent,
        user_assets_agent,
        creative_brief_agent,
        storyline_executor_agent,
        storyline_evaluator_agent,
        visual_casting_agent,
        storyboard_agent,
        voiceover_script_agent,
        storyboard_verifier_agent,
        keyframe_agent,
        video_agent,
        audio_agent,
        post_production_agent,
        final_video_verifier_agent,
        mab_logging_agent,
        mab_selection_agent,
        theoretical_definitions_agent,
        creative_director_agent,
        mab_report_agent,
        mab_initialization_agent,
        root_agent,
    )

    agents = [
        (parameters_agent, "parameters_agent"),
        (user_assets_agent, "user_assets_agent"),
        (creative_brief_agent, "creative_brief_agent"),
        (storyline_executor_agent, "storyline_executor_agent"),
        (storyline_evaluator_agent, "storyline_evaluator_agent"),
        (visual_casting_agent, "visual_casting_agent"),
        (storyboard_agent, "storyboard_agent"),
        (voiceover_script_agent, "voiceover_script_agent"),
        (storyboard_verifier_agent, "storyboard_verifier_agent"),
        (keyframe_agent, "keyframe_agent"),
        (video_agent, "video_agent"),
        (audio_agent, "audio_agent"),
        (post_production_agent, "post_production_agent"),
        (final_video_verifier_agent, "final_video_verifier_agent"),
        (mab_logging_agent, "mab_logging_agent"),
        (mab_selection_agent, "mab_selection_agent"),
        (theoretical_definitions_agent, "theoretical_definitions_agent"),
        (creative_director_agent, "creative_director_agent"),
        (mab_report_agent, "mab_report_agent"),
        (mab_initialization_agent, "mab_initialization_agent"),
        (root_agent, "orchestrator_agent"),
    ]

    for agent, name in agents:
        assert isinstance(agent, LlmAgent)
        assert agent.name == name


def test_progress_wrapper_agents():
    """Verify ProgressWrapper agents wrap the correct sub-agents."""
    from ads_codirector.agent import (
        creative_direction_pipeline,
        mab_initialization_agent_with_progress,
        creative_brief_with_saver,
        storyline_to_storyboard_pipeline,
        keyframe_agent_with_progress,
        video_audio_pipeline,
        post_production_pipeline,
    )
    from ads_codirector.utils.progress_events import ProgressWrapper

    wrappers = [
        creative_direction_pipeline,
        mab_initialization_agent_with_progress,
        creative_brief_with_saver,
        storyline_to_storyboard_pipeline,
        keyframe_agent_with_progress,
        video_audio_pipeline,
        post_production_pipeline,
    ]
    for wrapper in wrappers:
        assert isinstance(wrapper, ProgressWrapper), f"{wrapper.name} is not a ProgressWrapper"
        assert len(wrapper.sub_agents) == 1, f"{wrapper.name} should wrap exactly 1 sub-agent"


def test_root_agent_tools():
    """Verify root agent has the correct tools for stateful pipeline."""
    from ads_codirector.agent import root_agent

    tool_names = [t.name for t in root_agent.tools]

    # Agent tools
    assert "user_assets_agent" in tool_names
    assert "parameters_agent" in tool_names
    assert "mab_init_progress" in tool_names
    assert "creative_direction_progress" in tool_names
    assert "creative_brief_progress" in tool_names
    assert "mab_report_agent" in tool_names

    # Pipeline tools
    assert "advance_pipeline" in tool_names
    assert "request_revision" in tool_names
    assert "present_for_approval" in tool_names

    # Legacy tools should NOT be in root agent
    assert "mab_loop_agent" not in tool_names
    assert "iteration_agent" not in tool_names


def test_root_agent_has_callbacks():
    """Verify root agent has the required callbacks."""
    from ads_codirector.agent import root_agent

    assert root_agent.before_agent_callback is not None
    assert root_agent.before_model_callback is not None


def test_root_agent_instruction_is_callable():
    """Verify root agent instruction is a callable (dynamic provider)."""
    from ads_codirector.agent import root_agent

    assert callable(root_agent.instruction)
