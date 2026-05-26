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

"""Pipeline step constants and transition validation for the stateful ads co-director."""


class PipelineStep:
    AWAITING_BRIEF = "AWAITING_BRIEF"
    INGESTING_ASSETS = "INGESTING_ASSETS"
    INITIALIZING_MAB = "INITIALIZING_MAB"
    AWAITING_CREATIVE_APPROVAL = "AWAITING_CREATIVE_APPROVAL"
    RUNNING_CREATIVE_BRIEF = "RUNNING_CREATIVE_BRIEF"
    AWAITING_BRIEF_APPROVAL = "AWAITING_BRIEF_APPROVAL"
    RUNNING_STORYLINE_TO_STORYBOARD = "RUNNING_STORYLINE_TO_STORYBOARD"
    AWAITING_KEYFRAME_APPROVAL = "AWAITING_KEYFRAME_APPROVAL"
    RUNNING_KEYFRAMES = "RUNNING_KEYFRAMES"
    AWAITING_VIDEO_APPROVAL = "AWAITING_VIDEO_APPROVAL"
    RUNNING_VIDEO_AND_AUDIO = "RUNNING_VIDEO_AND_AUDIO"
    RUNNING_POST_PRODUCTION = "RUNNING_POST_PRODUCTION"
    CHECKING_ITERATION = "CHECKING_ITERATION"
    RUNNING_REPORT = "RUNNING_REPORT"
    PIPELINE_COMPLETE = "PIPELINE_COMPLETE"


ALL_STEPS = {
    getattr(PipelineStep, attr)
    for attr in dir(PipelineStep)
    if not attr.startswith("_")
}

AWAITING_STEPS = {s for s in ALL_STEPS if s.startswith("AWAITING_")}

VALID_TRANSITIONS: dict[str, list[str]] = {
    PipelineStep.AWAITING_BRIEF: [
        PipelineStep.INGESTING_ASSETS,
        PipelineStep.INITIALIZING_MAB,
    ],
    PipelineStep.INGESTING_ASSETS: [
        PipelineStep.INITIALIZING_MAB,
    ],
    PipelineStep.INITIALIZING_MAB: [
        PipelineStep.AWAITING_CREATIVE_APPROVAL,
        PipelineStep.RUNNING_CREATIVE_BRIEF,
    ],
    PipelineStep.AWAITING_CREATIVE_APPROVAL: [
        PipelineStep.RUNNING_CREATIVE_BRIEF,
        PipelineStep.INITIALIZING_MAB,
    ],
    PipelineStep.RUNNING_CREATIVE_BRIEF: [
        PipelineStep.AWAITING_BRIEF_APPROVAL,
    ],
    PipelineStep.AWAITING_BRIEF_APPROVAL: [
        PipelineStep.RUNNING_STORYLINE_TO_STORYBOARD,
        PipelineStep.RUNNING_CREATIVE_BRIEF,
    ],
    PipelineStep.RUNNING_STORYLINE_TO_STORYBOARD: [
        PipelineStep.AWAITING_KEYFRAME_APPROVAL,
    ],
    PipelineStep.AWAITING_KEYFRAME_APPROVAL: [
        PipelineStep.RUNNING_KEYFRAMES,
        PipelineStep.RUNNING_STORYLINE_TO_STORYBOARD,
    ],
    PipelineStep.RUNNING_KEYFRAMES: [
        PipelineStep.AWAITING_VIDEO_APPROVAL,
    ],
    PipelineStep.AWAITING_VIDEO_APPROVAL: [
        PipelineStep.RUNNING_VIDEO_AND_AUDIO,
        PipelineStep.RUNNING_KEYFRAMES,
    ],
    PipelineStep.RUNNING_VIDEO_AND_AUDIO: [
        PipelineStep.RUNNING_POST_PRODUCTION,
    ],
    PipelineStep.RUNNING_POST_PRODUCTION: [
        PipelineStep.CHECKING_ITERATION,
    ],
    PipelineStep.CHECKING_ITERATION: [
        PipelineStep.INITIALIZING_MAB,
        PipelineStep.RUNNING_REPORT,
    ],
    PipelineStep.RUNNING_REPORT: [
        PipelineStep.PIPELINE_COMPLETE,
    ],
}

GATE_TO_AWAITING_STEP: dict[str, str] = {
    "creative_direction": PipelineStep.AWAITING_CREATIVE_APPROVAL,
    "creative_brief": PipelineStep.AWAITING_BRIEF_APPROVAL,
    "keyframes": PipelineStep.AWAITING_KEYFRAME_APPROVAL,
    "video": PipelineStep.AWAITING_VIDEO_APPROVAL,
}

GATE_TO_ROLLBACK_STEP: dict[str, str] = {
    "creative_direction": PipelineStep.INITIALIZING_MAB,
    "creative_brief": PipelineStep.RUNNING_CREATIVE_BRIEF,
    "keyframes": PipelineStep.RUNNING_STORYLINE_TO_STORYBOARD,
    "video": PipelineStep.RUNNING_KEYFRAMES,
}


def validate_transition(from_step: str, to_step: str) -> bool:
    """Returns True if the transition from from_step to to_step is valid."""
    return to_step in VALID_TRANSITIONS.get(from_step, [])


def is_awaiting_step(step: str) -> bool:
    """Returns True if the step is an approval-waiting state."""
    return step in AWAITING_STEPS
