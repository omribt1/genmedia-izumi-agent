# Copyright 2026 Google LLC
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

import json
import logging

from google.adk.apps import App
from google.adk.runners import Runner
from google.genai import types

from ads_codirector.agent import root_agent
from state_schema import CampaignStep

logger = logging.getLogger(__name__)

# Create the App wrapper for ads_codirector
ads_codirector_app = App(root_agent=root_agent, name="ads_codirector")


class IzumiResumeHandler:
    def __init__(self, session_service):
        """Initializes the resume handler with the Firestore session service."""
        self.session_service = session_service
        # Create the runner specifically for the ads_codirector app
        self.runner = Runner(app=ads_codirector_app, session_service=session_service)

    def _log_structured(self, severity: str, message: str, **kwargs) -> None:
        """Helper to output formatted JSON logs."""
        payload = {"severity": severity, "message": message, **kwargs}
        logger.info(json.dumps(payload))

    async def receive_storyboard_approval_callback(
        self, user_id: str, session_id: str
    ) -> None:
        """Called when the storyboard/script is approved by the user.

        Wakes up the ads_codirector agent, transitions the step to APPROVED, and resumes.
        """
        self._log_structured(
            severity="INFO",
            message=f"Received storyboard approval notification for session {session_id}",
            event="webhook_received",
            webhook_type="storyboard_approved",
            session_id=session_id,
            user_id=user_id,
        )

        try:
            self._log_structured(
                severity="INFO",
                message=f"State machine transitioned to {CampaignStep.APPROVED}",
                event="state_transition",
                session_id=session_id,
                user_id=user_id,
                new_step=CampaignStep.APPROVED,
            )

            # Trigger runner wake-up and run execution ambiently
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Resume production: Storyboard and script have been approved. Start video generation."
                        )
                    ],
                ),
                state_delta={
                    "current_step": CampaignStep.APPROVED,
                    "pending_signals": [],
                },
            ):
                self._log_structured(
                    severity="INFO",
                    message=f"Wake-up execution event: {event}",
                    event="runner_event",
                    session_id=session_id,
                    user_id=user_id,
                )

            self._log_structured(
                severity="INFO",
                message="Ambient storyboard approval execution turn completed successfully",
                event="runner_turn_success",
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            self._log_structured(
                severity="ERROR",
                message=f"Ambient storyboard approval execution turn failed: {e!s}",
                event="runner_turn_failure",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise
