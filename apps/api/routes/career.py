"""Career analysis endpoints."""

import asyncio
import logging
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from apps.api.main import app_state
from packages.core.use_cases.career_analysis import find_matching_occupations
from packages.core.use_cases.generate_roadmap import (
    build_link_validation_instructions,
    build_link_validation_schema,
    extract_resources_from_roadmap,
    patch_roadmap_urls,
    build_roadmap_instructions,
    build_roadmap_schema,
    build_roadmap_user_text,
    compute_gap_analysis,
)

logger = logging.getLogger(__name__)
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


class RoadmapRequest(BaseModel):
    occupation_id: str
    occupation_name: str


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

    # Store career preferences for use by the roadmap endpoint
    app_state["career_preferences"] = {
        "answers": cleaned_answers,
        "feedback": feedback,
    }

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


def _format_career_preferences() -> str:
    """Format stored career preferences into text for LLM prompt."""
    prefs = app_state.get("career_preferences")
    if not prefs:
        return ""

    parts: list[str] = []
    feedback = prefs.get("feedback", "").strip()
    if feedback:
        parts.append(f"User feedback: {feedback}")

    answers = prefs.get("answers", [])
    if answers:
        qa_lines = "\n".join(
            f"- Q: {a.get('question', '')}\n  A: {a.get('answer', '')}"
            for a in answers
        )
        parts.append(f"Career preference answers:\n{qa_lines}")

    return "\n\n".join(parts)


@router.post("/career-roadmap")
async def generate_career_roadmap(payload: RoadmapRequest):
    user = app_state.get("current_user")
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile yet. Upload a resume first.")

    occupations = app_state["occupations"]
    target_occupation = occupations.get(payload.occupation_id)
    if target_occupation is None:
        raise HTTPException(status_code=404, detail=f"Occupation '{payload.occupation_id}' not found.")

    # Current role from most recent job
    current_job = user.jobs[0] if user.jobs else None
    current_job_title = current_job.job_title if current_job else "Unknown"
    current_occupation_name = current_job.occupation_name if current_job else "Unknown"

    # Gap analysis
    loop = asyncio.get_running_loop()
    gaps, strengths = await loop.run_in_executor(
        None,
        lambda: compute_gap_analysis(user, target_occupation),
    )

    # Education and skills from parsed resume
    parsed_resume = app_state.get("parsed_resume")
    education: list[dict] = []
    skills: list[str] = []
    if parsed_resume:
        education = [
            {"degree": e.degree, "field": e.field_of_study, "institution": e.institution}
            for e in parsed_resume.education
        ]
        skills = parsed_resume.skills

    # Career preferences from refinement step
    career_preferences = _format_career_preferences()

    user_text = build_roadmap_user_text(
        current_job_title=current_job_title,
        current_occupation_name=current_occupation_name,
        target_occupation_id=payload.occupation_id,
        target_occupation_name=payload.occupation_name,
        gap_analysis=gaps,
        user_strengths=strengths,
        education=education,
        skills=skills,
        career_preferences=career_preferences,
    )

    provider = OpenAIResponsesClient()
    roadmap_schema = build_roadmap_schema()
    roadmap_instructions = build_roadmap_instructions()

    try:
        roadmap = await loop.run_in_executor(
            None,
            lambda: provider.generate_career_roadmap(
                user_text=user_text,
                schema=roadmap_schema,
                instructions=roadmap_instructions,
            ),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Validate links and patch any invalid ones in-place
    resources = extract_resources_from_roadmap(roadmap)
    if resources:
        validation_schema = build_link_validation_schema()
        validation_instructions = build_link_validation_instructions()
        try:
            validation = await loop.run_in_executor(
                None,
                lambda: provider.validate_and_fix_roadmap_links(
                    resources=resources,
                    schema=validation_schema,
                    instructions=validation_instructions,
                ),
            )
            if not validation.get("all_valid", True):
                url_replacements = {
                    r["url"]: r["suggested_url"]
                    for r in validation.get("results", [])
                    if not r.get("is_valid", True) and r.get("suggested_url")
                }
                if url_replacements:
                    logger.info(
                        "Patching %d invalid URL(s): %s",
                        len(url_replacements),
                        list(url_replacements.keys()),
                    )
                    patch_roadmap_urls(roadmap, url_replacements)
        except Exception as exc:
            logger.warning("Link validation failed, returning roadmap as-is: %s", exc)

    return roadmap
