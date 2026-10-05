"""Проверенное фоновое выполнение, состояния и логи скриптов Resolve."""

from __future__ import annotations

import contextlib
import importlib.util
import logging
import queue
import sys
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
    """Возникает, когда идентификатор запуска неизвестен."""


class RunCannotBeStoppedError(RuntimeError):
    """Возникает, когда выполняющийся синхронный скрипт нельзя безопасно прервать."""


class RunAlreadyActiveError(RuntimeError):
    """Возникает, когда другой скрипт ожидает запуска или выполняется."""


@dataclass(frozen=True)
class ScriptRun:
    """Публичные данные, возвращаемые после постановки скрипта в очередь."""

    id: str
    status: str


@dataclass
class _RunRecord:
    """Изменяемое внутреннее состояние принятого запуска скрипта."""

    id: str
    status: str = "queued"
    future: Optional[Future[None]] = None
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=1_000))
    subscribers: List[queue.Queue[Dict[str, Any]]] = field(default_factory=list)


class ScriptRunner:
    """Выполнять не более одного скрипта Resolve и предоставлять его состояние."""

    def __init__(self, resolve_bridge: ResolveBridge) -> None:
        self._resolve_bridge = resolve_bridge
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="resolve-script")
        self._runs: Dict[str, _RunRecord] = {}
        self._lock = RLock()

    def submit(self, script: ScriptDefinition, raw_params: Mapping[str, Any]) -> ScriptRun:
        """Принять скрипт, только если другой не ожидает запуска и не выполняется."""
        params = validate_params(script, raw_params)
        with self._lock:
            if any(record.status not in TERMINAL_STATUSES for record in self._runs.values()):
                raise RunAlreadyActiveError("Другой скрипт уже выполняется. Дождитесь его завершения перед новым запуском.")

            run_id = uuid4().hex
            record = _RunRecord(id=run_id)
            self._runs[run_id] = record
        self._publish(record, "status", status="queued")

        future = self._executor.submit(self._execute, record, script.path, params)
        with self._lock:
            record.future = future
        return ScriptRun(id=run_id, status="queued")

    def stop(self, run_id: str) -> ScriptRun:
        """Отменить ожидающий запуск; активный Python-код нельзя безопасно остановить принудительно."""
        with self._lock:
            record = self._get_record(run_id)
            future = record.future
            status = record.status

        if status in TERMINAL_STATUSES:
            return ScriptRun(id=run_id, status=status)
        if status == "running":
            raise RunCannotBeStoppedError(
                "Скрипт уже выполняется и не может быть безопасно прерван. "
                "Он завершится штатно."
            )
        if future is not None and future.cancel():
            self._publish(record, "status", status="cancelled")
            return ScriptRun(id=run_id, status="cancelled")

        raise RunCannotBeStoppedError("Скрипт уже запускается и не может быть безопасно прерван.")

    def subscribe(self, run_id: str) -> Tuple[List[Dict[str, Any]], queue.Queue[Dict[str, Any]]]:
        """Вернуть историю событий и очередь для всех будущих событий запуска."""
        with self._lock:
            record = self._get_record(run_id)
            subscriber: queue.Queue[Dict[str, Any]] = queue.Queue()
            record.subscribers.append(subscriber)
            return list(record.events), subscriber

    def unsubscribe(self, run_id: str, subscriber: queue.Queue[Dict[str, Any]]) -> None:
        """Удалить подписку WebSocket после отключения."""
        with self._lock:
            record = self._runs.get(run_id)
            if record is not None and subscriber in record.subscribers:
                record.subscribers.remove(subscriber)

    def shutdown(self) -> None:
        """Прекратить принимать новые задачи при штатном завершении приложения."""
        self._executor.shutdown(wait=False, cancel_futures=False)

    def _execute(self, record: _RunRecord, script_path: Path, params: Dict[str, Any]) -> None:
        self._publish(record, "status", status="running")
        resolve = self._resolve_bridge.get_resolve()
        if resolve is None:
            self._publish(record, "log", level="error", message="DaVinci Resolve недоступен.")
            self._publish(record, "status", status="error")
            return

        stream = _RunLogStream(lambda level, message: self._publish(record, "log", level=level, message=message))
        try:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                module = _load_module(script_path, record.id)
                run = getattr(module, "run", None)
                if not callable(run):
                    raise RuntimeError("Скрипт должен определять вызываемую функцию run(resolve, params).")
                result = run(resolve, params)
            stream.flush()
            self._publish(record, "result", result=repr(result)[:2_000])
            self._publish(record, "status", status="success")
        except (FileNotFoundError, ValueError) as error:
            stream.flush()
            self._publish(record, "log", level="error", message=f"Ошибка: {error}")
            self._publish(record, "status", status="error")
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
    """Построчно буферизуемый поток для скриптов с вызовами ``print``."""

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
    """Объединить значения по умолчанию с вводом и отклонить неизвестные или неверно типизированные параметры."""
    parameter_names = {parameter.name for parameter in script.params}
    unknown_names = set(raw_params).difference(parameter_names)
    if unknown_names:
        raise ScriptManifestError("неизвестные параметры: %s" % ", ".join(sorted(unknown_names)))

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
        raise ScriptManifestError("параметр %r имеет недопустимое значение" % name)


def _load_module(script_path: Path, run_id: str) -> Any:
    module_name = "resolve_panel_script_%s" % run_id
    module_spec = importlib.util.spec_from_file_location(module_name, script_path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("Не удалось загрузить модуль скрипта.")

    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    try:
        module_spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module
