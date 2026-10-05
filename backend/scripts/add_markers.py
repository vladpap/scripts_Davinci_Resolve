"""
name: Добавить маркеры на таймлинию
description: Добавляет маркер в начале каждого клипа на выбранной дорожке. Тестовый скрипт.
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
    default: Автоматический маркер
"""

from __future__ import annotations

from typing import Any, Dict


def run(resolve: Any, params: Dict[str, Any]) -> Dict[str, int]:
    """Добавить по одному маркеру для каждого клипа на выбранной дорожке."""
    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        raise ValueError("Откройте проект и выберите таймлинию перед запуском скрипта.")

    track_type = str(params["track_type"])
    track_index = int(params["track_index"])
    if track_index < 1 or track_index > timeline.GetTrackCount(track_type):
        raise ValueError("Выбранная дорожка не существует.")

    timeline_start_frame = timeline.GetStartFrame()
    added = 0
    for clip in timeline.GetItemListInTrack(track_type, track_index) or []:
        was_added = timeline.AddMarker(
            clip.GetStart() - timeline_start_frame,
            str(params["color"]),
            "Автоматический маркер",
            str(params["note"]),
            1,
            "",
        )
        if was_added:
            added += 1

    return {"markers_added": added}
