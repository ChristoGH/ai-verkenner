"""Source registry: load and validate `sources/sources.yaml`."""

from app.sources.registry import (
    RegistryLoadResult,
    SourceError,
    load_sources,
    load_sources_from_settings,
)

__all__ = [
    "load_sources",
    "load_sources_from_settings",
    "RegistryLoadResult",
    "SourceError",
]
