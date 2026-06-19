"""Load and validate the curated source registry.

The headline guarantee: **a malformed registry never crashes the app.** Every problem (a missing
file, unparseable YAML, the wrong top-level shape, or an invalid entry) is collected into a
`SourceError` that names the file, the offending entry, and the reason — and the valid entries are
still returned. The caller decides what to do with the errors (log them, surface a count).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.source import Source

logger = logging.getLogger(__name__)


@dataclass
class SourceError:
    """A single, localised registry problem — clear enough to fix the YAML by hand."""

    file: str
    entry: str  # a human pointer: "entry #3", "entry #3 (OpenAI Blog)", or "file"
    reason: str

    def __str__(self) -> str:  # pragma: no cover - trivial formatting
        return f"{self.file}: {self.entry}: {self.reason}"


@dataclass
class RegistryLoadResult:
    """The outcome of a load: the valid sources plus every problem found."""

    sources: list[Source] = field(default_factory=list)
    errors: list[SourceError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _condense(exc: ValidationError) -> str:
    """Turn a Pydantic error into a short, single-line reason."""
    parts = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err["loc"]) or "(entry)"
        parts.append(f"{loc}: {err['msg']}")
    return "; ".join(parts)


def load_sources(path: Path) -> RegistryLoadResult:
    """Parse, validate, and return the registry at `path`, failing safely.

    Never raises for bad content: file-not-found, malformed YAML, the wrong top-level shape, and
    invalid entries all become `SourceError`s on the result.
    """
    result = RegistryLoadResult()
    file_label = str(path)

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.errors.append(SourceError(file_label, "file", "registry file not found"))
        return result
    except OSError as exc:
        result.errors.append(SourceError(file_label, "file", f"could not read file: {exc}"))
        return result

    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        result.errors.append(SourceError(file_label, "file", f"invalid YAML: {exc}"))
        return result

    if data is None:
        result.errors.append(SourceError(file_label, "file", "registry is empty"))
        return result
    if not isinstance(data, dict) or "sources" not in data:
        result.errors.append(
            SourceError(file_label, "file", "expected a top-level 'sources:' list")
        )
        return result

    entries = data["sources"]
    if not isinstance(entries, list):
        result.errors.append(
            SourceError(file_label, "sources", "'sources' must be a list of entries")
        )
        return result

    for index, entry in enumerate(entries):
        pointer = f"entry #{index}"
        if not isinstance(entry, dict):
            result.errors.append(
                SourceError(file_label, pointer, "entry must be a mapping (key: value)")
            )
            continue
        # Enrich the pointer with the name if one is present — easier to find in the file.
        name = entry.get("name")
        if isinstance(name, str) and name.strip():
            pointer = f"entry #{index} ({name})"
        try:
            result.sources.append(Source(**entry))
        except ValidationError as exc:
            result.errors.append(SourceError(file_label, pointer, _condense(exc)))
        except TypeError as exc:  # e.g. non-string keys in the mapping
            result.errors.append(SourceError(file_label, pointer, f"invalid entry: {exc}"))

    return result


def load_sources_from_settings() -> RegistryLoadResult:
    """Load the registry from the configured `SOURCES_FILE`, logging any problems."""
    result = load_sources(settings.sources_file)
    for error in result.errors:
        logger.warning("source registry problem — %s", error)
    return result
