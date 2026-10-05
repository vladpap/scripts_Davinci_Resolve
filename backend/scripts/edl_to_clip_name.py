"""
name: Переименовать клипы таймлинии из EDL
description: Сверяет EDL с клипами видеодорожки по таймкодам и переименовывает совпавшие клипы из FROM CLIP NAME.
params:
  - name: edl_content
    type: textarea
    default: ""
  - name: edl_filename
    type: text
    default: ""
  - name: track_index
    type: number
    default: 1
  - name: strict_count_match
    type: bool
    default: false
  - name: clip_color
    type: select
    options: [Orange, Apricot, Yellow, Lime, Olive, Green, Teal, Navy, Blue, Purple, Violet, Pink, Tan, Beige, Brown, Chocolate]
    default: Orange
  - name: set_clip_color
    type: bool
    default: false
  - name: add_flag
    type: bool
    default: false
  - name: add_marker
    type: bool
    default: false
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence


EVENT_PATTERN = re.compile(
    r"^\s*\d+\s+\S+\s+V(?:\s+\S+)*\s+"
    r"(?P<source_in>\d{2}:\d{2}:\d{2}:\d{2})\s+"
    r"(?P<source_out>\d{2}:\d{2}:\d{2}:\d{2})\s+"
    r"(?P<record_in>\d{2}:\d{2}:\d{2}:\d{2})\s+"
    r"(?P<record_out>\d{2}:\d{2}:\d{2}:\d{2})\s*$"
)
CLIP_NAME_PATTERN = re.compile(r"^\*\s*FROM CLIP NAME:\s*(?P<name>.*)$", re.IGNORECASE)
MARKER_COLOR_BY_CLIP_COLOR = {
    "Orange": "Yellow",
    "Apricot": "Yellow",
    "Yellow": "Yellow",
    "Lime": "Green",
    "Olive": "Green",
    "Green": "Green",
    "Teal": "Cyan",
    "Navy": "Blue",
    "Blue": "Blue",
    "Purple": "Purple",
    "Violet": "Pink",
    "Pink": "Pink",
    "Tan": "Yellow",
    "Beige": "Yellow",
    "Brown": "Red",
    "Chocolate": "Red",
}


@dataclass(frozen=True)
class EdlEvent:
    """Таймкоды записи и название клипа, полученные из одного события CMX 3600."""

    record_in: str
    record_out: str
    name: str


@dataclass(frozen=True)
class TimelineClip:
    """Клип таймлинии с отображаемым именем и таймкодами записи."""

    item: Any
    name: str
    record_in: str
    record_out: str


def run(resolve: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Переименовать клипы дорожки только после совпадения всех таймкодов EDL."""
    edl_content = str(params["edl_content"])
    if not edl_content.strip():
        raise ValueError("Выберите EDL-файл перед запуском скрипта.")
    edl_filename = str(params["edl_filename"]).strip() or "выбранный EDL"

    track_index = int(params["track_index"])
    if track_index < 1:
        raise ValueError("Номер видеодорожки должен быть не меньше 1.")

    project_manager = resolve.GetProjectManager()
    project = project_manager.GetCurrentProject() if project_manager else None
    timeline = project.GetCurrentTimeline() if project else None
    if timeline is None:
        raise ValueError("Откройте проект и выберите таймлинию перед запуском скрипта.")
    if track_index > timeline.GetTrackCount("video"):
        raise ValueError("Выбранная видеодорожка не существует.")

    fps = _timeline_fps(timeline)
    edl_events = _parse_edl(edl_content)
    timeline_clips = _timeline_clips(timeline, track_index, fps)
    if not edl_events:
        raise ValueError("В EDL-файле не найдены видеособытия.")
    if not timeline_clips:
        raise ValueError(f"На видеодорожке V{track_index} не найдены клипы.")

    print(f"EDL: {len(edl_events)} видеособытий из {edl_filename}")
    print(f"Таймлиния: {len(timeline_clips)} клипов на V{track_index}, {fps:g} fps")

    pairs = _matching_pairs(edl_events, timeline_clips, bool(params["strict_count_match"]))
    _validate_timecodes(pairs)

    renamed = 0
    skipped = 0
    failed = 0
    clip_colors_set = 0
    flags_added = 0
    markers_added = 0
    annotation_failures = 0
    color = str(params["clip_color"])
    marker_color = MARKER_COLOR_BY_CLIP_COLOR[color]
    for event, clip in pairs:
        if not event.name:
            skipped += 1
            print(f"Пропущено пустое название из EDL: {clip.name}")
            continue

        if _rename_clip(clip.item, event.name):
            renamed += 1
            print(f"Переименовано: {clip.name} -> {event.name}")
        else:
            failed += 1
            print(f"Не удалось переименовать: {clip.name} -> {event.name}")

        if bool(params["set_clip_color"]):
            if clip.item.SetClipColor(color):
                clip_colors_set += 1
            else:
                annotation_failures += 1
        if bool(params["add_flag"]):
            if clip.item.AddFlag(marker_color):
                flags_added += 1
            else:
                annotation_failures += 1
        if bool(params["add_marker"]):
            marker_frame = clip.item.GetStart() - timeline.GetStartFrame()
            if timeline.AddMarker(marker_frame, marker_color, "Переименование из EDL", event.name, 1, "edl_to_clip_name"):
                markers_added += 1
            else:
                annotation_failures += 1

    _show_edit_page(resolve)
    return {
        "edl_events": len(edl_events),
        "timeline_clips": len(timeline_clips),
        "renamed": renamed,
        "skipped_empty_names": skipped,
        "rename_failures": failed,
        "clip_colors_set": clip_colors_set,
        "flags_added": flags_added,
        "markers_added": markers_added,
        "annotation_failures": annotation_failures,
    }


