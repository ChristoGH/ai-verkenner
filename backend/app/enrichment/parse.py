"""Parse + repair LLM output into validated payloads (M4).

Models don't always return clean JSON: they wrap it in prose, fence it in ```json blocks, or add
a trailing comment. `extract_json` pulls the first balanced JSON object out of the text; the typed
parsers then validate it with Pydantic. Any failure raises `EnrichmentParseError`, which the
enricher catches and degrades from (rule-based fallback) — it never crashes a run.
"""

from __future__ import annotations

import json

from app.schemas.enrichment import (
    ClassifyResult,
    GraphExtractResult,
    SummariseResult,
    WeakSignalResult,
)


class EnrichmentParseError(ValueError):
    """Raised when LLM output cannot be parsed/validated into the expected shape."""


def extract_json(text: str) -> dict:
    """Return the first balanced JSON object in `text`, tolerating fences and surrounding prose."""
    if text is None:
        raise EnrichmentParseError("no text to parse")

    cleaned = text.strip()
    # Strip a leading ```json / ``` fence if present.
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
        if cleaned.endswith("```"):
            cleaned = cleaned[: -3]
        cleaned = cleaned.strip()

    # Fast path: the whole thing is JSON.
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Otherwise scan for the first balanced {...} block (string-aware).
    start = cleaned.find("{")
    while start != -1:
        depth = 0
        in_string = False
        escape = False
        for i in range(start, len(cleaned)):
            ch = cleaned[i]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = cleaned[start : i + 1]
                    try:
                        obj = json.loads(candidate)
                        if isinstance(obj, dict):
                            return obj
                    except json.JSONDecodeError:
                        break  # try the next "{"
        start = cleaned.find("{", start + 1)

    raise EnrichmentParseError("no valid JSON object found in output")


def _validate(model, payload: dict):
    from pydantic import ValidationError

    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise EnrichmentParseError(f"{model.__name__} validation failed: {exc}") from exc


def parse_classify(text: str) -> ClassifyResult:
    return _validate(ClassifyResult, extract_json(text))


def parse_summarise(text: str) -> SummariseResult:
    return _validate(SummariseResult, extract_json(text))


def parse_weak_signal(text: str) -> WeakSignalResult:
    return _validate(WeakSignalResult, extract_json(text))


def parse_graph(text: str) -> GraphExtractResult:
    return _validate(GraphExtractResult, extract_json(text))
