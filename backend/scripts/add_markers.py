"""
name: Add Markers to Timeline
description: Добавляет маркер в начале каждого клипа на выбранной дорожке.
params:
  - name: track_type
    type: select
    options: [video, audio]
    default: video
  - name: track_index
    type: number
    default: 1
  - name: color
    type: select
    options: [Red, Blue, Green, Yellow, Purple, Pink, Cyan]
    default: Red
  - name: note
    type: text
    default: Auto marker
"""

from __future__ import annotations

from typing import Any, Dict


def run(resolve: Any, params: Dict[str, Any]) -> Dict[str, int]:
    """Add one marker for every clip on the configured track."""
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        raise RuntimeError("Open a project and select a timeline before running this script.")

    track_type = str(params["track_type"])
    track_index = int(params["track_index"])
    if track_index < 1 or track_index > timeline.GetTrackCount(track_type):
        raise ValueError("The selected track does not exist.")

    added = 0
    for clip in timeline.GetItemListInTrack(track_type, track_index) or []:
        was_added = timeline.AddMarker(
            clip.GetStart(),
            str(params["color"]),
            "Auto marker",
            str(params["note"]),
            1,
            "",
        )
        if was_added:
            added += 1

    return {"markers_added": added}
