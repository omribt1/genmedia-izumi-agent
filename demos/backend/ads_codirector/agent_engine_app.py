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

"""AdkApp subclass for deploying the ads_codirector agent to Agent Runtime."""

import copy
import logging
from typing import Any

from vertexai.preview.reasoning_engines import AdkApp

from .agent import root_agent

logger = logging.getLogger(__name__)


class AdsCoDirectorApp(AdkApp):
    """Agent Runtime wrapper for the stateful ads_codirector pipeline agent."""

    def set_up(self) -> None:
        """Initialize mediagent_kit services and tracing inside Agent Runtime."""
        super().set_up()

        import os

        import mediagent_kit

        mediagent_kit.initialize_from_env()

        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace import export as trace_export

        from utils.tracing import CloudTraceLoggingSpanExporter

        project_id = os.environ.get(
            "IZUMI_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        )
        provider = TracerProvider()
        processor = trace_export.BatchSpanProcessor(
            CloudTraceLoggingSpanExporter(project_id=project_id)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)

        logger.info(
            f"AdsCoDirectorApp: initialized with tracing (project={project_id})"
        )

    def register_operations(self) -> dict[str, list[str]]:
        operations = super().register_operations()
        operations[""] = operations[""] + ["register_feedback"]
        return operations

    def register_feedback(self, feedback: dict[str, Any]) -> None:
        logger.info(f"Feedback received: {feedback}")

    def clone(self) -> "AdsCoDirectorApp":
        template_attributes = self._tmpl_attrs
        return self.__class__(
            agent=copy.deepcopy(template_attributes["agent"]),
            enable_tracing=bool(template_attributes.get("enable_tracing", True)),
            session_service_builder=template_attributes.get("session_service_builder"),
            artifact_service_builder=template_attributes.get(
                "artifact_service_builder"
            ),
            env_vars=template_attributes.get("env_vars"),
        )


def create_app(
    artifacts_bucket: str | None = None,
) -> AdsCoDirectorApp:
    """Factory for the AdsCoDirectorApp with optional GCS artifact storage."""
    kwargs: dict[str, Any] = {"agent": root_agent, "enable_tracing": True}

    if artifacts_bucket:
        from google.adk.artifacts import GcsArtifactService

        kwargs["artifact_service_builder"] = lambda: GcsArtifactService(
            bucket_name=artifacts_bucket
        )

    return AdsCoDirectorApp(**kwargs)
