"""Resume processing use case."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Union

from packages.core.domain.resume import ParsedResume
from packages.core.ports.llm_provider import LLMProvider

RESUME_PARSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["jobs", "skills", "education"],
    "properties": {
        "jobs": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "job_title",
                    "company_title",
                    "years_of_experience",
                    "bullet_points",
                    "projects",
                ],
                "properties": {
                    "job_title": {"type": "string"},
                    "company_title": {"type": "string"},
                    "years_of_experience": {"type": "number"},
                    "bullet_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "projects": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["project_name", "bullet_points"],
                            "properties": {
                                "project_name": {
                                    "type": ["string", "null"],
                                },
                                "bullet_points": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                },
                            },
                        },
                    },
                },
            },
        },
        "skills": {
            "type": "array",
            "items": {"type": "string"},
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "institution",
                    "degree",
                    "field_of_study",
                    "graduation_year",
                    "bullet_points",
                ],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": ["string", "null"]},
                    "field_of_study": {"type": ["string", "null"]},
                    "graduation_year": {"type": ["integer", "null"]},
                    "bullet_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}

RESUME_PARSE_INSTRUCTIONS = """You extract structured resume data.

Rules:
- Return only valid JSON matching the provided schema.
- Do not fabricate information that is not present in the resume.
- Keep bullet points concise and factual.
- Include nested projects under each job when they are explicitly present.
- years_of_experience must be numeric and represent duration for each job.
- Use empty arrays when information is unavailable.
"""


def parse_resume_file(
    resume_path: Union[str, Path],
    *,
    llm_provider: LLMProvider,
    schema: Optional[Mapping[str, Any]] = None,
    instructions: str = RESUME_PARSE_INSTRUCTIONS,
) -> ParsedResume:
    """Parse a PDF/Word resume into normalized structured output."""
    normalized_path = Path(resume_path)
    if not normalized_path.exists():
        raise FileNotFoundError(f"Resume file not found: {normalized_path}")

    payload = llm_provider.parse_resume(
        resume_path=normalized_path,
        schema=schema or RESUME_PARSE_SCHEMA,
        instructions=instructions,
    )
    return ParsedResume.from_dict(dict(payload))


def parse_resume_with_openai(
    resume_path: Union[str, Path],
    *,
    model: Optional[str] = None,
) -> ParsedResume:
    """Convenience wrapper that parses a resume through OpenAI Responses API."""
    from packages.infra.llm.client import OpenAIResponsesClient

    provider = OpenAIResponsesClient(model=model)
    return parse_resume_file(resume_path, llm_provider=provider)
