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
        feedback: str = "",
    ) -> Mapping[str, Any]:
        """Refine matched occupations with follow-up user answers and feedback."""

    def generate_career_roadmap(
        self,
        *,
        user_text: str,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        """Generate a career roadmap from current role to target occupation."""

    def validate_and_fix_roadmap_links(
        self,
        *,
        resources: List[Mapping[str, Any]],
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        """Validate URL plausibility and suggest replacements for invalid ones.

        Returns dict with keys:
            - all_valid (bool)
            - results (list of {url, is_valid, reason, suggested_url})
        """
