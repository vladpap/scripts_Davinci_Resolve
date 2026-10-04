"""Synchronous, minimal adapter for the DaVinci Resolve scripting API."""

from __future__ import annotations

from dataclasses import dataclass
from threading import RLock
from typing import Any, Optional


@dataclass(frozen=True)
class ResolveStatus:
    """The connection information exposed by the health endpoint."""

    connected: bool
    version: str


class ResolveBridge:
    """Connect to Resolve and provide a small, safe connection-status surface.

    Methods in this class are synchronous because the DaVinci Resolve Python API
    is synchronous. Call them from FastAPI's thread pool, never its event loop.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._resolve: Optional[Any] = None

    def connect(self) -> bool:
        """Try to connect to the currently running DaVinci Resolve instance."""
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
        """Return live status, reconnecting if an existing handle is stale."""
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
        """Return a live Resolve handle, reconnecting when needed."""
        status = self.get_status()
        if not status.connected:
            return None
        with self._lock:
            return self._resolve

    @staticmethod
    def _read_version(resolve: Any) -> Optional[str]:
        """Read Resolve's version and treat API failures as a lost connection."""
        try:
            version = resolve.GetVersion()
        except (AttributeError, OSError, RuntimeError):
            return None

        if isinstance(version, (list, tuple)):
            return ".".join(str(part) for part in version if str(part))
        if version is None:
            return None
        return str(version)
