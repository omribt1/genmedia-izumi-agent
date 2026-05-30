/**
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

export interface PipelineStatusResponse {
  session_id: string;
  app_name: string;
  pipeline_step: string;
  pending_approval: { gate: string; summary: string } | null;
  mab_iteration: number;
  num_target_iterations: number;
  last_update_time: number;
  session_name: string;
}

export interface ApprovalPayload {
  approval_notes: string;
}

export interface RevisionPayload {
  gate_name: string;
  revision_feedback: string;
}

export const PIPELINE_STEPS = [
  'AWAITING_BRIEF',
  'INGESTING_ASSETS',
  'INITIALIZING_MAB',
  'AWAITING_CREATIVE_APPROVAL',
  'RUNNING_CREATIVE_BRIEF',
  'AWAITING_BRIEF_APPROVAL',
  'RUNNING_STORYLINE_TO_STORYBOARD',
  'AWAITING_KEYFRAME_APPROVAL',
  'RUNNING_KEYFRAMES',
  'AWAITING_VIDEO_APPROVAL',
  'RUNNING_VIDEO_AND_AUDIO',
  'RUNNING_POST_PRODUCTION',
  'CHECKING_ITERATION',
  'RUNNING_REPORT',
  'PIPELINE_COMPLETE',
] as const;

export type PipelineStep = (typeof PIPELINE_STEPS)[number];

export const STEP_LABELS: Record<string, string> = {
  AWAITING_BRIEF: 'Awaiting Brief',
  INGESTING_ASSETS: 'Ingesting Assets',
  INITIALIZING_MAB: 'Initializing',
  AWAITING_CREATIVE_APPROVAL: 'Review: Creative Direction',
  RUNNING_CREATIVE_BRIEF: 'Creative Brief',
  AWAITING_BRIEF_APPROVAL: 'Review: Creative Brief',
  RUNNING_STORYLINE_TO_STORYBOARD: 'Building Storyboard',
  AWAITING_KEYFRAME_APPROVAL: 'Review: Keyframes',
  RUNNING_KEYFRAMES: 'Generating Keyframes',
  AWAITING_VIDEO_APPROVAL: 'Review: Video Plan',
  RUNNING_VIDEO_AND_AUDIO: 'Generating Video & Audio',
  RUNNING_POST_PRODUCTION: 'Post-Production',
  CHECKING_ITERATION: 'Checking Iteration',
  RUNNING_REPORT: 'Generating Report',
  PIPELINE_COMPLETE: 'Complete',
};

export function isAwaitingStep(step: string): boolean {
  return step.startsWith('AWAITING_');
}
