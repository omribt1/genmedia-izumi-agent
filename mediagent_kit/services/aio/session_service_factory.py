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

"""Environment-based session service factory."""

import logging
import os

from google.adk.sessions.base_session_service import BaseSessionService

logger = logging.getLogger(__name__)


def get_session_service() -> BaseSessionService:
    """Returns the appropriate session service based on DEPLOYMENT_MODE.

    - "local" (default): Uses FirestoreSessionService if emulator is available,
      otherwise InMemorySessionService.
    - "agent_runtime": Uses VertexAiSessionService pointed at the deployed
      Agent Runtime instance.
    """
    deployment_mode = os.environ.get("DEPLOYMENT_MODE", "local")

    if deployment_mode == "agent_runtime":
        resource_name = os.environ.get("AGENT_ENGINE_RESOURCE_NAME", "")
        if not resource_name:
            raise ValueError(
                "AGENT_ENGINE_RESOURCE_NAME must be set when DEPLOYMENT_MODE=agent_runtime"
            )

        # Extract location and numeric ID from the full resource name
        # Format: projects/{project_number}/locations/{location}/reasoningEngines/{id}
        parts = resource_name.split("/")
        if len(parts) == 6:
            location = parts[3]
            engine_id = parts[5]
        else:
            engine_id = resource_name
            location = "us-central1"

        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")

        from google.adk.sessions import VertexAiSessionService

        logger.info(
            f"Using VertexAiSessionService (project={project}, "
            f"location={location}, engine_id={engine_id})"
        )
        return VertexAiSessionService(
            project=project, location=location, agent_engine_id=engine_id
        )

    # Local mode: try Firestore emulator, fall back to InMemory
    emulator_host = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if emulator_host:
        from mediagent_kit.services.aio import get_firestore_session_service

        logger.info(f"Using FirestoreSessionService (emulator at {emulator_host})")
        return get_firestore_session_service()

    from google.adk.sessions import InMemorySessionService

    logger.info("Using InMemorySessionService (no emulator, local mode)")
    return InMemorySessionService()
