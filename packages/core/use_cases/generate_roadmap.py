"""Career roadmap generation: build a personalized path from current role to target.

Uses LLM to produce structured milestones with actions and resources,
informed by gap analysis between the user's attribute profile and
the target occupation's requirements.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from packages.core.domain.occupation_class import Occupation
from packages.core.domain.user_class import User


# Same category configs used in career_analysis.py — maps user attribute
# prefixes to O*NET element prefixes and scales.
_CATEGORY_CONFIGS: List[Tuple[str, str, str, str]] = [
    ("Abilities",               "1.A", "1.A", "IM"),
    ("Work Styles",             "1.D", "1.D", "WI"),
    ("Basic Skills",            "3.A", "2.A", "IM"),
    ("Cross-Functional Skills", "3.B", "2.B", "IM"),
    ("Knowledge",               "3.C", "2.C", "IM"),
]


def compute_gap_analysis(
    user: User,
    target_occupation: Occupation,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Compare user attributes against target occupation requirements.

    Returns (gaps, strengths):
      - gaps: attributes where target requires significantly more than user has
      - strengths: attributes where user already scores well
    Each entry is a dict with attribute_name, category, user_score, target_score, gap.
    """
    gaps: List[Dict[str, Any]] = []
    strengths: List[Dict[str, Any]] = []

    for category_label, user_prefix, onet_prefix, scale_id in _CATEGORY_CONFIGS:
        leaf_prefix = user_prefix + "."
        for attr_id, attr in user.attributes.items():
            if not attr_id.startswith(leaf_prefix):
                continue
            if attr.capability is None or attr.mapping_element_id is None:
                continue

            element = target_occupation.elements.get(attr.mapping_element_id)
            if element is None:
                continue

            # Normalize target importance to 0-100
            if scale_id == "IM":
                im_scale = element.get_scale("IM")
                lv_scale = element.get_scale("LV")
                if im_scale and lv_scale and im_scale.value and lv_scale.value:
                    target_normalized = (im_scale.value * lv_scale.value / 35.0) * 100
                elif im_scale and im_scale.value:
                    target_normalized = (im_scale.value / 5.0) * 100
                else:
                    continue
            elif scale_id == "WI":
                wi_scale = element.get_scale("WI")
                if wi_scale and wi_scale.value is not None:
                    # WI ranges -3 to +3, normalize to 0-100
                    target_normalized = ((wi_scale.value + 3) / 6.0) * 100
                else:
                    continue
            else:
                scale = element.get_scale(scale_id)
                if scale and scale.value is not None:
                    target_normalized = (scale.value / scale.scale_def.max_value) * 100
                else:
                    continue

            gap_value = target_normalized - attr.capability

            entry = {
                "attribute_name": attr.attribute_name,
                "category": category_label,
                "user_score": round(attr.capability, 1),
                "target_score": round(target_normalized, 1),
                "gap": round(gap_value, 1),
            }

            if gap_value > 10:
                gaps.append(entry)
            elif attr.capability > 50:
                strengths.append(entry)

    gaps.sort(key=lambda g: g["gap"], reverse=True)
    strengths.sort(key=lambda s: s["user_score"], reverse=True)

    return gaps[:15], strengths[:10]


