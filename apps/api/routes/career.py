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

FOLLOW_UP_QUESTIONS = [
    "What kind of work environment do you prefer (e.g., remote, office, hands-on, fieldwork)?",
    "Which factors matter most to you right now (pick up to 3): salary, growth, stability, impact, flexibility, creativity?",
    "Do you have any constraints or goals for your next role (location, schedule, industry, leadership, certification)?",
]


class QuestionAnswer(BaseModel):
    question: str
    answer: str


class RefineCareerRequest(BaseModel):
    answers: list[QuestionAnswer]


def _build_matches(user, occupations):
    matches = find_matching_occupations(user, occupations)
    return [asdict(m) for m in matches]


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
        "follow_up_questions": FOLLOW_UP_QUESTIONS,
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
    if not cleaned_answers:
        raise HTTPException(status_code=400, detail="Please provide at least one answer.")

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
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "top_careers": refined.get("top_careers", []),
    }
