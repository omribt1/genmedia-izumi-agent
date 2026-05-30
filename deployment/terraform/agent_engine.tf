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

# Agent Runtime (Vertex AI Reasoning Engine) for the ads_codirector agent.
# The agent is deployed via scripts/deploy_ads_codirector_to_agent_engine.py
# which packages the source code and deploys to Vertex AI.
#
# This resource is managed by the deploy script, not Terraform directly,
# because Agent Runtime uses source-based deployment (not container images).
# The deploy script writes deployment_metadata.json with the resource name.
#
# The Cloud Run sidecar reads AGENT_ENGINE_RESOURCE_NAME env var to
# communicate with the deployed agent.

# GCS bucket for Agent Runtime staging (source upload)
resource "google_storage_bucket" "agent_engine_staging" {
  name                        = "${var.google_cloud_project}-agent-engine"
  location                    = var.google_cloud_location
  force_destroy               = true
  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis]
}

# GCS bucket for Agent Runtime artifacts (logs, data)
resource "google_storage_bucket" "agent_engine_logs" {
  name                        = "${var.google_cloud_project}-agents-logs-data"
  location                    = var.google_cloud_location
  force_destroy               = true
  uniform_bucket_level_access = true

  depends_on = [google_project_service.apis]
}
