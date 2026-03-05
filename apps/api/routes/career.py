"""Career analysis endpoints."""

import asyncio
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.main import app_state
from packages.core.use_cases.career_analysis import find_matching_occupations
from packages.core.use_cases.refine_career_matches import (
    build_refine_career_instructions,
    build_refine_career_schema,
)
from packages.infra.llm.client import OpenAIResponsesClient

router = APIRouter()

LEGACY_FOLLOW_UP_QUESTIONS = [
    "What kind of work environment do you prefer (e.g., remote, office, hands-on, fieldwork)?",
    "Which factors matter most to you right now (pick up to 3): salary, growth, stability, impact, flexibility, creativity?",
    "Do you have any constraints or goals for your next role (location, schedule, industry, leadership, certification)?",
]


def _get_follow_up_questions() -> list[str]:
    """Use the configured 6 career questions as refinement prompts."""
    configured = app_state.get("career_questions") or []
    prompts = [q.get("prompt", "").strip() for q in configured if isinstance(q, dict)]
    prompts = [p for p in prompts if p]
    return prompts or LEGACY_FOLLOW_UP_QUESTIONS


class QuestionAnswer(BaseModel):
    question: str
    answer: str


class RefineCareerRequest(BaseModel):
    answers: list[QuestionAnswer] = []
    feedback: str = ""


class AttributeUpdateRequest(BaseModel):
    capability: float


def _build_matches(user, occupations):
    matches = find_matching_occupations(user, occupations)
    return [asdict(m) for m in matches]


@router.put("/user/attributes/{attribute_id:path}")
async def update_user_attribute(attribute_id: str, payload: AttributeUpdateRequest):
    user = app_state.get("current_user")
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile yet. Upload a resume first.")

    attr = user.attributes.get(attribute_id)
    if attr is None:
        raise HTTPException(status_code=404, detail=f"Attribute '{attribute_id}' not found.")

    if not (0 <= payload.capability <= 100):
        raise HTTPException(status_code=400, detail="Capability must be between 0 and 100.")

    attr.capability = payload.capability
    # Invalidate stale career matches
    app_state.pop("last_career_matches", None)

    return {"attribute_id": attribute_id, "capability": attr.capability}


@router.get("/career-analysis")
async def career_analysis():
    user = app_state.get("current_user")
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile yet. Upload a resume first.")

    occupations = app_state["occupations"]

    loop = asyncio.get_running_loop()
    matches = await loop.run_in_executor(None, _build_matches, user, occupations)
    app_state["last_career_matches"] = matches

    return {
        "matches": matches,
        "follow_up_questions": _get_follow_up_questions(),
    }


@router.post("/career-analysis/refine")
async def refine_career_analysis(payload: RefineCareerRequest):
    user = app_state.get("current_user")
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile yet. Upload a resume first.")

    matches = app_state.get("last_career_matches")
    if not matches:
        occupations = app_state["occupations"]
        loop = asyncio.get_running_loop()
        matches = await loop.run_in_executor(None, _build_matches, user, occupations)
        app_state["last_career_matches"] = matches

    if len(matches) < 3:
        raise HTTPException(status_code=400, detail="Need at least 3 matched occupations to refine recommendations.")

    cleaned_answers = [
        {"question": a.question.strip(), "answer": a.answer.strip()}
        for a in payload.answers
        if a.answer.strip()
    ]
    feedback = payload.feedback.strip()

    if not cleaned_answers and not feedback:
        raise HTTPException(status_code=400, detail="Please provide feedback or answer at least one question.")

    provider = OpenAIResponsesClient()
    schema = build_refine_career_schema()
    instructions = build_refine_career_instructions()

    loop = asyncio.get_running_loop()
    try:
        refined = await loop.run_in_executor(
            None,
            lambda: provider.refine_career_matches(
                matches=matches,
                answers=cleaned_answers,
                schema=schema,
                instructions=instructions,
                feedback=feedback,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "top_careers": refined.get("top_careers", []),
    }
