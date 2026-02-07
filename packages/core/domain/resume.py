"""Resume domain models for structured resume parsing output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _as_string_list(value: Any, field_name: str) -> List[str]:
    """Normalize a field into a list of non-empty strings."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    result: List[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must contain only strings")
        cleaned = item.strip()
        if cleaned:
            result.append(cleaned)
    return result


def _coerce_optional_string(value: Any, field_name: str) -> Optional[str]:
    """Normalize optional strings, converting blanks to None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null")
    cleaned = value.strip()
    return cleaned or None


def _coerce_years(value: Any) -> float:
    """Convert numeric-like values to years as a float."""
    if isinstance(value, (int, float)):
        years = float(value)
    elif isinstance(value, str):
        stripped = value.strip()
        years = float(stripped)
    else:
        raise ValueError("years_of_experience must be a number")
    if years < 0:
        raise ValueError("years_of_experience cannot be negative")
    return years


def _coerce_optional_int(value: Any, field_name: str) -> Optional[int]:
    """Normalize optional integer fields."""
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{field_name} must be an integer or null")
    parsed = int(value)
    return parsed


@dataclass
class ResumeProject:
    """A project nested under a job."""

    project_name: Optional[str] = None
    bullet_points: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeProject":
        if not isinstance(data, dict):
            raise ValueError("project item must be an object")
        return cls(
            project_name=_coerce_optional_string(data.get("project_name"), "project_name"),
            bullet_points=_as_string_list(data.get("bullet_points"), "project bullet_points"),
        )


@dataclass
class ResumeJob:
    """A normalized job entry extracted from a resume."""

    job_title: str
    company_title: str
    years_of_experience: float
    bullet_points: List[str] = field(default_factory=list)
    projects: List[ResumeProject] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeJob":
        if not isinstance(data, dict):
            raise ValueError("job item must be an object")

        job_title = _coerce_optional_string(data.get("job_title"), "job_title")
        company_title = _coerce_optional_string(data.get("company_title"), "company_title")
        if job_title is None:
            raise ValueError("job_title is required")
        if company_title is None:
            raise ValueError("company_title is required")

        raw_projects = data.get("projects") or []
        if not isinstance(raw_projects, list):
            raise ValueError("projects must be a list")

        return cls(
            job_title=job_title,
            company_title=company_title,
            years_of_experience=_coerce_years(data.get("years_of_experience")),
            bullet_points=_as_string_list(data.get("bullet_points"), "job bullet_points"),
            projects=[ResumeProject.from_dict(item) for item in raw_projects],
        )


@dataclass
class ResumeEducation:
    """A normalized education entry extracted from a resume."""

    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    bullet_points: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResumeEducation":
        if not isinstance(data, dict):
            raise ValueError("education item must be an object")

        institution = _coerce_optional_string(data.get("institution"), "institution")
        if institution is None:
            raise ValueError("institution is required")

        return cls(
            institution=institution,
            degree=_coerce_optional_string(data.get("degree"), "degree"),
            field_of_study=_coerce_optional_string(data.get("field_of_study"), "field_of_study"),
            graduation_year=_coerce_optional_int(data.get("graduation_year"), "graduation_year"),
            bullet_points=_as_string_list(data.get("bullet_points"), "education bullet_points"),
        )


@dataclass
class ParsedResume:
    """Structured resume parse output."""

    jobs: List[ResumeJob] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    education: List[ResumeEducation] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ParsedResume":
        if not isinstance(data, dict):
            raise ValueError("resume payload must be an object")

        raw_jobs = data.get("jobs") or []
        raw_skills = data.get("skills") or []
        raw_education = data.get("education") or []

        if not isinstance(raw_jobs, list):
            raise ValueError("jobs must be a list")
        if not isinstance(raw_education, list):
            raise ValueError("education must be a list")

        return cls(
            jobs=[ResumeJob.from_dict(job) for job in raw_jobs],
            skills=_as_string_list(raw_skills, "skills"),
            education=[ResumeEducation.from_dict(item) for item in raw_education],
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize back to a JSON-compatible dictionary."""
        return {
            "jobs": [
                {
                    "job_title": job.job_title,
                    "company_title": job.company_title,
                    "years_of_experience": job.years_of_experience,
                    "bullet_points": job.bullet_points,
                    "projects": [
                        {
                            "project_name": project.project_name,
                            "bullet_points": project.bullet_points,
                        }
                        for project in job.projects
                    ],
                }
                for job in self.jobs
            ],
            "skills": self.skills,
            "education": [
                {
                    "institution": edu.institution,
                    "degree": edu.degree,
                    "field_of_study": edu.field_of_study,
                    "graduation_year": edu.graduation_year,
                    "bullet_points": edu.bullet_points,
                }
                for edu in self.education
            ],
        }
