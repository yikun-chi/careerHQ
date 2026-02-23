"""LLM provider port definitions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, List, Mapping, Protocol


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

    def map_bullets_to_attributes(
        self,
        *,
        bullet_texts: List[str],
        attribute_catalog_text: str,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        """Map numbered bullet texts to user attributes.

        Returns a schema-shaped dictionary with attribute mappings.
        """

    def refine_career_matches(
        self,
        *,
        matches: List[Mapping[str, Any]],
        answers: List[Mapping[str, str]],
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        """Refine matched occupations with follow-up user answers."""
