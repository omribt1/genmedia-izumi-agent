#!/usr/bin/env python3
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

"""Deploy the ads_codirector agent to Vertex AI Agent Runtime."""

import argparse
import datetime
import json
import logging
import os
import shutil
import sys
import tempfile

import google.auth
import vertexai
from vertexai import agent_engines

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
BACKEND_DIR = os.path.join(ROOT_DIR, "demos/backend")
KIT_DIR = os.path.join(ROOT_DIR, "mediagent_kit")

REQUIREMENTS = [
    "google-cloud-aiplatform[agent_engines,adk]>=1.132.0",
    "google-adk==1.29.0",
    "google-genai",
    "firebase-admin",
    "google-cloud-storage",
    "google-cloud-texttospeech",
    "fastapi",
    "uvicorn",
    "python-dotenv",
    "moviepy",
    "imageio-ffmpeg",
    "requests",
    "beautifulsoup4",
    "pydantic>=2.0",
    "cloudpickle>=3.0",
]


def create_bundle() -> str:
    """Create a temporary directory with flattened package structure."""
    bundle_dir = tempfile.mkdtemp(prefix="ads_codirector_deploy_")
    logger.info(f"Creating deployment bundle at {bundle_dir}")

    for item in os.listdir(BACKEND_DIR):
        src = os.path.join(BACKEND_DIR, item)
        dst = os.path.join(bundle_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)

    shutil.copytree(KIT_DIR, os.path.join(bundle_dir, "mediagent_kit"))
    return bundle_dir


def deploy(
    project: str,
    location: str,
    agent_name: str,
    asset_bucket: str,
    firestore_db_id: str,
    service_account: str | None = None,
) -> str:
    """Deploy the ads_codirector agent and return the resource name."""
    staging_bucket = f"gs://{project}-agent-engine"
    vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    bundle_dir = create_bundle()
    sys.path.insert(0, bundle_dir)
    os.chdir(bundle_dir)

    try:
        from ads_codirector.agent_engine_app import create_app

        app = create_app(artifacts_bucket=f"{project}-agents-logs-data")

        env_vars = {
            "IZUMI_PROJECT_ID": project,
            "IZUMI_LOCATION": "global",
            "GOOGLE_CLOUD_LOCATION": "global",
            "ASSET_SERVICE_GCS_BUCKET": asset_bucket,
            "FIRESTORE_DATABASE_ID": firestore_db_id,
            "DEPLOYMENT_MODE": "agent_runtime",
            "APP_ENV": "prod",
            "NUM_WORKERS": "1",
            "GOOGLE_GENAI_USE_VERTEXAI": "True",
            "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            "ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS": "true",
        }

        config = {
            "agent_engine": app,
            "display_name": agent_name,
            "description": "Stateful video ad creation agent with pipeline approval gates",
            "requirements": REQUIREMENTS,
            "extra_packages": ["ads_codirector", "mediagent_kit", "utils"],
            "env_vars": env_vars,
            "resource_limits": {"cpu": "4", "memory": "8Gi"},
        }

        if service_account:
            config["service_account"] = service_account

        existing = list(agent_engines.list(filter=f"display_name={agent_name}"))
        if existing:
            logger.info(f"Updating existing agent: {agent_name}")
            remote_agent = existing[0].update(**config)
        else:
            logger.info(f"Creating new agent: {agent_name}")
            remote_agent = agent_engines.create(**config)

        resource_name = remote_agent.resource_name
        logger.info(f"Deployed: {resource_name}")

        metadata = {
            "remote_agent_runtime_id": resource_name,
            "deployment_target": "agent_runtime",
            "deployment_timestamp": datetime.datetime.now().isoformat(),
            "agent_name": agent_name,
        }
        metadata_path = os.path.join(ROOT_DIR, "deployment/agent_engine_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Metadata written to {metadata_path}")

        return resource_name

    finally:
        os.chdir(ROOT_DIR)
        shutil.rmtree(bundle_dir)
        logger.info("Bundle cleaned up")


def main():
    parser = argparse.ArgumentParser(
        description="Deploy ads_codirector agent to Vertex AI Agent Runtime"
    )
    parser.add_argument("--project", default=None, help="GCP project ID")
    parser.add_argument("--location", default="us-central1", help="GCP region")
    parser.add_argument(
        "--agent-name",
        default="ads-codirector",
        help="Display name for the agent",
    )
    parser.add_argument(
        "--asset-bucket",
        default=None,
        help="GCS bucket for assets (defaults to {project}-izumi-assets)",
    )
    parser.add_argument(
        "--firestore-db-id",
        default="(default)",
        help="Firestore database ID",
    )
    parser.add_argument(
        "--service-account",
        default=None,
        help="Service account email",
    )
    args = parser.parse_args()

    if not args.project:
        _, args.project = google.auth.default()

    if not args.asset_bucket:
        args.asset_bucket = f"{args.project}-izumi-assets"

    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║  Deploying ads_codirector to Agent Runtime                ║
    ║  Project: {args.project:<46s} ║
    ║  Location: {args.location:<45s} ║
    ║  Agent: {args.agent_name:<48s} ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    resource_name = deploy(
        project=args.project,
        location=args.location,
        agent_name=args.agent_name,
        asset_bucket=args.asset_bucket,
        firestore_db_id=args.firestore_db_id,
        service_account=args.service_account,
    )

    print(f"\nAgent Runtime resource: {resource_name}")
    print(
        f"Console: https://console.cloud.google.com/vertex-ai/agent-runtime?project={args.project}"
    )


if __name__ == "__main__":
    main()
