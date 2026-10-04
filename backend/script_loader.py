"""Discovery and validation for user-provided DaVinci Resolve scripts."""

from __future__ import annotations

import ast
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

import yaml

logger = logging.getLogger(__name__)

SCRIPTS_DIRECTORY = Path(__file__).parent / "scripts"
SUPPORTED_PARAM_TYPES = frozenset({"text", "number", "select", "bool", "textarea", "file"})
SCRIPT_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
PARAMETER_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class ScriptManifestError(ValueError):
    """Raised when a script does not contain a valid panel manifest."""


class ScriptNotFoundError(KeyError):
    """Raised when a requested script identifier is not registered."""


@dataclass(frozen=True)
class ScriptParameter:
    """A single user-configurable value declared in a script manifest."""

    name: str
    type: str
    default: Any
    options: Optional[List[Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "name": self.name,
            "type": self.type,
            "default": self.default,
        }
        if self.options is not None:
            result["options"] = self.options
        return result


@dataclass(frozen=True)
class ScriptDefinition:
    """The safe metadata required to present a script in the control panel."""

    id: str
    name: str
    description: str
    params: List[ScriptParameter]
    path: Path

    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "params": [parameter.as_dict() for parameter in self.params],
        }


class ScriptRegistry:
    """Registry populated by scanning the configured scripts directory at startup."""

    def __init__(self, scripts_directory: Path = SCRIPTS_DIRECTORY) -> None:
        self._scripts_directory = scripts_directory
        self._scripts: Dict[str, ScriptDefinition] = {}

    def load(self) -> None:
        """Discover scripts without importing or executing user-provided modules."""
        self._scripts = {}
        self._scripts_directory.mkdir(parents=True, exist_ok=True)

        for path in sorted(self._scripts_directory.glob("*.py")):
            if path.name.startswith("_"):
                continue

            try:
                script = self._load_script(path)
            except (OSError, SyntaxError, ScriptManifestError) as error:
                logger.warning("Skipped script %s: %s", path.name, error)
                continue

            if script.id in self._scripts:
                logger.warning("Skipped script %s: duplicate id %r", path.name, script.id)
                continue
            self._scripts[script.id] = script

    def list_scripts(self) -> List[ScriptDefinition]:
        """Return registered scripts ordered by their display name."""
        return sorted(self._scripts.values(), key=lambda script: script.name.casefold())

    def get_script(self, script_id: str) -> ScriptDefinition:
        """Return one script or raise a domain-specific not-found error."""
        try:
            return self._scripts[script_id]
        except KeyError as error:
            raise ScriptNotFoundError(script_id) from error

    @staticmethod
    def _load_script(path: Path) -> ScriptDefinition:
        script_id = path.stem
        if not SCRIPT_ID_PATTERN.fullmatch(script_id):
            raise ScriptManifestError(
                "filename must use lowercase letters, digits, and underscores "
                "and start with a letter"
            )

        source = path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(path))
        docstring = ast.get_docstring(module, clean=True)
        if docstring is None:
            raise ScriptManifestError("missing YAML manifest in module docstring")

        try:
            manifest = yaml.safe_load(docstring)
        except yaml.YAMLError as error:
            raise ScriptManifestError("manifest is not valid YAML") from error

        if not isinstance(manifest, Mapping):
            raise ScriptManifestError("manifest must be a YAML mapping")

        return ScriptDefinition(
            id=script_id,
            name=_required_string(manifest, "name"),
            description=_optional_string(manifest, "description"),
            params=_parse_parameters(manifest.get("params", [])),
            path=path,
        )


def _required_string(manifest: Mapping[str, Any], field_name: str) -> str:
    value = manifest.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ScriptManifestError("%r must be a non-empty string" % field_name)
    return value.strip()


def _optional_string(manifest: Mapping[str, Any], field_name: str) -> str:
    value = manifest.get(field_name, "")
    if not isinstance(value, str):
        raise ScriptManifestError("%r must be a string" % field_name)
    return value.strip()


def _parse_parameters(raw_parameters: Any) -> List[ScriptParameter]:
    if not isinstance(raw_parameters, Sequence) or isinstance(raw_parameters, (str, bytes)):
        raise ScriptManifestError("'params' must be a YAML list")

    names = set()
    parameters = []
    for index, raw_parameter in enumerate(raw_parameters, start=1):
        if not isinstance(raw_parameter, Mapping):
            raise ScriptManifestError("parameter #%d must be a mapping" % index)

        name = _required_string(raw_parameter, "name")
        if not PARAMETER_NAME_PATTERN.fullmatch(name):
            raise ScriptManifestError("parameter %r has an invalid name" % name)
        if name in names:
            raise ScriptManifestError("parameter %r is declared more than once" % name)
        names.add(name)

        parameter_type = _required_string(raw_parameter, "type")
        if parameter_type not in SUPPORTED_PARAM_TYPES:
            raise ScriptManifestError("parameter %r has unsupported type %r" % (name, parameter_type))

        default = raw_parameter.get("default", _default_for(parameter_type))
        _validate_value(default, "default for parameter %r" % name)

        options = raw_parameter.get("options")
        if parameter_type == "select":
            if not isinstance(options, list) or not options:
                raise ScriptManifestError("select parameter %r requires non-empty 'options'" % name)
            for option in options:
                _validate_value(option, "option for parameter %r" % name)
            if default not in options:
                raise ScriptManifestError("default for select parameter %r must be an option" % name)
        elif options is not None:
            raise ScriptManifestError("only select parameters may define 'options'")

        parameters.append(
            ScriptParameter(
                name=name,
                type=parameter_type,
                default=default,
                options=options if parameter_type == "select" else None,
            )
        )
    return parameters


def _default_for(parameter_type: str) -> Any:
    if parameter_type == "bool":
        return False
    if parameter_type == "number":
        return 0
    return ""


def _validate_value(value: Any, context: str) -> None:
    if not isinstance(value, (str, int, float, bool)) and value is not None:
        raise ScriptManifestError("%s must be a JSON scalar" % context)