def build_roadmap_schema() -> Dict[str, Any]:
    """Return strict JSON schema for the career roadmap LLM response."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "roadmap_title": {"type": "string"},
            "estimated_timeline_months": {"type": "integer"},
            "summary": {"type": "string"},
            "milestones": {
                "type": "array",
                "minItems": 4,
                "maxItems": 6,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "milestone_number": {"type": "integer"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "timeline_months": {"type": "string"},
                        "milestone_type": {
                            "type": "string",
                            "enum": [
                                "skill_building",
                                "certification",
                                "experience",
                                "networking",
                                "transition",
                                "advancement",
                            ],
                        },
                        "actions": {
                            "type": "array",
                            "minItems": 2,
                            "maxItems": 4,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "action_title": {"type": "string"},
                                    "action_description": {"type": "string"},
                                    "action_type": {
                                        "type": "string",
                                        "enum": [
                                            "learn",
                                            "certify",
                                            "build",
                                            "network",
                                            "apply",
                                            "practice",
                                        ],
                                    },
                                    "resources": {
                                        "type": "array",
                                        "minItems": 2,
                                        "maxItems": 3,
                                        "items": {
                                            "type": "object",
                                            "additionalProperties": False,
                                            "properties": {
                                                "resource_name": {"type": "string"},
                                                "resource_type": {
                                                    "type": "string",
                                                    "enum": [
                                                        "course",
                                                        "book",
                                                        "community",
                                                        "tool",
                                                        "certification_program",
                                                        "website",
                                                    ],
                                                },
                                                "url": {"type": "string"},
                                                "description": {"type": "string"},
                                            },
                                            "required": [
                                                "resource_name",
                                                "resource_type",
                                                "url",
                                                "description",
                                            ],
                                        },
                                    },
                                },
                                "required": [
                                    "action_title",
                                    "action_description",
                                    "action_type",
                                    "resources",
                                ],
                            },
                        },
                    },
                    "required": [
                        "milestone_number",
                        "title",
                        "description",
                        "timeline_months",
                        "milestone_type",
                        "actions",
                    ],
                },
            },
        },
        "required": ["roadmap_title", "estimated_timeline_months", "summary", "milestones"],
    }


def build_roadmap_instructions() -> str:
    """System instructions for generating a career roadmap."""
    return (
        "You are an expert career coach and transition strategist.\n"
        "You receive: (1) the user's current role and background, "
        "(2) their target occupation with O*NET data, "
        "(3) a gap analysis showing which skills/abilities/knowledge areas need development, "
        "(4) their education, skills, and career preferences.\n\n"
        "Generate a realistic, actionable career roadmap with 4-6 milestones that form a clear path "
        "from the current role to the target occupation.\n\n"
        "Guidelines:\n"
        "- Each milestone should represent a meaningful career step, not just a task.\n"
        "- Order milestones chronologically. Early milestones should address foundational gaps; "
        "later milestones should address advanced requirements and the final transition.\n"
        "- Each milestone must have 2-4 concrete actions the user can take.\n"
        "- Each action must include 2-3 specific, real resources (courses, books, communities, tools). "
        "Provide actual URLs when possible (e.g., Coursera, edX, LinkedIn Learning, specific books on Amazon). "
        "If an exact URL is uncertain, provide the resource name and a plausible URL.\n"
        "- The timeline_months field for each milestone should be a range like '1-3' or '3-6'.\n"
        "- estimated_timeline_months should be the total realistic time for the full transition.\n"
        "- Be specific about what to learn based on the gap analysis. Don't give generic advice.\n"
        "- The summary should be 2-3 sentences describing the overall transition strategy.\n"
        "- milestone_type must be one of: skill_building, certification, experience, networking, transition, advancement.\n"
        "- action_type must be one of: learn, certify, build, network, apply, practice.\n"
        "- resource_type must be one of: course, book, community, tool, certification_program, website.\n"
        "- Return only valid JSON matching the schema."
    )


def build_link_validation_schema() -> Dict[str, Any]:
    """Return strict JSON schema for the link validation+fix LLM response."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "all_valid": {"type": "boolean"},
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "url":           {"type": "string"},
                        "is_valid":      {"type": "boolean"},
                        "reason":        {"type": "string"},
                        "suggested_url": {"type": "string"},
                    },
                    "required": ["url", "is_valid", "reason", "suggested_url"],
                },
            },
        },
        "required": ["all_valid", "results"],
    }


