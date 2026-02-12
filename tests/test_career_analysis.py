"""Unit tests for career analysis matching logic."""

import sys
import unittest
from pathlib import Path
from typing import Dict

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
from packages.core.use_cases.career_analysis import (
    CareerMatch,
    find_matching_occupations,
    _get_user_top3,
    _get_occ_top3,
    _get_occ_top3_interests,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

IM_DEF = ScaleDefinition(scale_id="IM", scale_name="Importance", min_value=1, max_value=5, scale_type=ScaleType.INTERVAL)
WI_DEF = ScaleDefinition(scale_id="WI", scale_name="Work Importance", min_value=-3, max_value=3, scale_type=ScaleType.INTERVAL)
OI_DEF = ScaleDefinition(scale_id="OI", scale_name="Occupational Interests", min_value=1, max_value=7, scale_type=ScaleType.INTERVAL)
EX_DEF = ScaleDefinition(scale_id="EX", scale_name="Extent", min_value=1, max_value=7, scale_type=ScaleType.INTERVAL)
IVAL = IntervalSemantics(meaning="test")


def _make_element(eid: str, name: str, scale_def: ScaleDefinition, value: float) -> Element:
    elem = Element(element_id=eid, element_name=name)
    elem.upsert_scale(ElementScale(scale_def=scale_def, value=value, interval_semantics=IVAL))
    return elem


def _make_user_with_abilities(top_eids: Dict[str, float]) -> User:
    """Create a user with ability attributes (prefix 1.A).

    top_eids: mapping from element_id to capability value.
    User attribute_id == mapping_element_id for abilities (both 1.A prefix).
    """
    user = User(user_id="test")
    for eid, cap in top_eids.items():
        user.add_attribute(UserAttribute(
            attribute_id=eid,
            attribute_name=f"Ability {eid}",
            mapping_element_id=eid,
            capability=cap,
        ))
    return user


def _make_occupation_with_abilities(occ_id: str, name: str, elements: Dict[str, float]) -> Occupation:
    """Create an occupation with ability elements (prefix 1.A) using IM scale."""
    occ = Occupation(occupation_id=occ_id, occupation_name=name)
    for eid, value in elements.items():
        occ.elements[eid] = _make_element(eid, f"Elem {eid}", IM_DEF, value)
    return occ


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetUserTop3(unittest.TestCase):

    def test_returns_top3_by_capability(self):
        user = _make_user_with_abilities({
            "1.A.1.a": 90,
            "1.A.1.b": 70,
            "1.A.1.c": 50,
            "1.A.1.d": 30,
        })
        top = _get_user_top3(user, "1.A")
        self.assertEqual(len(top), 3)
        self.assertEqual(top, ["1.A.1.a", "1.A.1.b", "1.A.1.c"])

    def test_skips_zero_capability(self):
        user = _make_user_with_abilities({
            "1.A.1.a": 10,
            "1.A.1.b": 0,
        })
        top = _get_user_top3(user, "1.A")
        self.assertEqual(top, ["1.A.1.a"])

    def test_only_matching_prefix(self):
        user = _make_user_with_abilities({"1.A.1.a": 50})
        # Add a non-ability attribute
        user.add_attribute(UserAttribute(
            attribute_id="3.A.1.a",
            attribute_name="Reading",
            mapping_element_id="2.A.1.a",
            capability=99,
        ))
        top = _get_user_top3(user, "1.A")
        self.assertEqual(top, ["1.A.1.a"])


class TestGetOccTop3(unittest.TestCase):

    def test_returns_top3_by_scale(self):
        occ = _make_occupation_with_abilities("11-1011.00", "Test", {
            "1.A.1.a": 5.0,
            "1.A.1.b": 4.0,
            "1.A.1.c": 3.0,
            "1.A.1.d": 2.0,
        })
        top = _get_occ_top3(occ, "1.A", "IM")
        self.assertEqual(len(top), 3)
        self.assertEqual(top, ["1.A.1.a", "1.A.1.b", "1.A.1.c"])


class TestGetOccTop3Interests(unittest.TestCase):

    def test_combines_oi_and_ex(self):
        occ = Occupation(occupation_id="11-1011.00", occupation_name="Test")
        # Interest with OI scale
        occ.elements["1.B.1.a"] = _make_element("1.B.1.a", "Realistic", OI_DEF, 6.0)
        occ.elements["1.B.1.b"] = _make_element("1.B.1.b", "Investigative", OI_DEF, 3.0)
        # Work value with EX scale
        occ.elements["1.B.2.a"] = _make_element("1.B.2.a", "Achievement", EX_DEF, 5.0)
        occ.elements["1.B.2.b"] = _make_element("1.B.2.b", "Independence", EX_DEF, 4.0)

        top = _get_occ_top3_interests(occ)
        self.assertEqual(len(top), 3)
        # Ranked: 6.0, 5.0, 4.0
        self.assertEqual(top, ["1.B.1.a", "1.B.2.a", "1.B.2.b"])


class TestFindMatchingOccupations(unittest.TestCase):

    def test_perfect_match(self):
        """User's top 3 abilities perfectly overlap with occupation's top 3."""
        user = _make_user_with_abilities({
            "1.A.1.a": 90,
            "1.A.1.b": 80,
            "1.A.1.c": 70,
        })
        occ = _make_occupation_with_abilities("11-1011.00", "Manager", {
            "1.A.1.a": 5.0,
            "1.A.1.b": 4.5,
            "1.A.1.c": 4.0,
            "1.A.1.d": 1.0,
        })
        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_count, 1)
        self.assertIn("Abilities", matches[0].matched_categories)

    def test_partial_overlap_meets_threshold(self):
        """2 of 3 overlap -> still a match."""
        user = _make_user_with_abilities({
            "1.A.1.a": 90,
            "1.A.1.b": 80,
            "1.A.1.c": 70,
        })
        occ = _make_occupation_with_abilities("11-1011.00", "Manager", {
            "1.A.1.a": 5.0,
            "1.A.1.b": 4.5,
            "1.A.1.d": 4.0,  # different from user's 3rd
        })
        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 1)

    def test_insufficient_overlap_no_match(self):
        """Only 1 of 3 overlap -> no match."""
        user = _make_user_with_abilities({
            "1.A.1.a": 90,
            "1.A.1.b": 80,
            "1.A.1.c": 70,
        })
        occ = _make_occupation_with_abilities("11-1011.00", "Manager", {
            "1.A.1.a": 5.0,
            "1.A.1.d": 4.5,
            "1.A.1.e": 4.0,
        })
        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 0)

    def test_too_few_user_attributes_skips_category(self):
        """User has only 1 scored ability -> category is skipped."""
        user = _make_user_with_abilities({"1.A.1.a": 50})
        occ = _make_occupation_with_abilities("11-1011.00", "Manager", {
            "1.A.1.a": 5.0,
            "1.A.1.b": 4.5,
            "1.A.1.c": 4.0,
        })
        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 0)

    def test_multiple_categories(self):
        """User with abilities + work styles -> can match on both."""
        user = User(user_id="test")
        # Abilities (prefix 1.A)
        for eid, cap in [("1.A.1.a", 90), ("1.A.1.b", 80), ("1.A.1.c", 70)]:
            user.add_attribute(UserAttribute(
                attribute_id=eid, attribute_name=f"Ability {eid}",
                mapping_element_id=eid, capability=cap,
            ))
        # Work Styles (prefix 1.D) — user attr_id = onet element_id for this category
        for eid, cap in [("1.D.1.a", 60), ("1.D.1.b", 50), ("1.D.1.c", 40)]:
            user.add_attribute(UserAttribute(
                attribute_id=eid, attribute_name=f"Style {eid}",
                mapping_element_id=eid, capability=cap,
            ))

        occ = Occupation(occupation_id="11-1011.00", occupation_name="Manager")
        # Abilities matching
        for eid, val in [("1.A.1.a", 5.0), ("1.A.1.b", 4.5), ("1.A.1.c", 4.0)]:
            occ.elements[eid] = _make_element(eid, f"Elem {eid}", IM_DEF, val)
        # Work Styles matching
        for eid, val in [("1.D.1.a", 3.0), ("1.D.1.b", 2.5), ("1.D.1.c", 2.0)]:
            occ.elements[eid] = _make_element(eid, f"Elem {eid}", WI_DEF, val)

        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].match_count, 2)
        self.assertEqual(matches[0].total_categories, 2)
        self.assertIn("Abilities", matches[0].matched_categories)
        self.assertIn("Work Styles", matches[0].matched_categories)

    def test_results_sorted_descending(self):
        """Occupations are sorted by match_count descending."""
        user = User(user_id="test")
        # Abilities
        for eid, cap in [("1.A.1.a", 90), ("1.A.1.b", 80), ("1.A.1.c", 70)]:
            user.add_attribute(UserAttribute(
                attribute_id=eid, attribute_name=f"A {eid}",
                mapping_element_id=eid, capability=cap,
            ))
        # Work Styles
        for eid, cap in [("1.D.1.a", 60), ("1.D.1.b", 50), ("1.D.1.c", 40)]:
            user.add_attribute(UserAttribute(
                attribute_id=eid, attribute_name=f"S {eid}",
                mapping_element_id=eid, capability=cap,
            ))

        # occ1 matches both categories
        occ1 = Occupation(occupation_id="1", occupation_name="Both")
        for eid, val in [("1.A.1.a", 5.0), ("1.A.1.b", 4.5), ("1.A.1.c", 4.0)]:
            occ1.elements[eid] = _make_element(eid, f"E {eid}", IM_DEF, val)
        for eid, val in [("1.D.1.a", 3.0), ("1.D.1.b", 2.5), ("1.D.1.c", 2.0)]:
            occ1.elements[eid] = _make_element(eid, f"E {eid}", WI_DEF, val)

        # occ2 matches only abilities
        occ2 = Occupation(occupation_id="2", occupation_name="AbilitiesOnly")
        for eid, val in [("1.A.1.a", 5.0), ("1.A.1.b", 4.5), ("1.A.1.c", 4.0)]:
            occ2.elements[eid] = _make_element(eid, f"E {eid}", IM_DEF, val)

        matches = find_matching_occupations(user, {"1": occ1, "2": occ2})
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0].occupation_name, "Both")
        self.assertEqual(matches[0].match_count, 2)
        self.assertEqual(matches[1].occupation_name, "AbilitiesOnly")
        self.assertEqual(matches[1].match_count, 1)

    def test_max_15_results(self):
        """At most 15 results are returned."""
        user = _make_user_with_abilities({
            "1.A.1.a": 90,
            "1.A.1.b": 80,
            "1.A.1.c": 70,
        })
        occs = {}
        for i in range(20):
            occ = _make_occupation_with_abilities(f"{i}", f"Occ{i}", {
                "1.A.1.a": 5.0,
                "1.A.1.b": 4.5,
                "1.A.1.c": 4.0,
            })
            occs[f"{i}"] = occ

        matches = find_matching_occupations(user, occs)
        self.assertLessEqual(len(matches), 15)

    def test_empty_user_returns_empty(self):
        """User with no attributes -> no matches."""
        user = User(user_id="test")
        occ = _make_occupation_with_abilities("11-1011.00", "Manager", {
            "1.A.1.a": 5.0, "1.A.1.b": 4.5, "1.A.1.c": 4.0,
        })
        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(matches, [])

    def test_cross_prefix_skills(self):
        """Basic Skills use user prefix 3.A but onet prefix 2.A."""
        user = User(user_id="test")
        # User attributes with prefix 3.A, mapping to 2.A
        for uid, eid, cap in [
            ("3.A.1.a", "2.A.1.a", 90),
            ("3.A.1.b", "2.A.1.b", 80),
            ("3.A.1.c", "2.A.1.c", 70),
        ]:
            user.add_attribute(UserAttribute(
                attribute_id=uid, attribute_name=f"Skill {uid}",
                mapping_element_id=eid, capability=cap,
            ))

        occ = Occupation(occupation_id="11-1011.00", occupation_name="Manager")
        for eid, val in [("2.A.1.a", 5.0), ("2.A.1.b", 4.5), ("2.A.1.c", 4.0)]:
            occ.elements[eid] = _make_element(eid, f"E {eid}", IM_DEF, val)

        matches = find_matching_occupations(user, {"11-1011.00": occ})
        self.assertEqual(len(matches), 1)
        self.assertIn("Basic Skills", matches[0].matched_categories)


class TestCareerMatchDataclass(unittest.TestCase):

    def test_fields(self):
        m = CareerMatch(
            occupation_id="15-1252.00",
            occupation_name="Software Developers",
            match_count=5,
            total_categories=6,
            matched_categories=["Abilities", "Knowledge"],
        )
        self.assertEqual(m.occupation_id, "15-1252.00")
        self.assertEqual(m.match_count, 5)
        self.assertEqual(len(m.matched_categories), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
