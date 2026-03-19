"""Resume upload endpoint."""

import asyncio
import tempfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from apps.api.main import app_state
from packages.core.domain.user_class import User
from packages.core.use_cases.init_profile_from_resume import init_profile_from_resume
from packages.core.use_cases.process_resume import parse_resume_file
from packages.infra.llm.client import OpenAIResponsesClient

router = APIRouter()

ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx"}

ATTRIBUTE_SECTIONS = [
    ("Abilities", "1.A"),
    ("Work Styles", "1.D"),
    ("Education", "2.D"),
    ("Basic Skills", "3.A"),
    ("Cross-Functional Skills", "3.B"),
    ("Knowledge", "3.C"),
    ("Interests & Work Values", "4.B"),
]


def _run_pipeline(tmp_path: str):
    """Synchronous pipeline: parse resume then init profile."""
    provider = OpenAIResponsesClient()
    instructions = app_state["resume_instructions"]
    occupations = app_state["occupations"]

    parsed = parse_resume_file(tmp_path, llm_provider=provider, instructions=instructions)

    user = User(user_id="web-session")
    result = init_profile_from_resume(user, parsed, provider, occupations=occupations)

    return parsed, user, result


def _build_attribute_sections(user: User, scale_anchors: dict | None = None):
    """Build the 7 attribute sections with top 5 each."""
    if scale_anchors is None:
        scale_anchors = {}
    sections = []
    for label, prefix in ATTRIBUTE_SECTIONS:
        leaf_prefix = prefix + "."
        leaves = []
        for attr_id, attr in user.attributes.items():
            if attr_id.startswith(leaf_prefix) and attr.capability is not None and attr.capability > 0:
                element_id = attr.mapping_element_id or attr_id
                leaves.append({
                    "attribute_id": attr_id,
                    "name": attr.attribute_name,
                    "capability": round(attr.capability, 1),
                    "preference": round(attr.preference, 1) if attr.preference is not None else None,
                    "description": attr.description,
                    "scale_anchors": scale_anchors.get(element_id, []),
                })
        leaves.sort(key=lambda x: x["capability"], reverse=True)
        sections.append({
            "label": label,
            "prefix": prefix,
            "attributes": leaves[:5],
        })
    return sections


@router.post("/upload")
async def upload_resume(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'. Allowed: .pdf, .doc, .docx")

    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        loop = asyncio.get_running_loop()
        parsed, user, result = await loop.run_in_executor(None, _run_pipeline, tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    app_state["current_user"] = user
    app_state["parsed_resume"] = parsed

    jobs = [
        {
            "job_title": j.job_title,
            "company": j.company_title,
            "occupation": j.occupation_title,
            "years": j.years_of_experience,
        }
        for j in parsed.jobs
    ]

    education = [
        {
            "institution": e.institution,
            "degree": e.degree,
            "field": e.field_of_study,
            "year": e.graduation_year,
        }
        for e in parsed.education
    ]

    return {
        "career_questions": app_state.get("career_questions", []),
        "jobs": jobs,
        "education": education,
        "resume_skills": parsed.skills,
        "attribute_sections": _build_attribute_sections(user, app_state.get("scale_anchors")),
        "stats": {
            "jobs_added": result.jobs_added,
            "bullets_mapped": result.bullets_mapped,
            "attributes_updated": result.attributes_updated,
        },
    }
