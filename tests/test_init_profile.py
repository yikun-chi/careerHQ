"""Unit tests for init_profile_from_resume (no external API calls)."""

import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

# Add project root for imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.bullet_mapping import BulletContext
from packages.core.domain.occupation_class import (
    Element,
    ElementScale,
    IntervalSemantics,
    Occupation,
    ScaleDefinition,
    ScaleType,
)
from packages.core.domain.resume import ParsedResume, ResumeEducation, ResumeJob, ResumeProject
from packages.core.domain.user_class import User, UserAttributeTemplate
from packages.core.domain.user_service import update_attributes_from_bullet_mappings
from packages.core.domain.bullet_mapping import AttributeMapping, BulletAttributeMapping
from packages.core.use_cases.init_profile_from_resume import (
    _collect_bullets,
    _build_catalog_text,
    _parse_mapping_response,
    init_profile_from_resume,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_leaf_templates() -> Dict[str, UserAttributeTemplate]:
    """Create a small set of leaf templates for testing."""
    return {
        "1.A.1.a.1": UserAttributeTemplate(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
            mapping_element_id="1.A.1.a.1",
            element_name="Oral Comprehension",
            description="Listen and understand spoken info",
        ),
        "3.A.1.a": UserAttributeTemplate(
            attribute_id="3.A.1.a",
            attribute_name="Reading Comprehension",
            mapping_element_id="2.A.1.a",
            element_name="Reading Comprehension",
            description="Understanding written sentences",
        ),
        "3.B.3.e": UserAttributeTemplate(
            attribute_id="3.B.3.e",
            attribute_name="Programming",
            mapping_element_id="2.B.3.e",
            element_name="Programming",
            description="Writing computer programs",
        ),
    }


def _make_occupation(occ_id: str = "15-1252.00", name: str = "Software Developers") -> Occupation:
    """Create a minimal Occupation with one element that has LV+IM scales."""
    lv_def = ScaleDefinition(
        scale_id="LV", scale_name="Level", min_value=0, max_value=7, scale_type=ScaleType.INTERVAL
    )
    im_def = ScaleDefinition(
        scale_id="IM", scale_name="Importance", min_value=1, max_value=5, scale_type=ScaleType.INTERVAL
    )

    elem = Element(element_id="1.A.1.a.1", element_name="Oral Comprehension")
    elem.upsert_scale(
        ElementScale(
            scale_def=lv_def,
            value=4.0,
            interval_semantics=IntervalSemantics(meaning="level"),
        )
    )
    elem.upsert_scale(
        ElementScale(
            scale_def=im_def,
            value=3.5,
            interval_semantics=IntervalSemantics(meaning="importance"),
        )
    )

    return Occupation(
        occupation_id=occ_id,
        occupation_name=name,
        elements={"1.A.1.a.1": elem},
    )


class FakeLLMProvider:
    """Returns canned mapping responses for testing."""

    def __init__(self, mapping_response: Optional[Dict[str, Any]] = None) -> None:
        self.mapping_response = mapping_response or {"mappings": []}
        self.bullet_texts_received: Optional[List[str]] = None

    def parse_resume(
        self,
        *,
        resume_path: Path,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        raise NotImplementedError("FakeLLMProvider should not be asked to parse resumes")

    def map_bullets_to_attributes(
        self,
        *,
        bullet_texts: List[str],
        attribute_catalog_text: str,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        self.bullet_texts_received = bullet_texts
        return dict(self.mapping_response)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCollectBullets(unittest.TestCase):

    def test_job_bullets_use_job_years(self) -> None:
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Engineer",
                company_title="Corp",
                occupation_id="15-1252.00",
                occupation_title="Software Developers",
                years_of_experience=3.0,
                bullet_points=["Built APIs", "Wrote tests"],
                projects=[],
            ),
        ])
        bullets = _collect_bullets(resume)
        self.assertEqual(len(bullets), 2)
        self.assertEqual(bullets[0].years, 3.0)
        self.assertEqual(bullets[0].source, "job")
        self.assertEqual(bullets[1].bullet_index, 1)

    def test_project_bullets_use_one_year(self) -> None:
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Engineer",
                company_title="Corp",
                occupation_id="15-1252.00",
                occupation_title="Software Developers",
                years_of_experience=5.0,
                bullet_points=[],
                projects=[
                    ResumeProject(
                        project_name="Dashboard",
                        bullet_points=["Built realtime dashboard"],
                    ),
                ],
            ),
        ])
        bullets = _collect_bullets(resume)
        self.assertEqual(len(bullets), 1)
        self.assertEqual(bullets[0].years, 1.0)
        self.assertEqual(bullets[0].source, "project")
        self.assertEqual(bullets[0].project_name, "Dashboard")