def _show_edit_page(resolve: Any) -> None:
    """Открыть Edit и активировать Resolve, не отменяя успешное переименование."""
    try:
        resolve.OpenPage("edit")
    except (AttributeError, OSError, RuntimeError, TypeError):
        print("Не удалось открыть страницу Edit.")

    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            ["osascript", "-e", 'tell application "DaVinci Resolve" to activate'],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        print("Не удалось вывести окно DaVinci Resolve на передний план.")


def _parse_edl(content: str) -> List[EdlEvent]:
    """Прочитать видеособытия и следующие за ними комментарии FROM CLIP NAME из CMX 3600."""
    events: List[EdlEvent] = []
    current_event_index: int | None = None

    for line in content.removeprefix("\ufeff").splitlines():
        event_match = EVENT_PATTERN.match(line)
        if event_match:
            events.append(
                EdlEvent(
                    record_in=event_match.group("record_in"),
                    record_out=event_match.group("record_out"),
                    name="",
                )
            )
            current_event_index = len(events) - 1
            continue

        clip_name_match = CLIP_NAME_PATTERN.match(line)
        if clip_name_match and current_event_index is not None:
            event = events[current_event_index]
            events[current_event_index] = EdlEvent(
                record_in=event.record_in,
                record_out=event.record_out,
                name=clip_name_match.group("name").strip(),
            )

    return events


def _timeline_clips(timeline: Any, track_index: int, fps: float) -> List[TimelineClip]:
    return [
        TimelineClip(
            item=item,
            name=str(item.GetName() or ""),
            record_in=_frames_to_timecode(int(item.GetStart()), fps),
            record_out=_frames_to_timecode(int(item.GetEnd()), fps),
        )
        for item in timeline.GetItemListInTrack("video", track_index) or []
    ]


def _matching_pairs(
    events: Sequence[EdlEvent],
    clips: Sequence[TimelineClip],
    strict_count_match: bool,
) -> List[tuple[EdlEvent, TimelineClip]]:
    if len(events) != len(clips):
        message = (
            "Количество склеек не совпадает: "
            f"в EDL — {len(events)}, на таймлинии — {len(clips)}. Проект не изменён."
        )
        if strict_count_match:
            raise ValueError(message)
        print(f"Предупреждение: {message} Проверяются первые {min(len(events), len(clips))} пар.")
    return list(zip(events, clips))


def _validate_timecodes(pairs: Sequence[tuple[EdlEvent, TimelineClip]]) -> None:
    mismatches = [
        (index + 1, event, clip)
        for index, (event, clip) in enumerate(pairs)
        if event.record_in != clip.record_in or event.record_out != clip.record_out
    ]
    if not mismatches:
        print("Все таймкоды записи совпадают. Начинается переименование.")
        return

    details = "\n".join(
        f"№{index}: EDL {event.record_in}-{event.record_out} не совпадает с "
        f"таймлинией {clip.record_in}-{clip.record_out} ({clip.name})"
        for index, event, clip in mismatches[:20]
    )
    if len(mismatches) > 20:
        details += f"\n…и ещё несовпадений: {len(mismatches) - 20}."
    raise ValueError(f"Таймлиния не изменена, потому что таймкоды не совпадают:\n{details}")


def _rename_clip(item: Any, new_name: str) -> bool:
    """Использовать API таймлинии, а при его отсутствии — элемент медиатеки."""
    try:
        set_name = item.SetName
    except AttributeError:
        set_name = None
    if callable(set_name) and set_name(new_name):
        return True

    media_pool_item = item.GetMediaPoolItem()
    return bool(media_pool_item and media_pool_item.SetClipProperty("Clip Name", new_name))


def _timeline_fps(timeline: Any) -> float:
    raw_fps = timeline.GetSetting("timelineFrameRate")
    try:
        fps = float(raw_fps)
    except (TypeError, ValueError) as error:
        raise ValueError("Не удалось определить частоту кадров таймлинии.") from error
    if fps <= 0 or not fps.is_integer():
        raise ValueError("Поддерживаются только целочисленные частоты кадров без режима пропуска кадров.")
    return fps


def _frames_to_timecode(frame_number: int, fps: float) -> str:
    if frame_number < 0:
        raise ValueError("Позиция кадра клипа на таймлинии не может быть отрицательной.")

    frame_rate = int(fps)
    total_seconds, frames = divmod(frame_number, frame_rate)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}"
