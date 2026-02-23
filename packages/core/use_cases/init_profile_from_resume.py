"""Initialize a user profile from a parsed resume.

Bridges resume parsing output to the user attribute system:
1. Occupation-based update: loads Occupation by occupation_id, calls add_job_experience
2. Bullet-point-based update: sends bullets to LLM, maps them to user attributes
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from packages.core.domain.bullet_mapping import (
    AttributeMapping,
    BulletAttributeMapping,
    BulletContext,
)
from packages.core.domain.occupation_class import Occupation
from packages.core.domain.resume import ParsedResume
from packages.core.domain.user_class import User, UserAttributeTemplate
from packages.core.domain.user_initialize import get_attribute_template_registry
from packages.core.domain.user_service import (
    add_job_experience,
    update_attributes_from_bullet_mappings,
)
from packages.core.ports.llm_provider import LLMProvider


@dataclass
class ProfileInitResult:
    """Result of initializing a profile from a resume."""

    jobs_added: int = 0
    bullets_mapped: int = 0
    attributes_updated: int = 0
    skipped_occupations: List[str] = field(default_factory=list)


BULLET_MAPPING_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["mappings"],
    "properties": {
        "mappings": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["bullet_index", "attributes"],
                "properties": {
                    "bullet_index": {"type": "integer"},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["attribute_id", "relevance_score"],
                            "properties": {
                                "attribute_id": {"type": "string"},
                                "relevance_score": {"type": "number"},
                            },
                        },
                    },
                },
            },
        },
    },
}

_BULLET_MAPPING_INSTRUCTIONS_TEMPLATE = """You map resume bullet points to user attributes.

## Rules
- For each bullet, pick up to 3 attributes from the catalog below that the bullet demonstrates.
- Set relevance_score between 0 and 1:
  - 1.0 = bullet is a direct demonstration of this attribute
  - 0.5 = bullet is moderately related
  - 0.1 = bullet is tangentially related
- Use the exact attribute_id from the catalog. Do not invent IDs.
- If a bullet does not relate to any attribute, return an empty attributes array for it.
- Return valid JSON matching the provided schema.