def build_link_validation_instructions() -> str:
    """System instructions for validating and fixing roadmap resource URLs."""
    return (
        "You are a URL plausibility checker. You cannot browse the internet — use reasoning only.\n\n"
        "For each resource (resource_name | resource_type | url | description), assess whether the URL is plausible:\n"
        "- Well-formed HTTPS URL\n"
        "- Known, legitimate domain (e.g., coursera.org, edx.org, linkedin.com/learning, udemy.com, "
        "amazon.com, github.com, freecodecamp.org, datacamp.com, udacity.com, docs.python.org, "
        "developer.mozilla.org, kaggle.com, pluralsight.com, oreilly.com, manning.com, etc.)\n"
        "- URL path plausibly matches the resource name and type (e.g., a course URL should not have a "
        "book ISBN path, a Python docs URL should point to python.org)\n"
        "- No obvious hallucination signals (random characters, impossible paths, mismatched domain/content)\n\n"
        "For each URL:\n"
        "- If valid: set is_valid=true, suggested_url = the original URL (unchanged)\n"
        "- If invalid: set is_valid=false, suggested_url = a real, plausible replacement URL for the "
        "same resource (same resource_name, resource_type, description). Choose a well-known URL "
        "that actually exists for that resource or a close equivalent.\n\n"
        "Set all_valid=true only if every single URL is valid.\n"
        "Return one result entry per input URL, in the same order as the input.\n"
        "Return only valid JSON matching the schema."
    )


def extract_resources_from_roadmap(roadmap: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return flat list of all resource dicts from milestones → actions → resources.

    Skips entries with empty or missing url.
    """
    resources = []
    for milestone in roadmap.get("milestones", []):
        for action in milestone.get("actions", []):
            for resource in action.get("resources", []):
                if isinstance(resource, dict) and resource.get("url"):
                    resources.append(resource)
    return resources


def patch_roadmap_urls(roadmap: Dict[str, Any], url_replacements: Dict[str, str]) -> None:
    """Mutate roadmap in-place, replacing invalid URLs with their suggested replacements."""
    for milestone in roadmap.get("milestones", []):
        for action in milestone.get("actions", []):
            for resource in action.get("resources", []):
                old_url = resource.get("url", "")
                if old_url in url_replacements:
                    resource["url"] = url_replacements[old_url]


def build_roadmap_user_text(
    *,
    current_job_title: str,
    current_occupation_name: str,
    target_occupation_id: str,
    target_occupation_name: str,
    gap_analysis: List[Dict[str, Any]],
    user_strengths: List[Dict[str, Any]],
    education: List[Dict[str, str]],
    skills: List[str],
    career_preferences: str = "",
) -> str:
    """Build user payload text for roadmap generation."""
    sections: List[str] = ["Generate a career roadmap using these inputs:\n"]

    sections.append(
        f"## Current Role\n"
        f"- Job Title: {current_job_title}\n"
        f"- O*NET Occupation: {current_occupation_name}\n"
    )

    sections.append(
        f"## Target Role\n"
        f"- O*NET Occupation ID: {target_occupation_id}\n"
        f"- O*NET Occupation: {target_occupation_name}\n"
    )

    if gap_analysis:
        rendered_gaps = "\n".join(
            f"- {g['attribute_name']} (category: {g['category']}): "
            f"user={g['user_score']}, target_importance={g['target_score']}, "
            f"gap={g['gap']}"
            for g in gap_analysis
        )
        sections.append(f"## Skill/Ability Gaps to Address\n{rendered_gaps}\n")

    if user_strengths:
        rendered_strengths = "\n".join(
            f"- {s['attribute_name']} (category: {s['category']}): score={s['user_score']}"
            for s in user_strengths
        )
        sections.append(f"## Existing Strengths\n{rendered_strengths}\n")

    if education:
        rendered_edu = "\n".join(
            f"- {e.get('degree', 'N/A')} in {e.get('field', 'N/A')} from {e.get('institution', 'N/A')}"
            for e in education
        )
        sections.append(f"## Education Background\n{rendered_edu}\n")

    if skills:
        sections.append(f"## Skills from Resume\n{', '.join(skills)}\n")

    if career_preferences.strip():
        sections.append(f"## Career Preferences & Feedback\n{career_preferences.strip()}\n")

    return "\n".join(sections)