class TestBuildCatalogText(unittest.TestCase):

    def test_sorted_output(self) -> None:
        templates = _make_leaf_templates()
        text = _build_catalog_text(templates)
        lines = text.strip().split("\n")
        self.assertEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("1.A.1.a.1"))
        self.assertIn("Oral Comprehension", lines[0])


class TestParseMappingResponse(unittest.TestCase):

    def test_valid_response(self) -> None:
        raw = {
            "mappings": [
                {
                    "bullet_index": 0,
                    "attributes": [
                        {"attribute_id": "3.B.3.e", "relevance_score": 0.9},
                    ],
                },
            ],
        }
        result = _parse_mapping_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].bullet_index, 0)
        self.assertEqual(result[0].attributes[0].attribute_id, "3.B.3.e")
        self.assertAlmostEqual(result[0].attributes[0].relevance_score, 0.9)

    def test_skips_malformed_entries(self) -> None:
        raw = {
            "mappings": [
                "not a dict",
                {"bullet_index": "not_int", "attributes": []},
                {"bullet_index": 0, "attributes": [{"attribute_id": 123, "relevance_score": 0.5}]},
            ],
        }
        result = _parse_mapping_response(raw)
        # First two are skipped; third has bullet_index=0 but its attribute has int id -> skipped
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].attributes, [])


class TestUpdateAttributesFromBulletMappings(unittest.TestCase):

    def test_basic_update(self) -> None:
        user = User(user_id="u1")
        templates = _make_leaf_templates()
        bullets = [
            BulletContext(bullet_index=0, text="Built APIs", occupation_title="Dev", source="job", project_name=None, years=3.0),
        ]
        mappings = [
            BulletAttributeMapping(
                bullet_index=0,
                attributes=[AttributeMapping(attribute_id="3.B.3.e", relevance_score=0.8)],
            ),
        ]
        update_attributes_from_bullet_mappings(user, mappings, bullets, templates)

        attr = user.get_attribute("3.B.3.e")
        self.assertIsNotNone(attr)
        self.assertAlmostEqual(attr.capability, 3.0 * 0.8)  # 2.4
        self.assertAlmostEqual(attr.preference, 3.0 * 2)     # 6.0

    def test_invalid_attribute_id_skipped(self) -> None:
        user = User(user_id="u1")
        templates = _make_leaf_templates()
        bullets = [
            BulletContext(bullet_index=0, text="x", occupation_title="Dev", source="job", project_name=None, years=1.0),
        ]
        mappings = [
            BulletAttributeMapping(
                bullet_index=0,
                attributes=[AttributeMapping(attribute_id="FAKE.ID", relevance_score=1.0)],
            ),
        ]
        update_attributes_from_bullet_mappings(user, mappings, bullets, templates)
        self.assertEqual(len(user.attributes), 0)

    def test_relevance_clamped(self) -> None:
        user = User(user_id="u1")
        templates = _make_leaf_templates()
        bullets = [
            BulletContext(bullet_index=0, text="x", occupation_title="Dev", source="job", project_name=None, years=2.0),
        ]
        mappings = [
            BulletAttributeMapping(
                bullet_index=0,
                attributes=[AttributeMapping(attribute_id="3.B.3.e", relevance_score=1.5)],
            ),
        ]
        update_attributes_from_bullet_mappings(user, mappings, bullets, templates)
        attr = user.get_attribute("3.B.3.e")
        # Clamped to 1.0, so capability = 2.0 * 1.0 = 2.0
        self.assertAlmostEqual(attr.capability, 2.0)

    def test_cap_at_100(self) -> None:
        user = User(user_id="u1")
        templates = _make_leaf_templates()
        bullets = [
            BulletContext(bullet_index=0, text="x", occupation_title="Dev", source="job", project_name=None, years=200.0),
        ]
        mappings = [
            BulletAttributeMapping(
                bullet_index=0,
                attributes=[AttributeMapping(attribute_id="3.B.3.e", relevance_score=1.0)],
            ),
        ]
        update_attributes_from_bullet_mappings(user, mappings, bullets, templates)
        attr = user.get_attribute("3.B.3.e")
        self.assertEqual(attr.capability, 100.0)
        self.assertEqual(attr.preference, 100.0)


