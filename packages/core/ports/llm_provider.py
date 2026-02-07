"""LLM provider port definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Protocol


class LLMProvider(Protocol):
    """Port for structured extraction calls to LLM providers."""

    def parse_resume(
        self,
        *,
        resume_path: Path,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        """Parse a resume file and return a schema-shaped dictionary."""
