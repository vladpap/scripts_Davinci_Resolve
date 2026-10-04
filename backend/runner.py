"""Validated background execution, lifecycle state, and logs for Resolve scripts."""

from __future__ import annotations

import contextlib
import importlib.util
import logging
import queue
import traceback
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from typing import Any, Deque, Dict, List, Mapping, Optional, Tuple
from uuid import uuid4

from .resolve_bridge import ResolveBridge
from .script_loader import ScriptDefinition, ScriptManifestError

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = frozenset({"cancelled", "error", "success"})


class RunNotFoundError(KeyError):
    """Raised when a run identifier is unknown."""


class RunCannotBeStoppedError(RuntimeError):
    """Raised when a running synchronous script cannot be interrupted safely."""


class RunAlreadyActiveError(RuntimeError):
    """Raised when another script is queued or running."""


@dataclass(frozen=True)
class ScriptRun:
    """The public data returned when a script has been queued."""

    id: str
    status: str


@dataclass
class _RunRecord:
    """Mutable internal state for an accepted script execution."""

    id: str
    status: str = "queued"
    future: Optional[Future[None]] = None
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=1_000))
    subscribers: List[queue.Queue[Dict[str, Any]]] = field(default_factory=list)


class ScriptRunner:
    """Run at most one Resolve script at a time and make its lifecycle observable."""

    def __init__(self, resolve_bridge: ResolveBridge) -> None:
        self._resolve_bridge = resolve_bridge
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="resolve-script")
        self._runs: Dict[str, _RunRecord] = {}
        self._lock = RLock()

    def submit(self, script: ScriptDefinition, raw_params: Mapping[str, Any]) -> ScriptRun:
        """Accept a script only when no other script is queued or running."""
        params = validate_params(script, raw_params)
        with self._lock:
            if any(record.status not in TERMINAL_STATUSES for record in self._runs.values()):
                raise RunAlreadyActiveError("A script is already running. Wait for it to finish before starting another one.")

            run_id = uuid4().hex
            record = _RunRecord(id=run_id)
            self._runs[run_id] = record
        self._publish(record, "status", status="queued")

        future = self._executor.submit(self._execute, record, script.path, params)
        with self._lock:
            record.future = future
        return ScriptRun(id=run_id, status="queued")

    def stop(self, run_id: str) -> ScriptRun:
        """Cancel a queued execution; active Python code cannot be force-stopped safely."""
        with self._lock:
            record = self._get_record(run_id)
            future = record.future
            status = record.status

        if status in TERMINAL_STATUSES:
            return ScriptRun(id=run_id, status=status)
        if status == "running":
            raise RunCannotBeStoppedError(
                "The script is already running and cannot be safely interrupted. "
                "It will finish normally."
            )
        if future is not None and future.cancel():
            self._publish(record, "status", status="cancelled")
            return ScriptRun(id=run_id, status="cancelled")

        raise RunCannotBeStoppedError("The script is already starting and cannot be safely interrupted.")

    def subscribe(self, run_id: str) -> Tuple[List[Dict[str, Any]], queue.Queue[Dict[str, Any]]]:
        """Return replayable events and a queue for all future run events."""
        with self._lock:
            record = self._get_record(run_id)
            subscriber: queue.Queue[Dict[str, Any]] = queue.Queue()
            record.subscribers.append(subscriber)
            return list(record.events), subscriber

    def unsubscribe(self, run_id: str, subscriber: queue.Queue[Dict[str, Any]]) -> None:
        """Remove a WebSocket subscription after disconnect."""
        with self._lock:
            record = self._runs.get(run_id)
            if record is not None and subscriber in record.subscribers:
                record.subscribers.remove(subscriber)

    def shutdown(self) -> None:
        """Stop accepting queued work during controlled application shutdown."""
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _execute(self, record: _RunRecord, script_path: Path, params: Dict[str, Any]) -> None:
        self._publish(record, "status", status="running")
        resolve = self._resolve_bridge.get_resolve()
        if resolve is None:
            self._publish(record, "log", level="error", message="DaVinci Resolve is unavailable.")
            self._publish(record, "status", status="error")
            return

        stream = _RunLogStream(lambda level, message: self._publish(record, "log", level=level, message=message))
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                module = _load_module(script_path, record.id)
                run = getattr(module, "run", None)
                if not callable(run):
                    raise RuntimeError("The script must define a callable run(resolve, params) function.")
                result = run(resolve, params)
            stream.flush()
            self._publish(record, "result", result=repr(result)[:2_000])
            self._publish(record, "status", status="success")
        except Exception:
            stream.flush()
            error = traceback.format_exc()
            self._publish(record, "log", level="error", message=error)
            self._publish(record, "status", status="error")

    def _get_record(self, run_id: str) -> _RunRecord:
        try:
            return self._runs[run_id]
        except KeyError as error:
            raise RunNotFoundError(run_id) from error

    def _publish(self, record: _RunRecord, event_type: str, **payload: Any) -> None:
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **payload,
        }
        with self._lock:
            if event_type == "status":
                record.status = str(payload["status"])
            record.events.append(event)
            for subscriber in list(record.subscribers):
                subscriber.put(event)


class _RunLogStream:
    """Line-buffered stream used by scripts that call ``print`` during a run."""

    def __init__(self, publish: Any) -> None:
        self._publish = publish
        self._buffer = ""

    def write(self, text: str) -> int:
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line:
                self._publish("info", line)
        return len(text)

    def flush(self) -> None:
        if self._buffer:
            self._publish("info", self._buffer)
            self._buffer = ""


def validate_params(script: ScriptDefinition, raw_params: Mapping[str, Any]) -> Dict[str, Any]:
    """Merge manifest defaults and reject undeclared or incorrectly typed input."""
    parameter_names = {parameter.name for parameter in script.params}
    unknown_names = set(raw_params).difference(parameter_names)
    if unknown_names:
        raise ScriptManifestError("unknown parameter(s): %s" % ", ".join(sorted(unknown_names)))

    params: Dict[str, Any] = {}
    for parameter in script.params:
        value = raw_params.get(parameter.name, parameter.default)
        _validate_parameter_value(parameter.name, parameter.type, value, parameter.options)
        params[parameter.name] = value
    return params


def _validate_parameter_value(
    name: str,
    parameter_type: str,
    value: Any,
    options: Optional[list[Any]],
) -> None:
    if parameter_type in {"text", "textarea", "file"}:
        valid = isinstance(value, str)
    elif parameter_type == "number":
        valid = isinstance(value, (int, float)) and not isinstance(value, bool)
    elif parameter_type == "bool":
        valid = isinstance(value, bool)
    elif parameter_type == "select":
        valid = options is not None and value in options
    else:
        valid = False

    if not valid:
        raise ScriptManifestError("parameter %r has an invalid value" % name)


def _load_module(script_path: Path, run_id: str) -> Any:
    module_name = "resolve_panel_script_%s" % run_id
    module_spec = importlib.util.spec_from_file_location(module_name, script_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("Unable to load script module.")

    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module
