"""Unit tests for resume parsing use case (no external API calls)."""

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping

# Add project root for imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.resume import ResumeEducation, ParsedResume
from packages.core.use_cases.process_resume import parse_resume_file


class FakeResumeLLMProvider:
    """Test double that returns a fixed structured payload."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)
        self.last_resume_path: Path | None = None
        self.last_schema: Mapping[str, Any] | None = None
        self.last_instructions: str | None = None

    def parse_resume(
        self,
        *,
        resume_path: Path,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        self.last_resume_path = resume_path
        self.last_schema = schema
        self.last_instructions = instructions
        return dict(self.payload)

    def map_bullets_to_attributes(
        self,
        *,
        bullet_texts: List[str],
        attribute_catalog_text: str,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        return {"mappings": []}


class TestParseResumeFile(unittest.TestCase):
    """Unit tests that do not call external APIs."""

    def test_parse_resume_file_returns_normalized_resume(self) -> None:
        fake_payload = {
            "jobs": [
                {
                    "job_title": "Software Engineer",
                    "company_title": "Example Corp",
                    "occupation_id": "15-1252.00",
                    "occupation_title": "Software Developers",
                    "years_of_experience": 2.5,
                    "bullet_points": ["Built internal API", "Reduced latency by 30%"],
                    "projects": [
                        {
                            "project_name": "Realtime Analytics",
                            "bullet_points": ["Implemented stream processing pipeline"],
                        }
                    ],
                }
            ],
            "skills": ["Python", "SQL", "FastAPI"],
            "education": [
                {
                    "institution": "State University",
                    "degree": "B.S.",
                    "field_of_study": "Computer Science",
                    "graduation_year": 2022,
                    "education_level": 6,
                    "bullet_points": ["Dean's List"],
                }
            ],
        }
        provider = FakeResumeLLMProvider(fake_payload)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            parsed = parse_resume_file(tmp.name, llm_provider=provider)

        self.assertEqual(len(parsed.jobs), 1)
        self.assertEqual(parsed.jobs[0].job_title, "Software Engineer")
        self.assertEqual(parsed.jobs[0].company_title, "Example Corp")
        self.assertEqual(parsed.jobs[0].occupation_id, "15-1252.00")
        self.assertEqual(parsed.jobs[0].occupation_title, "Software Developers")
        self.assertAlmostEqual(parsed.jobs[0].years_of_experience, 2.5)
        self.assertEqual(parsed.jobs[0].projects[0].project_name, "Realtime Analytics")
        self.assertEqual(parsed.skills, ["Python", "SQL", "FastAPI"])
        self.assertEqual(parsed.education[0].institution, "State University")
        self.assertEqual(parsed.education[0].education_level, 6)
        self.assertIsNotNone(provider.last_resume_path)
        self.assertIsNotNone(provider.last_schema)
        self.assertIsNotNone(provider.last_instructions)

    def test_parse_resume_file_raises_for_missing_file(self) -> None:
        provider = FakeResumeLLMProvider({"jobs": [], "skills": [], "education": []})
        with self.assertRaises(FileNotFoundError):
            parse_resume_file("does_not_exist.pdf", llm_provider=provider)


class TestEducationLevelRoundTrip(unittest.TestCase):
    """Verify education_level survives from_dict -> to_dict."""

    def test_education_level_round_trips(self) -> None:
        data = {
            "jobs": [],
            "skills": [],
            "education": [
                {
                    "institution": "MIT",
                    "degree": "Ph.D.",
                    "field_of_study": "Physics",
                    "graduation_year": 2020,
                    "education_level": 11,
                    "bullet_points": [],
                }
            ],
        }
        parsed = ParsedResume.from_dict(data)
        self.assertEqual(parsed.education[0].education_level, 11)

        out = parsed.to_dict()
        self.assertEqual(out["education"][0]["education_level"], 11)

    def test_education_level_none_when_absent(self) -> None:
        edu = ResumeEducation.from_dict({
            "institution": "Community College",
            "degree": None,
            "field_of_study": None,
            "graduation_year": None,
            "bullet_points": [],
        })
        self.assertIsNone(edu.education_level)

    def test_education_level_rejects_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            ResumeEducation.from_dict({
                "institution": "School",
                "education_level": 13,
            })
        with self.assertRaises(ValueError):
            ResumeEducation.from_dict({
                "institution": "School",
                "education_level": 0,
            })


if __name__ == "__main__":
    unittest.main(verbosity=2)
