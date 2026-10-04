"""
name: Export Timeline Metadata
description: Экспортирует текущую временную шкалу, ее маркеры и видеоклипы в файл JSON.
params:
  - name: output_path
    type: file
    default: ~/Desktop/timeline_export.json
  - name: include_markers
    type: bool
    default: true
  - name: include_video_clips
    type: bool
    default: true
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def run(resolve: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Write selected metadata from the current Resolve timeline as JSON."""
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        raise RuntimeError("Open a project and select a timeline before running this script.")

    export = {
        "project_name": project.GetName(),
        "timeline_name": timeline.GetName(),
        "frame_rate": timeline.GetSetting("timelineFrameRate"),
        "start_frame": timeline.GetStartFrame(),
        "end_frame": timeline.GetEndFrame(),
    }
    if bool(params["include_markers"]):
        export["markers"] = timeline.GetMarkers() or {}
    if bool(params["include_video_clips"]):
        export["video_clips"] = _video_clips(timeline)

    output_path = Path(str(params["output_path"])).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(export, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    return {"output_path": str(output_path), "timeline_name": timeline.GetName()}


def _video_clips(timeline: Any) -> List[Dict[str, Any]]:
    clips = []
    for track_index in range(1, timeline.GetTrackCount("video") + 1):
        for clip in timeline.GetItemListInTrack("video", track_index) or []:
            clips.append(
                {
                    "track": track_index,
                    "name": clip.GetName(),
                    "start_frame": clip.GetStart(),
                    "end_frame": clip.GetEnd(),
                    "duration": clip.GetDuration(),
                }
            )
    return clips
