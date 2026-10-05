"""Синхронный минимальный адаптер для API сценариев DaVinci Resolve."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess
import sys
from threading import RLock
from typing import Any, Iterable, Optional


@dataclass(frozen=True)
class ResolveStatus:
    """Сведения о подключении, доступные через endpoint состояния."""

    connected: bool
    version: str


@dataclass(frozen=True)
class ProjectDashboard:
    """Краткая сводка об открытом в Resolve проекте."""

    connected: bool
    project_name: str
    media_count: int
    timeline_name: str
    timeline_count: int
    missing_clip_count: int


@dataclass(frozen=True)
class OfflineMedia:
    """Недоступный элемент медиатеки и сведения о его расположении."""

    id: str
    name: str
    file_path: str
    folder_path: str


class ResolveBridge:
    """Подключаться к Resolve и предоставлять небольшой безопасный интерфейс состояния.

    Методы класса синхронны, потому что Python API DaVinci Resolve синхронен.
    Вызывайте их из пула потоков FastAPI, а не из его цикла событий.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._resolve: Optional[Any] = None

    def connect(self) -> bool:
        """Попытаться подключиться к запущенному экземпляру DaVinci Resolve."""
        with self._lock:
            if self._resolve is not None:
                return True

            try:
                import DaVinciResolveScript as resolve_script

                resolve = resolve_script.scriptapp("Resolve")
            except (ImportError, OSError, RuntimeError):
                return False

            if resolve is None:
                return False

            self._resolve = resolve
            return True

    def get_status(self) -> ResolveStatus:
        """Вернуть актуальное состояние, переподключившись при устаревшем дескрипторе."""
        with self._lock:
            if self._resolve is not None:
                version = self._read_version(self._resolve)
                if version is not None:
                    return ResolveStatus(connected=True, version=version)
                self._resolve = None

            if not self.connect() or self._resolve is None:
                return ResolveStatus(connected=False, version="")

            version = self._read_version(self._resolve)
            if version is None:
                self._resolve = None
                return ResolveStatus(connected=False, version="")

            return ResolveStatus(connected=True, version=version)

    def get_resolve(self) -> Optional[Any]:
        """Вернуть действующий дескриптор Resolve, переподключившись при необходимости."""
        status = self.get_status()
        if not status.connected:
            return None
        with self._lock:
            return self._resolve

    def get_project_dashboard(self) -> ProjectDashboard:
        """Вернуть метрики проекта или пустую сводку, когда Resolve недоступен."""
        with self._lock:
            if not self.get_status().connected or self._resolve is None:
                return _empty_dashboard()

            try:
                project_manager = self._resolve.GetProjectManager()
                project = project_manager.GetCurrentProject() if project_manager else None
                if project is None:
                    return ProjectDashboard(True, "", 0, "", 0, 0)

                media_count, missing_clip_count = _get_media_stats(project.GetMediaPool())
                timeline = project.GetCurrentTimeline()
                return ProjectDashboard(
                    connected=True,
                    project_name=str(project.GetName() or ""),
                    media_count=media_count,
                    timeline_name=str(timeline.GetName() or "") if timeline else "",
                    timeline_count=int(project.GetTimelineCount() or 0),
                    missing_clip_count=missing_clip_count,
                )
            except (AttributeError, OSError, RuntimeError, TypeError):
                self._resolve = None
                return _empty_dashboard()

    def get_offline_media(self) -> list[OfflineMedia]:
        """Вернуть недоступные элементы медиатеки текущего проекта."""
        with self._lock:
            if not self.get_status().connected or self._resolve is None:
                return []

            try:
                project_manager = self._resolve.GetProjectManager()
                project = project_manager.GetCurrentProject() if project_manager else None
                media_pool = project.GetMediaPool() if project else None
                return [
                    OfflineMedia(
                        id=_clip_identifier(folder_path, clip_index, clip),
                        name=str(clip.GetName() or "Без названия"),
                        file_path=_clip_file_path(clip),
                        folder_path=folder_path,
                    )
                    for _, clip, folder_path, clip_index in _media_pool_items(media_pool)
                    if _is_missing_clip(clip)
                ]
            except (AttributeError, OSError, RuntimeError, TypeError):
                self._resolve = None
                return []

    def reveal_offline_media(self, media_id: str) -> bool:
        """Открыть страницу Media и папку медиатеки для недоступного элемента."""
        with self._lock:
            if not self.get_status().connected or self._resolve is None:
                return False

            try:
                project_manager = self._resolve.GetProjectManager()
                project = project_manager.GetCurrentProject() if project_manager else None
                media_pool = project.GetMediaPool() if project else None
                for folder, clip, folder_path, clip_index in _media_pool_items(media_pool):
                    if _clip_identifier(folder_path, clip_index, clip) != media_id or not _is_missing_clip(clip):
                        continue
                    self._resolve.OpenPage("media")
                    if not media_pool.SetCurrentFolder(folder):
                        return False
                    _activate_resolve_window()
                    return True
                return False
            except (AttributeError, OSError, RuntimeError, TypeError):
                self._resolve = None
                return False

    @staticmethod
    def _read_version(resolve: Any) -> Optional[str]:
        """Прочитать версию Resolve и считать сбои API потерей подключения."""
        try:
            version = resolve.GetVersion()
        except (AttributeError, OSError, RuntimeError, TypeError):
            return None

        if isinstance(version, (list, tuple)):
            return ".".join(str(part) for part in version if str(part))
        if version is None:
            return None
        return str(version)