class TestInitProfileFromResume(unittest.TestCase):

    def test_occupation_only_no_bullets(self) -> None:
        """Job with no bullets -> only occupation-based update runs."""
        user = User(user_id="u1")
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Dev",
                company_title="Corp",
                occupation_id="15-1252.00",
                occupation_title="Software Developers",
                years_of_experience=2.0,
                bullet_points=[],
                projects=[],
            ),
        ])
        occ = _make_occupation()
        provider = FakeLLMProvider()
        result = init_profile_from_resume(
            user, resume, provider, occupations={"15-1252.00": occ}
        )

        self.assertEqual(result.jobs_added, 1)
        self.assertEqual(result.bullets_mapped, 0)
        self.assertEqual(len(user.jobs), 1)
        # Occupation-based update should have created an attribute
        attr = user.get_attribute("1.A.1.a.1")
        self.assertIsNotNone(attr)
        self.assertGreater(attr.capability, 0)

    def test_job_and_bullets_both_update(self) -> None:
        """Both occupation and bullet updates run and accumulate."""
        user = User(user_id="u1")
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Dev",
                company_title="Corp",
                occupation_id="15-1252.00",
                occupation_title="Software Developers",
                years_of_experience=2.0,
                bullet_points=["Built APIs"],
                projects=[],
            ),
        ])
        occ = _make_occupation()
        # LLM maps bullet 0 to the same attribute as occupation
        provider = FakeLLMProvider(mapping_response={
            "mappings": [
                {
                    "bullet_index": 0,
                    "attributes": [
                        {"attribute_id": "1.A.1.a.1", "relevance_score": 0.7},
                    ],
                },
            ],
        })

        result = init_profile_from_resume(
            user, resume, provider, occupations={"15-1252.00": occ}
        )

        self.assertEqual(result.jobs_added, 1)
        self.assertEqual(result.bullets_mapped, 1)

        attr = user.get_attribute("1.A.1.a.1")
        self.assertIsNotNone(attr)
        # Occupation contributes: 2 years * (4.0*3.5)/35 = 2 * 0.4 = 0.8
        # Bullet contributes: 2 years * 0.7 = 1.4
        # Total capability should be 0.8 + 1.4 = 2.2
        self.assertAlmostEqual(attr.capability, 2.2, places=5)

    def test_skipped_occupation(self) -> None:
        """Unknown occupation_id is tracked in skipped_occupations."""
        user = User(user_id="u1")
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Dev",
                company_title="Corp",
                occupation_id="99-9999.00",
                occupation_title="Fake",
                years_of_experience=1.0,
                bullet_points=["Did stuff"],
                projects=[],
            ),
        ])
        provider = FakeLLMProvider(mapping_response={"mappings": []})
        result = init_profile_from_resume(
            user, resume, provider, occupations={}
        )
        self.assertEqual(result.jobs_added, 0)
        self.assertIn("99-9999.00", result.skipped_occupations)

    def test_project_bullets_use_one_year(self) -> None:
        """Project bullets should use 1.0 year regardless of job years."""
        user = User(user_id="u1")
        resume = ParsedResume(jobs=[
            ResumeJob(
                job_title="Dev",
                company_title="Corp",
                occupation_id="15-1252.00",
                occupation_title="Software Developers",
                years_of_experience=5.0,
                bullet_points=[],
                projects=[
                    ResumeProject(
                        project_name="Dashboard",
                        bullet_points=["Built dashboard"],
                    ),
                ],
            ),
        ])
        occ = _make_occupation()
        provider = FakeLLMProvider(mapping_response={
            "mappings": [
                {
                    "bullet_index": 0,
                    "attributes": [
                        {"attribute_id": "3.B.3.e", "relevance_score": 1.0},
                    ],
                },
            ],
        })

        init_profile_from_resume(
            user, resume, provider, occupations={"15-1252.00": occ}
        )

        attr = user.get_attribute("3.B.3.e")
        self.assertIsNotNone(attr)
        # Project bullet: 1.0 year * 1.0 relevance = 1.0 capability
        self.assertAlmostEqual(attr.capability, 1.0)
        # Preference: 1.0 year * 2 = 2.0
        self.assertAlmostEqual(attr.preference, 2.0)


