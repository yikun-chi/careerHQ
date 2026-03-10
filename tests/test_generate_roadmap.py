"""Unit tests for career roadmap generation logic."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.occupation_class import (
    Element,
    ElementScale,
    IntervalSemantics,
    Occupation,
    ScaleDefinition,
    ScaleType,
)
from packages.core.domain.user_class import User, UserAttribute
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IM_DEF = ScaleDefinition(scale_id="IM", scale_name="Importance", min_value=1, max_value=5, scale_type=ScaleType.INTERVAL)
LV_DEF = ScaleDefinition(scale_id="LV", scale_name="Level", min_value=0, max_value=7, scale_type=ScaleType.INTERVAL)
WI_DEF = ScaleDefinition(scale_id="WI", scale_name="Work Importance", min_value=-3, max_value=3, scale_type=ScaleType.INTERVAL)
IVAL = IntervalSemantics(meaning="test")


def _make_element_im_lv(eid: str, im_val: float, lv_val: float) -> Element:
    """Create element with both IM and LV scales."""
    elem = Element(element_id=eid, element_name=f"Elem {eid}")
    elem.upsert_scale(ElementScale(scale_def=IM_DEF, value=im_val, interval_semantics=IVAL))
    elem.upsert_scale(ElementScale(scale_def=LV_DEF, value=lv_val, interval_semantics=IVAL))
    return elem


def _make_element_wi(eid: str, wi_val: float) -> Element:
    """Create element with WI scale."""
    elem = Element(element_id=eid, element_name=f"Elem {eid}")
    elem.upsert_scale(ElementScale(scale_def=WI_DEF, value=wi_val, interval_semantics=IVAL))
    return elem


def _make_user_with_attrs(attrs: dict) -> User:
    """Create user with attributes. attrs: {attr_id: (capability, mapping_element_id)}"""
    user = User(user_id="test")
    for attr_id, (cap, eid) in attrs.items():
        user.add_attribute(UserAttribute(
            attribute_id=attr_id,
            attribute_name=f"Attr {attr_id}",
            mapping_element_id=eid,
            capability=cap,
        ))
    return user


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildRoadmapSchema(unittest.TestCase):

    def test_schema_is_valid_object(self):
        schema = build_roadmap_schema()
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])

    def test_required_top_level_fields(self):
        schema = build_roadmap_schema()
        required = schema["required"]
        self.assertIn("roadmap_title", required)
        self.assertIn("estimated_timeline_months", required)
        self.assertIn("summary", required)
        self.assertIn("milestones", required)

    def test_milestones_array_bounds(self):
        schema = build_roadmap_schema()
        milestones = schema["properties"]["milestones"]
        self.assertEqual(milestones["type"], "array")
        self.assertEqual(milestones["minItems"], 4)
        self.assertEqual(milestones["maxItems"], 6)

    def test_actions_array_bounds(self):
        schema = build_roadmap_schema()
        actions = schema["properties"]["milestones"]["items"]["properties"]["actions"]
        self.assertEqual(actions["minItems"], 2)
        self.assertEqual(actions["maxItems"], 4)

    def test_resources_array_bounds(self):
        schema = build_roadmap_schema()
        resources = (
            schema["properties"]["milestones"]["items"]
            ["properties"]["actions"]["items"]
            ["properties"]["resources"]
        )
        self.assertEqual(resources["minItems"], 2)
        self.assertEqual(resources["maxItems"], 3)

    def test_milestone_type_enum_values(self):
        schema = build_roadmap_schema()
        mt = schema["properties"]["milestones"]["items"]["properties"]["milestone_type"]
        self.assertIn("skill_building", mt["enum"])
        self.assertIn("certification", mt["enum"])
        self.assertIn("networking", mt["enum"])

    def test_action_type_enum_values(self):
        schema = build_roadmap_schema()
        at = (
            schema["properties"]["milestones"]["items"]
            ["properties"]["actions"]["items"]
            ["properties"]["action_type"]
        )
        self.assertIn("learn", at["enum"])
        self.assertIn("certify", at["enum"])
        self.assertIn("network", at["enum"])

    def test_resource_type_enum_values(self):
        schema = build_roadmap_schema()
        rt = (
            schema["properties"]["milestones"]["items"]
            ["properties"]["actions"]["items"]
            ["properties"]["resources"]["items"]
            ["properties"]["resource_type"]
        )
        self.assertIn("course", rt["enum"])
        self.assertIn("book", rt["enum"])
        self.assertIn("community", rt["enum"])


class TestBuildRoadmapInstructions(unittest.TestCase):

    def test_contains_key_phrases(self):
        instructions = build_roadmap_instructions()
        self.assertIn("career coach", instructions)
        self.assertIn("gap analysis", instructions)
        self.assertIn("4-6 milestones", instructions)
        self.assertIn("2-3 specific, real resources", instructions)

    def test_returns_string(self):
        self.assertIsInstance(build_roadmap_instructions(), str)


class TestBuildRoadmapUserText(unittest.TestCase):

    def test_includes_current_role(self):
        text = build_roadmap_user_text(
            current_job_title="Software Engineer",
            current_occupation_name="Software Developers",
            target_occupation_id="11-1021.00",
            target_occupation_name="General Managers",
            gap_analysis=[],
            user_strengths=[],
            education=[],
            skills=[],
        )
        self.assertIn("Software Engineer", text)
        self.assertIn("Software Developers", text)

    def test_includes_target_role(self):
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=[],
            education=[],
            skills=[],
        )
        self.assertIn("15-1252.00", text)
        self.assertIn("Software Developers", text)

    def test_includes_gap_analysis(self):
        gaps = [
            {"attribute_name": "Programming", "category": "Basic Skills",
             "user_score": 30.0, "target_score": 80.0, "gap": 50.0}
        ]
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=gaps,
            user_strengths=[],
            education=[],
            skills=[],
        )
        self.assertIn("Programming", text)
        self.assertIn("gap=50.0", text)

    def test_includes_strengths(self):
        strengths = [
            {"attribute_name": "Critical Thinking", "category": "Abilities",
             "user_score": 85.0}
        ]
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=strengths,
            education=[],
            skills=[],
        )
        self.assertIn("Critical Thinking", text)
        self.assertIn("score=85.0", text)

    def test_includes_education(self):
        education = [
            {"degree": "B.S.", "field": "Computer Science", "institution": "Stanford"}
        ]
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=[],
            education=education,
            skills=[],
        )
        self.assertIn("B.S.", text)
        self.assertIn("Computer Science", text)
        self.assertIn("Stanford", text)

    def test_includes_skills(self):
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=[],
            education=[],
            skills=["Python", "SQL", "Tableau"],
        )
        self.assertIn("Python", text)
        self.assertIn("SQL", text)

    def test_includes_career_preferences(self):
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=[],
            education=[],
            skills=[],
            career_preferences="I prefer remote work in AI industry",
        )
        self.assertIn("remote work", text)
        self.assertIn("AI industry", text)

    def test_omits_empty_sections(self):
        text = build_roadmap_user_text(
            current_job_title="Analyst",
            current_occupation_name="Analysts",
            target_occupation_id="15-1252.00",
            target_occupation_name="Software Developers",
            gap_analysis=[],
            user_strengths=[],
            education=[],
            skills=[],
            career_preferences="",
        )
        self.assertNotIn("Skill/Ability Gaps", text)
        self.assertNotIn("Existing Strengths", text)
        self.assertNotIn("Education Background", text)
        self.assertNotIn("Skills from Resume", text)
        self.assertNotIn("Career Preferences", text)


class TestComputeGapAnalysis(unittest.TestCase):

    def test_identifies_gaps(self):
        """User with low capability + target with high importance = gap."""
        user = _make_user_with_attrs({
            "1.A.1.a.1": (20.0, "1.A.1.a.1"),  # low capability
        })

        occ = Occupation(occupation_id="test", occupation_name="Test Occ")
        # IM=4, LV=5 -> normalized = 4*5/35*100 = 57.1
        occ.elements["1.A.1.a.1"] = _make_element_im_lv("1.A.1.a.1", 4.0, 5.0)

        gaps, strengths = compute_gap_analysis(user, occ)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["attribute_name"], "Attr 1.A.1.a.1")
        self.assertEqual(gaps[0]["category"], "Abilities")
        self.assertGreater(gaps[0]["gap"], 10)

    def test_identifies_strengths(self):
        """User with high capability = strength."""
        user = _make_user_with_attrs({
            "1.A.1.a.1": (80.0, "1.A.1.a.1"),
        })

        occ = Occupation(occupation_id="test", occupation_name="Test Occ")
        # IM=4, LV=5 -> normalized = 57.1, user=80, gap=-22.9 (no gap)
        occ.elements["1.A.1.a.1"] = _make_element_im_lv("1.A.1.a.1", 4.0, 5.0)

        gaps, strengths = compute_gap_analysis(user, occ)

        self.assertEqual(len(gaps), 0)
        self.assertEqual(len(strengths), 1)
        self.assertEqual(strengths[0]["user_score"], 80.0)

    def test_work_styles_gap(self):
        """Work styles (1.D prefix) use WI scale."""
        user = _make_user_with_attrs({
            "1.D.1.a": (10.0, "1.D.1.a"),
        })

        occ = Occupation(occupation_id="test", occupation_name="Test Occ")
        # WI=2 -> normalized = (2+3)/6*100 = 83.3
        occ.elements["1.D.1.a"] = _make_element_wi("1.D.1.a", 2.0)

        gaps, strengths = compute_gap_analysis(user, occ)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["category"], "Work Styles")

    def test_cross_prefix_skills_gap(self):
        """User 3.A attributes map to O*NET 2.A elements."""
        user = _make_user_with_attrs({
            "3.A.1.a": (15.0, "2.A.1.a"),  # user prefix 3.A, maps to onet 2.A
        })

        occ = Occupation(occupation_id="test", occupation_name="Test Occ")
        occ.elements["2.A.1.a"] = _make_element_im_lv("2.A.1.a", 4.5, 6.0)

        gaps, strengths = compute_gap_analysis(user, occ)

        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["category"], "Basic Skills")

    def test_limits_results(self):
        """Should limit gaps to 15 and strengths to 10."""
        user = User(user_id="test")
        occ = Occupation(occupation_id="test", occupation_name="Test Occ")

        # Create 20 attributes with gaps
        for i in range(20):
            eid = f"1.A.1.a.{i}"
            user.add_attribute(UserAttribute(
                attribute_id=eid,
                attribute_name=f"Ability {i}",
                mapping_element_id=eid,
                capability=5.0,  # low
            ))
            occ.elements[eid] = _make_element_im_lv(eid, 5.0, 7.0)

        gaps, strengths = compute_gap_analysis(user, occ)
        self.assertLessEqual(len(gaps), 15)

    def test_no_element_in_target_skipped(self):
        """Attributes with no matching element in target are skipped."""
        user = _make_user_with_attrs({
            "1.A.1.a.1": (50.0, "1.A.1.a.1"),
        })

        # Empty occupation - no elements
        occ = Occupation(occupation_id="test", occupation_name="Test Occ")

        gaps, strengths = compute_gap_analysis(user, occ)
        self.assertEqual(len(gaps), 0)
        self.assertEqual(len(strengths), 0)

    def test_gaps_sorted_by_magnitude(self):
        """Gaps should be sorted largest first."""
        user = _make_user_with_attrs({
            "1.A.1.a.1": (10.0, "1.A.1.a.1"),
            "1.A.1.a.2": (30.0, "1.A.1.a.2"),
        })

        occ = Occupation(occupation_id="test", occupation_name="Test Occ")
        # Both have same target score; first has bigger gap
        occ.elements["1.A.1.a.1"] = _make_element_im_lv("1.A.1.a.1", 5.0, 7.0)
        occ.elements["1.A.1.a.2"] = _make_element_im_lv("1.A.1.a.2", 5.0, 7.0)

        gaps, _ = compute_gap_analysis(user, occ)

        self.assertEqual(len(gaps), 2)
        self.assertGreaterEqual(gaps[0]["gap"], gaps[1]["gap"])


class TestBuildLinkValidationSchema(unittest.TestCase):

    def test_top_level_structure(self):
        schema = build_link_validation_schema()
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("all_valid", schema["required"])
        self.assertIn("results", schema["required"])

    def test_all_valid_is_boolean(self):
        schema = build_link_validation_schema()
        self.assertEqual(schema["properties"]["all_valid"]["type"], "boolean")

    def test_results_is_array(self):
        schema = build_link_validation_schema()
        self.assertEqual(schema["properties"]["results"]["type"], "array")

    def test_result_item_no_additional_properties(self):
        schema = build_link_validation_schema()
        item = schema["properties"]["results"]["items"]
        self.assertFalse(item["additionalProperties"])

    def test_result_item_required_fields(self):
        schema = build_link_validation_schema()
        required = schema["properties"]["results"]["items"]["required"]
        self.assertIn("url", required)
        self.assertIn("is_valid", required)
        self.assertIn("reason", required)
        self.assertIn("suggested_url", required)

    def test_result_item_field_types(self):
        schema = build_link_validation_schema()
        props = schema["properties"]["results"]["items"]["properties"]
        self.assertEqual(props["url"]["type"], "string")
        self.assertEqual(props["is_valid"]["type"], "boolean")
        self.assertEqual(props["reason"]["type"], "string")
        self.assertEqual(props["suggested_url"]["type"], "string")


class TestExtractResourcesFromRoadmap(unittest.TestCase):

    def _make_roadmap(self, milestones):
        return {"milestones": milestones}

    def test_extracts_all_resources(self):
        roadmap = self._make_roadmap([
            {"actions": [
                {"resources": [
                    {"url": "https://a.com", "resource_name": "A"},
                    {"url": "https://b.com", "resource_name": "B"},
                ]},
            ]},
            {"actions": [
                {"resources": [
                    {"url": "https://c.com", "resource_name": "C"},
                ]},
            ]},
        ])
        result = extract_resources_from_roadmap(roadmap)
        self.assertEqual(len(result), 3)
        urls = [r["url"] for r in result]
        self.assertIn("https://a.com", urls)
        self.assertIn("https://c.com", urls)

    def test_skips_empty_url(self):
        roadmap = self._make_roadmap([
            {"actions": [
                {"resources": [
                    {"url": "", "resource_name": "Empty"},
                    {"url": "https://valid.com", "resource_name": "Valid"},
                ]},
            ]},
        ])
        result = extract_resources_from_roadmap(roadmap)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["url"], "https://valid.com")

    def test_skips_missing_url_key(self):
        roadmap = self._make_roadmap([
            {"actions": [
                {"resources": [
                    {"resource_name": "No URL key"},
                    {"url": "https://present.com", "resource_name": "Has URL"},
                ]},
            ]},
        ])
        result = extract_resources_from_roadmap(roadmap)
        self.assertEqual(len(result), 1)

    def test_empty_milestones(self):
        result = extract_resources_from_roadmap({"milestones": []})
        self.assertEqual(result, [])

    def test_no_milestones_key(self):
        result = extract_resources_from_roadmap({})
        self.assertEqual(result, [])

    def test_multi_milestone_multi_action(self):
        roadmap = self._make_roadmap([
            {"actions": [
                {"resources": [{"url": "https://1.com"}, {"url": "https://2.com"}]},
                {"resources": [{"url": "https://3.com"}]},
            ]},
            {"actions": [
                {"resources": [{"url": "https://4.com"}]},
            ]},
        ])
        result = extract_resources_from_roadmap(roadmap)
        self.assertEqual(len(result), 4)


class TestPatchRoadmapUrls(unittest.TestCase):

    def _make_roadmap(self, resources_per_action):
        return {
            "milestones": [
                {"actions": [
                    {"resources": resources}
                    for resources in resources_per_action
                ]}
            ]
        }

    def test_patches_invalid_url(self):
        roadmap = self._make_roadmap([[
            {"url": "https://bad.example/fake", "resource_name": "X"},
        ]])
        patch_roadmap_urls(roadmap, {"https://bad.example/fake": "https://good.example/real"})
        resource = roadmap["milestones"][0]["actions"][0]["resources"][0]
        self.assertEqual(resource["url"], "https://good.example/real")

    def test_leaves_valid_url_unchanged(self):
        roadmap = self._make_roadmap([[
            {"url": "https://coursera.org/learn/python", "resource_name": "Python"},
        ]])
        patch_roadmap_urls(roadmap, {})
        resource = roadmap["milestones"][0]["actions"][0]["resources"][0]
        self.assertEqual(resource["url"], "https://coursera.org/learn/python")

    def test_patches_only_matching_urls(self):
        roadmap = self._make_roadmap([[
            {"url": "https://bad.com/fake", "resource_name": "Bad"},
            {"url": "https://good.com/real", "resource_name": "Good"},
        ]])
        patch_roadmap_urls(roadmap, {"https://bad.com/fake": "https://replacement.com"})
        resources = roadmap["milestones"][0]["actions"][0]["resources"]
        self.assertEqual(resources[0]["url"], "https://replacement.com")
        self.assertEqual(resources[1]["url"], "https://good.com/real")

    def test_handles_resource_without_url_key(self):
        roadmap = self._make_roadmap([[
            {"resource_name": "No URL"},
        ]])
        # Should not raise
        patch_roadmap_urls(roadmap, {"https://something.com": "https://other.com"})

    def test_empty_replacements_no_mutation(self):
        roadmap = self._make_roadmap([[
            {"url": "https://original.com", "resource_name": "R"},
        ]])
        patch_roadmap_urls(roadmap, {})
        self.assertEqual(
            roadmap["milestones"][0]["actions"][0]["resources"][0]["url"],
            "https://original.com",
        )


if __name__ == "__main__":
    unittest.main()
