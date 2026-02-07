"""Tests for worker resume parsing task wiring."""

import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Mapping

# Add project root for imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from apps.worker.tasks.parse_resume import parse_resume_task
from apps.worker.worker import get_registered_tasks


class FakeResumeLLMProvider:
    """Test double for worker task parsing."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self.payload = dict(payload)

    def parse_resume(
        self,
        *,
        resume_path: Path,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        _ = (resume_path, schema, instructions)
        return dict(self.payload)


class TestParseResumeTask(unittest.TestCase):
    """Tests for parse_resume_task worker wrapper."""

    def test_parse_resume_task_returns_structured_payload(self) -> None:
        fake_payload = {
            "jobs": [
                {
                    "job_title": "Data Analyst",
                    "company_title": "CareerHQ",
                    "years_of_experience": 1.5,
                    "bullet_points": ["Built dashboards"],
                    "projects": [],
                }
            ],
            "skills": ["SQL", "Python"],
            "education": [
                {
                    "institution": "Test University",
                    "degree": "B.S.",
                    "field_of_study": "Statistics",
                    "graduation_year": 2023,
                    "bullet_points": [],
                }
            ],
        }
        provider = FakeResumeLLMProvider(fake_payload)

        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            output = parse_resume_task(tmp.name, llm_provider=provider)

        self.assertIn("resume_path", output)
        self.assertIn("parsed_resume", output)
        self.assertEqual(output["parsed_resume"]["jobs"][0]["job_title"], "Data Analyst")
        self.assertEqual(output["parsed_resume"]["skills"], ["SQL", "Python"])


class TestWorkerRegistry(unittest.TestCase):
    """Tests for worker task registry."""

    def test_parse_resume_task_is_registered(self) -> None:
        tasks = get_registered_tasks()
        self.assertIn("parse_resume", tasks)
        self.assertTrue(callable(tasks["parse_resume"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