def _make_education_templates() -> Dict[str, UserAttributeTemplate]:
    """Create templates for all 12 education leaf attributes (2.D.1.1–2.D.1.12)."""
    labels = [
        "Less than a High School Diploma",
        "High School Diploma (GED)",
        "Post-Secondary Certificate",
        "Some College Courses",
        "Associate's Degree",
        "Bachelor's Degree",
        "Post-Baccalaureate Certificate",
        "Master's Degree",
        "Post-Master's Certificate",
        "First Professional Degree",
        "Doctoral Degree",
        "Post-Doctoral Training",
    ]
    templates: Dict[str, UserAttributeTemplate] = {}
    for i, label in enumerate(labels, start=1):
        attr_id = f"2.D.1.{i}"
        templates[attr_id] = UserAttributeTemplate(
            attribute_id=attr_id,
            attribute_name=label,
            mapping_element_id=f"2.D.1.{i}",
            element_name=label,
            description=label,
        )
    return templates


class TestEducationBinaryAttributes(unittest.TestCase):

    def test_bachelors_sets_binary_cumulative(self) -> None:
        """Bachelor's (level 6) -> 2.D.1.1-6 True, 2.D.1.7-12 False."""
        user = User(user_id="u1")
        resume = ParsedResume(
            jobs=[],
            education=[
                ResumeEducation(
                    institution="State University",
                    degree="B.S.",
                    field_of_study="Computer Science",
                    graduation_year=2022,
                    education_level=6,
                ),
            ],
        )

        # Merge education templates into the standard leaf templates
        templates = _make_leaf_templates()
        templates.update(_make_education_templates())

        provider = FakeLLMProvider()
        # Monkey-patch get_attribute_template_registry for this test
        import packages.core.use_cases.init_profile_from_resume as mod
        original_fn = mod.get_attribute_template_registry

        class FakeRegistry:
            def get_leaf_templates(self):
                return templates

        mod.get_attribute_template_registry = lambda: FakeRegistry()
        try:
            init_profile_from_resume(user, resume, provider, occupations={})
        finally:
            mod.get_attribute_template_registry = original_fn

        for level in range(1, 7):
            attr = user.get_attribute(f"2.D.1.{level}")
            self.assertIsNotNone(attr, f"2.D.1.{level} should exist")
            self.assertTrue(attr.binary, f"2.D.1.{level} should be True")

        for level in range(7, 13):
            attr = user.get_attribute(f"2.D.1.{level}")
            self.assertIsNotNone(attr, f"2.D.1.{level} should exist")
            self.assertFalse(attr.binary, f"2.D.1.{level} should be False")

    def test_highest_level_wins(self) -> None:
        """Multiple education entries — highest level determines cutoff."""
        user = User(user_id="u1")
        resume = ParsedResume(
            jobs=[],
            education=[
                ResumeEducation(
                    institution="Community College",
                    degree="A.S.",
                    education_level=5,
                ),
                ResumeEducation(
                    institution="State University",
                    degree="M.S.",
                    education_level=8,
                ),
            ],
        )
        templates = _make_leaf_templates()
        templates.update(_make_education_templates())

        provider = FakeLLMProvider()
        import packages.core.use_cases.init_profile_from_resume as mod
        original_fn = mod.get_attribute_template_registry

        class FakeRegistry:
            def get_leaf_templates(self):
                return templates

        mod.get_attribute_template_registry = lambda: FakeRegistry()
        try:
            init_profile_from_resume(user, resume, provider, occupations={})
        finally:
            mod.get_attribute_template_registry = original_fn

        for level in range(1, 9):
            self.assertTrue(user.get_attribute(f"2.D.1.{level}").binary)
        for level in range(9, 13):
            self.assertFalse(user.get_attribute(f"2.D.1.{level}").binary)

    def test_no_education_skips_binary(self) -> None:
        """No education entries -> no education binary attributes set."""
        user = User(user_id="u1")
        resume = ParsedResume(jobs=[], education=[])

        templates = _make_leaf_templates()
        templates.update(_make_education_templates())

        provider = FakeLLMProvider()
        import packages.core.use_cases.init_profile_from_resume as mod
        original_fn = mod.get_attribute_template_registry

        class FakeRegistry:
            def get_leaf_templates(self):
                return templates

        mod.get_attribute_template_registry = lambda: FakeRegistry()
        try:
            init_profile_from_resume(user, resume, provider, occupations={})
        finally:
            mod.get_attribute_template_registry = original_fn

        for level in range(1, 13):
            self.assertIsNone(user.get_attribute(f"2.D.1.{level}"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
