"""FastAPI application for the local DaVinci Resolve control panel."""

from __future__ import annotations

import asyncio
import logging
import queue
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .resolve_bridge import ResolveBridge
from .runner import RunAlreadyActiveError, RunCannotBeStoppedError, RunNotFoundError, ScriptRunner, TERMINAL_STATUSES
from .script_loader import ScriptManifestError, ScriptNotFoundError, ScriptRegistry

logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    """Public health API response."""

    resolve_connected: bool
    version: str


class RunScriptRequest(BaseModel):
    """Parameters supplied by the dynamically generated frontend form."""

    params: Dict[str, Any] = Field(default_factory=dict)


class RunScriptResponse(BaseModel):
    """Public response after a script is accepted for background execution."""

    run_id: str
    status: str


class StopRunResponse(BaseModel):
    """Public response after attempting to stop a run."""

    run_id: str
    status: str


resolve_bridge = ResolveBridge()
script_registry = ScriptRegistry()
script_runner = ScriptRunner(resolve_bridge)

app = FastAPI(title="DaVinci Resolve Control Panel", version="0.1.0")


@app.on_event("startup")
async def connect_to_resolve() -> None:
    """Attempt an initial connection without delaying the FastAPI event loop."""
    connected = await run_in_threadpool(resolve_bridge.connect)
    if connected:
        logger.info("Connected to DaVinci Resolve.")
    else:
        logger.info("DaVinci Resolve is not available; connection will be retried.")

    await run_in_threadpool(script_registry.load)
    logger.info("Loaded %d script(s).", len(script_registry.list_scripts()))


@app.on_event("shutdown")
async def shutdown_runner() -> None:
    """Release the runner's worker thread during controlled application shutdown."""
    script_runner.shutdown()


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report the live DaVinci Resolve connection status."""
    status = await run_in_threadpool(resolve_bridge.get_status)
    return HealthResponse(
        resolve_connected=status.connected,
        version=status.version,
    )


@app.get("/api/scripts")
async def list_scripts() -> list[dict]:
    """Return metadata for all scripts discovered during application startup."""
    return [script.as_dict() for script in script_registry.list_scripts()]


@app.get("/api/scripts/{script_id}")
async def get_script(script_id: str) -> dict:
    """Return metadata for a single discovered script."""
    try:
        return script_registry.get_script(script_id).as_dict()
    except ScriptNotFoundError as error:
        raise HTTPException(status_code=404, detail="Script not found.") from error


@app.post("/api/scripts/{script_id}/run", response_model=RunScriptResponse, status_code=202)
async def run_script(script_id: str, request: RunScriptRequest) -> RunScriptResponse:
    """Start a script in the worker thread when no other script is active."""
    try:
        script = script_registry.get_script(script_id)
    except ScriptNotFoundError as error:
        raise HTTPException(status_code=404, detail="Script not found.") from error

    status = await run_in_threadpool(resolve_bridge.get_status)
    if not status.connected:
        raise HTTPException(status_code=503, detail="DaVinci Resolve is not connected.")

    try:
        run = script_runner.submit(script, request.params)
    except ScriptManifestError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RunAlreadyActiveError as error:
        raise HTTPException(status_code=409, detail="Другой скрипт уже выполняется. Дождитесь его завершения.") from error

    return RunScriptResponse(run_id=run.id, status=run.status)


@app.post("/api/runs/{run_id}/stop", response_model=StopRunResponse)
async def stop_run(run_id: str) -> StopRunResponse:
    """Cancel a queued run; active synchronous scripts cannot be force-stopped safely."""
    try:
        run = script_runner.stop(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail="Run not found.") from error
    except RunCannotBeStoppedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return StopRunResponse(run_id=run.id, status=run.status)


@app.websocket("/ws/logs/{run_id}")
async def stream_run_logs(websocket: WebSocket, run_id: str) -> None:
    """Stream recorded and live events for one script execution."""
    await websocket.accept()
    try:
        history, subscriber = script_runner.subscribe(run_id)
    except RunNotFoundError:
        await websocket.close(code=4404, reason="Run not found.")
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
