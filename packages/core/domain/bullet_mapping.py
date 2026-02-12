"""Data structures for mapping resume bullets to user attributes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class BulletContext:
    """A single bullet point with its context for LLM mapping."""

    bullet_index: int
    text: str
    occupation_title: str
    source: str  # "job" or "project"
    project_name: Optional[str]
    years: float


@dataclass
class AttributeMapping:
    """One attribute picked by the LLM for a bullet."""

    attribute_id: str
    relevance_score: float  # 0-1


@dataclass
class BulletAttributeMapping:
    """LLM output: which attributes a single bullet maps to."""

    bullet_index: int
    attributes: List[AttributeMapping] = field(default_factory=list)