## Attribute catalog
{attribute_catalog}
"""


def _collect_bullets(parsed_resume: ParsedResume) -> List[BulletContext]:
    """Flatten all bullets from jobs and projects into a numbered list."""
    bullets: List[BulletContext] = []
    index = 0

    for job in parsed_resume.jobs:
        for text in job.bullet_points:
            bullets.append(
                BulletContext(
                    bullet_index=index,
                    text=text,
                    occupation_title=job.occupation_title,
                    source="job",
                    project_name=None,
                    years=job.years_of_experience,
                )
            )
            index += 1

        for project in job.projects:
            for text in project.bullet_points:
                bullets.append(
                    BulletContext(
                        bullet_index=index,
                        text=text,
                        occupation_title=job.occupation_title,
                        source="project",
                        project_name=project.project_name,
                        years=1.0,
                    )
                )
                index += 1

    return bullets


def _build_catalog_text(
    templates: Dict[str, UserAttributeTemplate],
) -> str:
    """Format leaf attribute templates as 'id | name | description' lines."""
    lines: List[str] = []
    for attr_id in sorted(templates):
        tmpl = templates[attr_id]
        desc = tmpl.description or ""
        lines.append(f"{attr_id} | {tmpl.attribute_name} | {desc}")
    return "\n".join(lines)


def _parse_mapping_response(
    response: Mapping[str, Any],
) -> List[BulletAttributeMapping]:
    """Convert raw LLM JSON into BulletAttributeMapping objects."""
    raw_mappings = response.get("mappings", [])
    result: List[BulletAttributeMapping] = []

    for raw in raw_mappings:
        if not isinstance(raw, dict):
            continue

        bullet_index = raw.get("bullet_index")
        if not isinstance(bullet_index, int):
            continue

        raw_attrs = raw.get("attributes", [])
        attrs: List[AttributeMapping] = []
        for raw_attr in raw_attrs:
            if not isinstance(raw_attr, dict):
                continue
            attr_id = raw_attr.get("attribute_id")
            score = raw_attr.get("relevance_score")
            if isinstance(attr_id, str) and isinstance(score, (int, float)):
                attrs.append(AttributeMapping(attribute_id=attr_id, relevance_score=float(score)))

        result.append(BulletAttributeMapping(bullet_index=bullet_index, attributes=attrs))

    return result


def init_profile_from_resume(
    user: User,
    parsed_resume: ParsedResume,
    llm_provider: LLMProvider,
    occupations: Optional[Dict[str, Occupation]] = None,
) -> ProfileInitResult:
    """Initialize user profile attributes from a parsed resume.

    Parameters
    ----------
    user : User
        The user to populate.
    parsed_resume : ParsedResume
        Output from resume parsing.
    llm_provider : LLMProvider
        LLM provider for bullet-to-attribute mapping.
    occupations : Optional[Dict[str, Occupation]]
        Pre-loaded occupations dict. If None, loads from disk.

    Returns
    -------
    ProfileInitResult
        Summary of what was updated.
    """
    if occupations is None:
        from packages.core.domain.occupation_populate import load_occupations
        occupations = load_occupations()

    registry = get_attribute_template_registry()
    leaf_templates = registry.get_leaf_templates()
    result = ProfileInitResult()

    # --- Phase 1: Occupation-based updates ---
    for job in parsed_resume.jobs:
        occupation = occupations.get(job.occupation_id)
        if occupation is None:
            result.skipped_occupations.append(job.occupation_id)
            continue

        add_job_experience(
            user,
            occupation,
            job_title=job.job_title,
            company_name=job.company_title,
            duration_months=int(job.years_of_experience * 12),
        )
        result.jobs_added += 1

    # --- Phase 2: Bullet-point-based updates ---
    bullets = _collect_bullets(parsed_resume)
    if bullets:
        catalog_text = _build_catalog_text(leaf_templates)
        instructions = _BULLET_MAPPING_INSTRUCTIONS_TEMPLATE.format(
            attribute_catalog=catalog_text,
        )
        bullet_texts = [b.text for b in bullets]

        raw_response = llm_provider.map_bullets_to_attributes(
            bullet_texts=bullet_texts,
            attribute_catalog_text=catalog_text,
            schema=BULLET_MAPPING_SCHEMA,
            instructions=instructions,
        )

        mappings = _parse_mapping_response(raw_response)
        result.bullets_mapped = len(mappings)

        update_attributes_from_bullet_mappings(user, mappings, bullets, leaf_templates)

    # --- Phase 3: Education-based binary attributes ---
    _apply_education_binary(user, parsed_resume, leaf_templates)

    result.attributes_updated = sum(
        1 for a in user.attributes.values()
        if a.capability is not None or a.preference is not None or a.binary is not None
    )

    return result


# Mapping from education_level (1-12) to attribute ID suffix
_EDUCATION_ATTR_IDS = [f"2.D.1.{i}" for i in range(1, 13)]


def _apply_education_binary(
    user: User,
    parsed_resume: ParsedResume,
    templates: Dict[str, UserAttributeTemplate],
) -> None:
    """Set binary education attributes based on highest education level.

    Levels are cumulative: if the user's highest level is 6 (Bachelor's),
    attributes 2.D.1.1 through 2.D.1.6 are set to True, and 2.D.1.7
    through 2.D.1.12 are set to False.
    """
    # Find the highest education_level across all education entries
    max_level = 0
    for edu in parsed_resume.education:
        if edu.education_level is not None and edu.education_level > max_level:
            max_level = edu.education_level

    if max_level == 0:
        return

    for level, attr_id in enumerate(_EDUCATION_ATTR_IDS, start=1):
        attr = user.get_attribute(attr_id)
        if attr is None:
            tmpl = templates.get(attr_id)
            if tmpl is None:
                continue
            attr = tmpl.instantiate()
            user.add_attribute(attr)

        attr.binary = level <= max_level
