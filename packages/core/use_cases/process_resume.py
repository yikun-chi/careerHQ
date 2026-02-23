"""Resume processing use case."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

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
                    "occupation_id",
                    "occupation_title",
                    "years_of_experience",
                    "bullet_points",
                    "projects",
                ],
                "properties": {
                    "job_title": {"type": "string"},
                    "company_title": {"type": "string"},
                    "occupation_id": {"type": "string"},
                    "occupation_title": {"type": "string"},
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
                    "education_level",
                    "bullet_points",
                ],
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": ["string", "null"]},
                    "field_of_study": {"type": ["string", "null"]},
                    "graduation_year": {"type": ["integer", "null"]},
                    "education_level": {
                        "type": "integer",
                        "enum": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
                    },
                    "bullet_points": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
            },
        },
    },
}

_RESUME_PARSE_INSTRUCTIONS_TEMPLATE = """You extract structured resume data.

## Job extraction rules
- Each distinct employer/company is ONE job entry. Do NOT split one employer into multiple jobs.
- "job_title" is the role/title the person held at that company (e.g. "Analytics Experienced Associate").
- "company_title" is the employer name. Every job MUST have a company_title — never leave it empty.
- If multiple named projects or sub-roles appear under the same employer, put them in the "projects"
  array of that single job entry. Each project gets a "project_name" and its own "bullet_points".
- Bullet points that are not under a specific project go in the job-level "bullet_points" array.
- Items listed as standalone personal projects (no employer) should be omitted from "jobs".
  Instead, capture their skills in the "skills" array.
- Items in an "Additional Experience" or similar section that have an employer (e.g. "Intern, IBM")
  are separate job entries — each with their own company_title and job_title.
- "years_of_experience" must be numeric. Estimate from dates when possible.

## Occupation matching
- For each job, match it to the single best O*NET occupation from the list below.
  Consider both the official title AND the alternate titles when deciding the best match.
  Pick the occupation whose scope and duties most closely match the job described.
- Set "occupation_id" to the O*NET code (e.g. "15-1252.00") and "occupation_title" to the
  official title (the text before the "|"). Both must come from the SAME row.
- You MUST pick from this list — do not invent IDs or titles.

## Education level classification
For each education entry, set "education_level" to the best matching level:
 1 = Less than a High School Diploma
 2 = High School Diploma (or GED)
 3 = Post-Secondary Certificate (vocational/trade certificate)
 4 = Some College Courses (attended college but no degree)
 5 = Associate's Degree (A.A., A.S.)
 6 = Bachelor's Degree (B.A., B.S., B.Eng., etc.)
 7 = Post-Baccalaureate Certificate
 8 = Master's Degree (M.A., M.S., M.Eng., MBA, etc.)
 9 = Post-Master's Certificate
10 = First Professional Degree (J.D., M.D., D.D.S., Pharm.D., etc.)
11 = Doctoral Degree (Ph.D., Ed.D., etc.)
12 = Post-Doctoral Training

## General rules
- Return only valid JSON matching the provided schema.
- Do not fabricate information that is not present in the resume.
- Keep bullet points concise and factual.
- Use empty arrays when information is unavailable.

## O*NET occupations (ID | Title | Alternate titles)
{occupation_list}
"""


def _load_occupation_data() -> Tuple[
    List[Tuple[str, str]], Dict[str, List[str]], Set[str]
]:
    """Load occupation titles and alternate titles.

    Returns
    -------
    occupations : List[Tuple[str, str]]
        (occupation_id, occupation_name) pairs.
    alt_titles : Dict[str, List[str]]
        Mapping of occupation_id to list of alternate titles.
    valid_ids : Set[str]
        Set of all valid occupation IDs for validation.
    """
    from packages.core.domain.occupation_populate import load_occupations_list
    from packages.core.domain.occupation_initialize import get_data_dir

    occupations = [(oid, name) for oid, name, _ in load_occupations_list()]
    valid_ids = {oid for oid, _ in occupations}

    alt_titles: Dict[str, List[str]] = {}
    alt_path = get_data_dir() / "Alternate Titles.txt"
    with open(alt_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)  # skip header
        for row in reader:
            if len(row) < 2:
                continue
            occ_id = row[0].strip()
            alt_title = row[1].strip()
            if occ_id and alt_title and occ_id in valid_ids:
                alt_titles.setdefault(occ_id, []).append(alt_title)

    return occupations, alt_titles, valid_ids


def build_resume_parse_instructions(
    occupation_data: Optional[
        Tuple[List[Tuple[str, str]], Dict[str, List[str]]]
    ] = None,
) -> str:
    """Build the full LLM instructions with occupation titles + alternates."""
    if occupation_data is None:
        occupations, alt_titles, _ = _load_occupation_data()
    else:
        occupations, alt_titles = occupation_data

    lines: List[str] = []
    for occ_id, occ_name in occupations:
        alts = alt_titles.get(occ_id, [])
        if alts:
            lines.append(f"{occ_id} | {occ_name} | {', '.join(alts)}")
        else:
            lines.append(f"{occ_id} | {occ_name}")

    listing = "\n".join(lines)
    return _RESUME_PARSE_INSTRUCTIONS_TEMPLATE.format(occupation_list=listing)


def parse_resume_file(
    resume_path: Union[str, Path],
    *,
    llm_provider: LLMProvider,
    schema: Optional[Mapping[str, Any]] = None,
    instructions: Optional[str] = None,
) -> ParsedResume:
    """Parse a PDF/Word resume into normalized structured output."""
    normalized_path = Path(resume_path)
    if not normalized_path.exists():
        raise FileNotFoundError(f"Resume file not found: {normalized_path}")

    if instructions is None:
        instructions = build_resume_parse_instructions()

    payload = llm_provider.parse_resume(
        resume_path=normalized_path,
        schema=schema or RESUME_PARSE_SCHEMA,
        instructions=instructions,
    )

    parsed = ParsedResume.from_dict(dict(payload))

    # Validate that returned occupation_ids are in the database
    _, _, valid_ids = _load_occupation_data()
    for job in parsed.jobs:
        if job.occupation_id not in valid_ids:
            raise ValueError(
                f"LLM returned unknown occupation_id '{job.occupation_id}' "
                f"for job '{job.job_title}'. Not in O*NET database."
            )

    return parsed


def parse_resume_with_openai(
    resume_path: Union[str, Path],
    *,
    model: Optional[str] = None,
) -> ParsedResume:
    """Convenience wrapper that parses a resume through OpenAI Responses API."""
    from packages.infra.llm.client import OpenAIResponsesClient

    provider = OpenAIResponsesClient(model=model)
    return parse_resume_file(resume_path, llm_provider=provider)
