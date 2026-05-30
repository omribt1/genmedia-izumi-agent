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

"""Tool to generate a visual HTML storyboard from the pipeline state."""

import logging
from html import escape
from typing import Any

from google.adk.tools.tool_context import ToolContext

import mediagent_kit.services.aio
from utils.adk import get_user_id_from_context

from ..utils.common_utils import (
    CREATIVE_BRIEF_KEY,
    STORYBOARD_KEY,
    ToolResult,
    tool_failure,
    tool_success,
)

logger = logging.getLogger(__name__)


def _build_html(
    storyboard: dict[str, Any],
    creative_brief: str,
    user_id: str,
    base_url: str,
) -> str:
    """Build an HTML page showing the storyboard scenes with prompts and images."""
    scenes = storyboard.get("scenes", [])
    voiceover = storyboard.get("voiceover_prompt", {})
    music = storyboard.get("background_music_prompt", {})

    scene_cards = []
    for i, scene in enumerate(scenes):
        topic = escape(scene.get("topic", f"Scene {i + 1}"))
        frame_prompt = scene.get("first_frame_prompt", {})
        video_prompt = scene.get("video_prompt", {})
        frame_desc = escape(frame_prompt.get("description", ""))
        video_desc = escape(video_prompt.get("description", ""))
        duration = video_prompt.get("duration_seconds", "?")
        ref_assets = frame_prompt.get("assets", [])

        # Find the latest generated keyframe asset_id
        gen_history = scene.get("first_frame_generation_history", [])
        keyframe_asset_id = None
        if gen_history:
            last = gen_history[-1]
            keyframe_asset_id = last.get("asset_id") or last.get("id")

        keyframe_img = ""
        if keyframe_asset_id:
            img_url = f"{base_url}/users/{user_id}/assets/{keyframe_asset_id}/download"
            keyframe_img = f"""
            <div class="keyframe-img">
                <img src="{img_url}" alt="Keyframe for {topic}" loading="lazy" />
            </div>"""
        else:
            keyframe_img = """
            <div class="keyframe-img placeholder">
                <span>Keyframe not yet generated</span>
            </div>"""

        ref_list = ""
        if ref_assets:
            ref_items = "".join(
                f'<img src="{base_url}/users/{user_id}/assets/{escape(a)}/download" '
                f'alt="{escape(a)}" class="ref-thumb" loading="lazy" />'
                for a in ref_assets if a
            )
            ref_list = f'<div class="ref-images"><strong>Reference Assets:</strong><div class="ref-grid">{ref_items}</div></div>'

        scene_cards.append(f"""
        <div class="scene-card">
            <div class="scene-header">
                <span class="scene-num">Scene {i + 1}</span>
                <span class="scene-topic">{topic}</span>
                <span class="scene-duration">{duration}s</span>
            </div>
            <div class="scene-body">
                {keyframe_img}
                <div class="scene-prompts">
                    <div class="prompt-block">
                        <label>Keyframe Prompt</label>
                        <p>{frame_desc}</p>
                    </div>
                    <div class="prompt-block">
                        <label>Video Prompt</label>
                        <p>{video_desc}</p>
                    </div>
                    {ref_list}
                </div>
            </div>
        </div>""")

    scenes_html = "\n".join(scene_cards)
    voiceover_text = escape(voiceover.get("text", ""))
    voiceover_style = escape(voiceover.get("description", ""))
    music_desc = escape(music.get("description", ""))
    brief_escaped = escape(creative_brief or "").replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Storyboard Preview</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f0f0f; color: #e0e0e0; padding: 2rem; }}
  h1 {{ text-align: center; margin-bottom: 0.5rem; color: #fff; font-size: 1.8rem; }}
  .subtitle {{ text-align: center; color: #888; margin-bottom: 2rem; }}
  .section {{ background: #1a1a1a; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }}
  .section h2 {{ color: #4fc3f7; font-size: 1.1rem; margin-bottom: 0.8rem; border-bottom: 1px solid #333; padding-bottom: 0.5rem; }}
  .scene-card {{ background: #1a1a1a; border-radius: 12px; margin-bottom: 1.5rem; overflow: hidden; border: 1px solid #2a2a2a; }}
  .scene-header {{ display: flex; align-items: center; gap: 1rem; padding: 1rem 1.5rem; background: #222; }}
  .scene-num {{ background: #4fc3f7; color: #000; padding: 0.2rem 0.8rem; border-radius: 20px; font-weight: 700; font-size: 0.85rem; }}
  .scene-topic {{ font-weight: 600; flex: 1; }}
  .scene-duration {{ color: #888; font-size: 0.9rem; }}
  .scene-body {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; padding: 1.5rem; }}
  .keyframe-img img {{ width: 100%; border-radius: 8px; }}
  .keyframe-img.placeholder {{ display: flex; align-items: center; justify-content: center; min-height: 200px; background: #252525; border-radius: 8px; color: #666; }}
  .scene-prompts {{ display: flex; flex-direction: column; gap: 1rem; }}
  .prompt-block label {{ display: block; color: #4fc3f7; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }}
  .prompt-block p {{ color: #ccc; font-size: 0.9rem; line-height: 1.5; }}
  .ref-images {{ margin-top: 0.5rem; }}
  .ref-images strong {{ color: #888; font-size: 0.8rem; }}
  .ref-grid {{ display: flex; gap: 0.5rem; margin-top: 0.3rem; flex-wrap: wrap; }}
  .ref-thumb {{ width: 60px; height: 60px; object-fit: cover; border-radius: 6px; border: 1px solid #333; }}
  .audio-section {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; }}
  .audio-block label {{ color: #4fc3f7; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }}
  .audio-block p {{ color: #ccc; font-size: 0.9rem; margin-top: 0.3rem; line-height: 1.5; }}
  .brief-section {{ font-size: 0.9rem; color: #aaa; line-height: 1.6; max-height: 200px; overflow-y: auto; }}
  @media (max-width: 768px) {{ .scene-body {{ grid-template-columns: 1fr; }} .audio-section {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<h1>Storyboard Preview</h1>
<p class="subtitle">{len(scenes)} scenes</p>

{scenes_html}

<div class="section">
  <h2>Audio</h2>
  <div class="audio-section">
    <div class="audio-block">
      <label>Voiceover</label>
      <p>{voiceover_text}</p>
      <p style="color:#666;font-size:0.8rem;margin-top:0.3rem">Style: {voiceover_style}</p>
    </div>
    <div class="audio-block">
      <label>Background Music</label>
      <p>{music_desc}</p>
    </div>
  </div>
</div>

<div class="section">
  <h2>Creative Brief</h2>
  <div class="brief-section">{brief_escaped}</div>
</div>
</body>
</html>"""


async def generate_storyboard_html(tool_context: ToolContext) -> ToolResult:
    """Generates a visual HTML page showing the storyboard with prompts and keyframe images.

    Call this after storyboard generation or keyframe generation to create
    a visual preview page. The HTML is saved as an asset and the URL is returned.
    """
    state = tool_context.state
    storyboard = state.get(STORYBOARD_KEY)
    if not storyboard:
        return tool_failure("No storyboard found in session state.")

    user_id = get_user_id_from_context(tool_context)
    creative_brief = state.get(CREATIVE_BRIEF_KEY, "")
    if isinstance(creative_brief, dict):
        creative_brief = creative_brief.get("brief", str(creative_brief))

    base_url = ""
    mab_iter = state.get("mab_iteration", 0)

    html = _build_html(storyboard, creative_brief, user_id, base_url)

    asset_service = mediagent_kit.services.aio.get_asset_service()
    asset = await asset_service.save_asset(
        user_id=user_id,
        file_name=f"iter_{mab_iter}_storyboard_preview.html",
        blob=html.encode("utf-8"),
        mime_type="text/html",
    )

    logger.info(f"Storyboard HTML saved as asset {asset.id}")

    return tool_success(
        f"Storyboard HTML preview saved. "
        f"View it at: /users/{user_id}/assets/{asset.id}/download"
    )
