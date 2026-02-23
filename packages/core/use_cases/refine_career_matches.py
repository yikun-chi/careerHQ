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
                        "reason": {"type": "string"},
                    },
                    "required": ["occupation_id", "occupation_name", "reason"],
                },
            }
        },
        "required": ["top_careers"],
    }


def build_refine_career_instructions() -> str:
    """System instructions for refining initial career matches."""
    return (
        "You are an expert career advisor.\n"
        "You receive: (1) a list of initially matched occupations ranked by profile overlap and "
        "(2) a user's follow-up answers about preferences, constraints, and goals.\n"
        "Pick exactly 3 best occupations from the provided list only.\n"
        "For each pick, explain why it fits the user's profile and answers in 2-4 concise sentences.\n"
        "Do not invent occupations not present in the supplied list.\n"
        "Return only valid JSON matching the schema."
    )


def build_refine_career_user_text(
    *,
    matches: List[Mapping[str, Any]],
    answers: List[Mapping[str, str]],
) -> str:
    """Build user payload text containing answers and the full match list."""
    rendered_answers = "\n".join(
        f"- Q: {a.get('question', '').strip()}\n  A: {a.get('answer', '').strip()}"
        for a in answers
    )

    rendered_matches = "\n".join(
        "- "
        f"{m.get('occupation_id', '')} | {m.get('occupation_name', '')} | "
        f"match score: {m.get('match_count', 0)}/{m.get('total_categories', 0)} | "
        f"categories: {', '.join(m.get('matched_categories', []))}"
        for m in matches
    )

    return (
        "Refine career recommendations using these inputs:\n\n"
        "## Follow-up answers\n"
        f"{rendered_answers}\n\n"
        "## All matched occupations\n"
        f"{rendered_matches}"
    )

