"""Unit tests for career match refinement prompt helpers."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.use_cases.refine_career_matches import (
    build_refine_career_instructions,
    build_refine_career_schema,
    build_refine_career_user_text,
)


class TestRefineCareerHelpers(unittest.TestCase):

    def test_schema_requires_exact_top3(self):
        schema = build_refine_career_schema()
        top = schema["properties"]["top_careers"]
        self.assertEqual(top["minItems"], 3)
        self.assertEqual(top["maxItems"], 3)

    def test_user_text_contains_answers_and_matches(self):
        text = build_refine_career_user_text(
            matches=[
                {
                    "occupation_id": "11-1011.00",
                    "occupation_name": "Chief Executives",
                    "match_count": 4,
                    "total_categories": 6,
                    "matched_categories": ["Abilities", "Knowledge"],
                }
            ],
            answers=[
                {
                    "question": "Preferred environment?",
                    "answer": "Remote with occasional travel",
                }
            ],
        )
        self.assertIn("Preferred environment?", text)
        self.assertIn("Chief Executives", text)
        self.assertIn("match score: 4/6", text)

    def test_instructions_constrain_to_provided_matches(self):
        instructions = build_refine_career_instructions()
        self.assertIn("provided list only", instructions)
        self.assertIn("Return only valid JSON", instructions)


if __name__ == "__main__":
    unittest.main()