def _empty_dashboard() -> ProjectDashboard:
    return ProjectDashboard(False, "", 0, "", 0, 0)


def _activate_resolve_window() -> None:
    """Вывести окно Resolve на передний план в macOS, не прерывая переход в медиатеку."""
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
        pass


def _get_media_stats(media_pool: Any) -> tuple[int, int]:
    """Подсчитать элементы медиатеки и элементы с недоступным исходным файлом."""
    media_count = 0
    missing_clip_count = 0
    for _, clip, _, _ in _media_pool_items(media_pool):
        media_count += 1
        missing_clip_count += _is_missing_clip(clip)

    return media_count, missing_clip_count


def _media_pool_items(media_pool: Any) -> Iterable[tuple[Any, Any, str, int]]:
    """Перебрать клипы медиатеки вместе с их папкой и путём папки."""
    if media_pool is None:
        return

    root_folder = media_pool.GetRootFolder()
    if root_folder is None:
        return

    folders = [(root_folder, _folder_name(root_folder))]
    while folders:
        folder, folder_path = folders.pop()
        for clip_index, clip in enumerate(_as_iterable(folder.GetClipList())):
            yield folder, clip, folder_path, clip_index
        for subfolder in _as_iterable(folder.GetSubFolderList()):
            folders.append((subfolder, f"{folder_path} / {_folder_name(subfolder)}"))


def _folder_name(folder: Any) -> str:
    """Вернуть отображаемое имя папки медиатеки."""
    name = folder.GetName()
    return str(name) if name else "Без названия"


def _clip_identifier(folder_path: str, clip_index: int, clip: Any) -> str:
    """Создать идентификатор без GetUniqueId, недоступного в части версий Resolve."""
    key = "\0".join((folder_path, str(clip_index), str(clip.GetName() or ""), _clip_file_path(clip)))
    return sha256(key.encode("utf-8")).hexdigest()


def _clip_file_path(clip: Any) -> str:
    """Вернуть исходный путь к файлу без изменения его значения."""
    file_path = clip.GetClipProperty("File Path")
    return str(file_path) if file_path else ""


def _is_missing_clip(clip: Any) -> bool:
    """Считать исходник отсутствующим, только если Resolve сообщил абсолютный путь к файлу."""
    file_path = _clip_file_path(clip)
    if not file_path.strip():
        return False

    source = Path(file_path).expanduser()
    if not source.is_absolute():
        return False
    try:
        return not source.is_file()
    except OSError:
        return True


def _as_iterable(value: Any) -> list[Any]:
    """Нормализовать списки API Resolve, отсутствующие у пустой папки."""
    if value is None:
        return []
    if isinstance(value, dict):
        return list(value.values())
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    return []
