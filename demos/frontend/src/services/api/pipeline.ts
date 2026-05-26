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

import { request } from './client';
import type { PipelineStatusResponse } from '../../data/types/pipeline';

export async function getPipelineStatus(
  userId: string,
): Promise<PipelineStatusResponse[]> {
  return request(`/users/${userId}/pipeline_status`);
}

export async function approvePipeline(
  userId: string,
  sessionId: string,
  notes: string = '',
): Promise<{ status: string; previous_step: string; next_step: string }> {
  return request(`/users/${userId}/sessions/${sessionId}/approve`, {
    method: 'POST',
    body: JSON.stringify({ approval_notes: notes }),
  });
}

export async function revisePipeline(
  userId: string,
  sessionId: string,
  gateName: string,
  feedback: string,
): Promise<{
  status: string;
  previous_step: string;
  rollback_step: string;
  gate: string;
}> {
  return request(`/users/${userId}/sessions/${sessionId}/revise`, {
    method: 'POST',
    body: JSON.stringify({
      gate_name: gateName,
      revision_feedback: feedback,
    }),
  });
}
