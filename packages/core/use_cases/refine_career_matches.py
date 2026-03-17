"""LLM prompt helpers for refining career matches with user preferences."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping


def build_refine_career_schema() -> Dict[str, Any]:
    """Return strict JSON schema for top-3 refined career recommendations."""
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "top_careers": {
                "type": "array",
                "minItems": 3,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "occupation_id": {"type": "string"},
                        "occupation_name": {"type": "string"},
                        "profile_fit": {"type": "string"},
                        "preference_fit": {"type": "string"},
                    },
                    "required": ["occupation_id", "occupation_name", "profile_fit", "preference_fit"],
                },
            }
        },
        "required": ["top_careers"],
    }


def build_refine_career_instructions() -> str:
    """System instructions for refining initial career matches."""
    return (
        "You are an expert career advisor.\n"
        "You receive: (1) a list of initially matched occupations ranked by profile overlap, "
        "(2) optional free-text feedback from the user, and "
        "(3) optional follow-up answers about preferences, constraints, and goals.\n"
        "Pick exactly 3 best occupations from the provided list only.\n"
        "For each pick, provide two explanations:\n"
        "- profile_fit: 1-2 sentences on which matched attributes from the user's profile "
        "(skills, abilities, work styles, etc.) make them a strong fit for this occupation.\n"
        "- preference_fit: 1-2 sentences on how the career aligns with the user's "
        "stated feedback and questionnaire answers.\n"
        "Do not invent occupations not present in the supplied list.\n"
        "Return only valid JSON matching the schema."
    )


def build_refine_career_user_text(
    *,
    matches: List[Mapping[str, Any]],
    answers: List[Mapping[str, str]],
    feedback: str = "",
) -> str:
    """Build user payload text containing feedback, answers, and the full match list."""
    sections: List[str] = ["Refine career recommendations using these inputs:\n"]

    if feedback.strip():
        sections.append(f"## User feedback\n{feedback.strip()}\n")

    if answers:
        rendered_answers = "\n".join(
            f"- Q: {a.get('question', '').strip()}\n  A: {a.get('answer', '').strip()}"
            for a in answers
        )
        sections.append(f"## Follow-up answers\n{rendered_answers}\n")

    rendered_matches = "\n".join(
        "- "
        f"{m.get('occupation_id', '')} | {m.get('occupation_name', '')} | "
        f"match score: {m.get('match_count', 0)}/{m.get('total_categories', 0)} | "
        f"categories: {', '.join(m.get('matched_categories', []))}"
        for m in matches
    )
    sections.append(f"## All matched occupations\n{rendered_matches}")

    return "\n".join(sections)

