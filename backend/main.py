"""FastAPI-приложение локальной панели управления DaVinci Resolve."""

from __future__ import annotations

import asyncio
import logging
import queue
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .resolve_bridge import OfflineMedia, ProjectDashboard, ResolveBridge
from .runner import RunAlreadyActiveError, RunCannotBeStoppedError, RunNotFoundError, ScriptRunner, TERMINAL_STATUSES
from .script_loader import ScriptManifestError, ScriptNotFoundError, ScriptRegistry

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Публичный ответ API о состоянии подключения."""

    resolve_connected: bool
    version: str


class ProjectDashboardResponse(BaseModel):
    """Метрики, отображаемые в сводке активного проекта."""

    resolve_connected: bool
    project_name: str
    media_count: int
    timeline_name: str
    timeline_count: int
    missing_clip_count: int


class OfflineMediaResponse(BaseModel):
    """Недоступный элемент медиатеки для отображения в панели."""

    id: str
    name: str
    file_path: str
    folder_path: str


class RunScriptRequest(BaseModel):
    """Параметры из динамически созданной формы frontend."""

    params: Dict[str, Any] = Field(default_factory=dict)


class RunScriptResponse(BaseModel):
    """Публичный ответ после принятия скрипта для фонового выполнения."""

    run_id: str
    status: str


class StopRunResponse(BaseModel):
    """Публичный ответ после попытки остановить запуск."""

    run_id: str
    status: str


resolve_bridge = ResolveBridge()
script_registry = ScriptRegistry()
script_runner = ScriptRunner(resolve_bridge)

app = FastAPI(title="Панель управления DaVinci Resolve", version="0.1.0")


@app.on_event("startup")
async def connect_to_resolve() -> None:
    """Выполнить первичное подключение, не задерживая цикл событий FastAPI."""
    connected = await run_in_threadpool(resolve_bridge.connect)
    if connected:
        logger.info("Подключено к DaVinci Resolve.")
    else:
        logger.info("DaVinci Resolve недоступен; подключение будет повторено.")

    await run_in_threadpool(script_registry.load)
    logger.info("Загружено скриптов: %d.", len(script_registry.list_scripts()))


@app.on_event("shutdown")
async def shutdown_runner() -> None:
    """Освободить рабочий поток при штатном завершении приложения."""
    script_runner.shutdown()


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Вернуть текущее состояние подключения к DaVinci Resolve."""
    status = await run_in_threadpool(resolve_bridge.get_status)
    return HealthResponse(
        resolve_connected=status.connected,
        version=status.version,
    )


@app.get("/api/project-dashboard", response_model=ProjectDashboardResponse)
async def project_dashboard() -> ProjectDashboardResponse:
    """Вернуть сводку по текущему проекту для панели."""
    dashboard = await run_in_threadpool(resolve_bridge.get_project_dashboard)
    return _project_dashboard_response(dashboard)


@app.get("/api/offline-media", response_model=list[OfflineMediaResponse])
async def offline_media() -> list[OfflineMediaResponse]:
    """Вернуть список недоступных элементов медиатеки текущего проекта."""
    status = await run_in_threadpool(resolve_bridge.get_status)
    if not status.connected:
        raise HTTPException(status_code=503, detail="DaVinci Resolve не подключён.")
    media = await run_in_threadpool(resolve_bridge.get_offline_media)
    return [_offline_media_response(item) for item in media]


@app.post("/api/offline-media/{media_id}/reveal")
async def reveal_offline_media(media_id: str) -> dict[str, bool]:
    """Открыть страницу Media и папку недоступного элемента медиатеки."""
    status = await run_in_threadpool(resolve_bridge.get_status)
    if not status.connected:
        raise HTTPException(status_code=503, detail="DaVinci Resolve не подключён.")
    was_revealed = await run_in_threadpool(resolve_bridge.reveal_offline_media, media_id)
    if not was_revealed:
        raise HTTPException(status_code=404, detail="Недоступный элемент больше не найден в медиатеке.")
    return {"revealed": True}


@app.get("/api/scripts")
async def list_scripts() -> list[dict]:
    """Вернуть метаданные всех скриптов, найденных при запуске приложения."""
    return [script.as_dict() for script in script_registry.list_scripts()]


@app.get("/api/scripts/{script_id}")
async def get_script(script_id: str) -> dict:
    """Вернуть метаданные одного найденного скрипта."""
    try:
        return script_registry.get_script(script_id).as_dict()
    except ScriptNotFoundError as error:
        raise HTTPException(status_code=404, detail="Скрипт не найден.") from error


@app.post("/api/scripts/{script_id}/run", response_model=RunScriptResponse, status_code=202)
async def run_script(script_id: str, request: RunScriptRequest) -> RunScriptResponse:
    """Запустить скрипт в рабочем потоке, если другой скрипт не выполняется."""
    try:
        script = script_registry.get_script(script_id)
    except ScriptNotFoundError as error:
        raise HTTPException(status_code=404, detail="Скрипт не найден.") from error

    status = await run_in_threadpool(resolve_bridge.get_status)
    if not status.connected:
        raise HTTPException(status_code=503, detail="DaVinci Resolve не подключён.")

    try:
        run = script_runner.submit(script, request.params)
    except ScriptManifestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RunAlreadyActiveError as error:
        raise HTTPException(status_code=409, detail="Другой скрипт уже выполняется. Дождитесь его завершения.") from error

    return RunScriptResponse(run_id=run.id, status=run.status)


@app.post("/api/runs/{run_id}/stop", response_model=StopRunResponse)
async def stop_run(run_id: str) -> StopRunResponse:
    """Отменить ожидающий запуск; выполняющиеся синхронные скрипты нельзя безопасно остановить принудительно."""
    try:
        run = script_runner.stop(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Запуск не найден.") from error
    except RunCannotBeStoppedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return StopRunResponse(run_id=run.id, status=run.status)


@app.websocket("/ws/logs/{run_id}")
async def stream_run_logs(websocket: WebSocket, run_id: str) -> None:
    """Передавать сохранённые и новые события одного запуска скрипта."""
    await websocket.accept()
    try:
        history, subscriber = script_runner.subscribe(run_id)
    except RunNotFoundError:
        await websocket.close(code=4404, reason="Запуск не найден.")
        return

    try:
        for event in history:
            await websocket.send_json(event)
        if history and history[-1].get("status") in TERMINAL_STATUSES:
            await websocket.close()
            return

        while True:
            try:
                event = await asyncio.to_thread(subscriber.get, True, 1.0)
            except queue.Empty:
                continue
            await websocket.send_json(event)
            if event.get("status") in TERMINAL_STATUSES:
                await websocket.close()
                return
    except WebSocketDisconnect:
        pass
    finally:
        script_runner.unsubscribe(run_id, subscriber)


def _project_dashboard_response(dashboard: ProjectDashboard) -> ProjectDashboardResponse:
    return ProjectDashboardResponse(
        resolve_connected=dashboard.connected,
        project_name=dashboard.project_name,
        media_count=dashboard.media_count,
        timeline_name=dashboard.timeline_name,
        timeline_count=dashboard.timeline_count,
        missing_clip_count=dashboard.missing_clip_count,
    )


def _offline_media_response(media: OfflineMedia) -> OfflineMediaResponse:
    return OfflineMediaResponse(
        id=media.id,
        name=media.name,
        file_path=media.file_path,
        folder_path=media.folder_path,
    )
