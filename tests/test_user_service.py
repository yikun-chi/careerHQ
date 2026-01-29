"""
Test suite for user_service module.

Tests the job experience flow and attribute update logic.
Run with: pytest tests/test_user_service.py -v -s
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import from packages
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.user_class import User, Job, UserAttribute
from packages.core.domain.user_service import (
    add_job_experience,
    update_user_attributes_from_job,
    update_attributes_with_element_mapping,
    _get_job_years,
    _calculate_experience_score,
)
from packages.core.domain.user_initialize import (
    get_attribute_template_registry,
    get_leaf_attribute_templates,
)
from packages.core.domain.occupation_populate import load_occupations


class TestGetJobYears:
    """Tests for _get_job_years helper function."""

    def test_duration_months_provided(self):
        """Test that duration_months is used when provided."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=36,  # 3 years
        )
        years = _get_job_years(job)
        assert years == 3.0

    def test_duration_months_fractional(self):
        """Test fractional years from duration_months."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=18,  # 1.5 years
        )
        years = _get_job_years(job)
        assert years == 1.5

    def test_start_end_dates(self):
        """Test calculation from start and end dates."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
            start_date="2020-01-01",
            end_date="2023-01-01",  # 3 years
        )
        years = _get_job_years(job)
        assert 2.9 < years < 3.1  # Allow some tolerance for leap years

    def test_default_one_year(self):
        """Test default of 1 year when no duration info."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
        )
        years = _get_job_years(job)
        assert years == 1.0


class TestCalculateExperienceScore:
    """Tests for _calculate_experience_score helper function."""

    def test_lv_im_scales(self):
        """Test experience score calculation for LV + IM scales."""
        occupations = load_occupations()
        ceo = occupations["11-1011.00"]

        # Oral Comprehension (1.A.1.a.1) - LV=4.88, IM=4.62
        element = ceo.elements["1.A.1.a.1"]
        score = _calculate_experience_score(element)

        # Expected: (4.88 * 4.62) / 35 = 0.644
        assert 0.64 < score < 0.65
        print(f"\nOral Comprehension score: {score:.3f}")

    def test_oi_scale(self):
        """Test experience score calculation for OI scale (Interests)."""
        occupations = load_occupations()
        ceo = occupations["11-1011.00"]

        # Enterprising (1.B.1.e) - should have OI scale
        if "1.B.1.e" in ceo.elements:
            element = ceo.elements["1.B.1.e"]
            score = _calculate_experience_score(element)
            # OI range is 1-7, so score should be between 0.14 and 1.0
            assert 0.0 <= score <= 1.0
            print(f"\nEnterprising interest score: {score:.3f}")

    def test_wi_scale(self):
        """Test experience score calculation for WI scale (Work Styles)."""
        occupations = load_occupations()
        ceo = occupations["11-1011.00"]

        # Leadership (1.D.1.i) - should have WI scale
        if "1.D.1.i" in ceo.elements:
            element = ceo.elements["1.D.1.i"]
            score = _calculate_experience_score(element)
            # WI range is -3 to 3, normalized to 0-1
            assert 0.0 <= score <= 1.0
            print(f"\nLeadership work style score: {score:.3f}")

    def test_category_scale(self):
        """Test experience score for category distribution scales."""
        occupations = load_occupations()
        ceo = occupations["11-1011.00"]

        # Education (2.D.1) - has RL scales
        element = ceo.elements["2.D.1"]
        score = _calculate_experience_score(element)
        # Should use highest percentage / 100
        assert 0.0 <= score <= 1.0
        print(f"\nEducation category score: {score:.3f}")


class TestAddJobExperience:
    """Tests for add_job_experience function."""

    def test_add_job_to_user(self):
        """Test that adding a job experience adds it to user.jobs."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1", user_name="Test User")
        assert len(user.jobs) == 0

        job = add_job_experience(
            user=user,
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=36,
        )

        assert len(user.jobs) == 1
        assert user.jobs[0] == job
        assert job.occupation_id == "11-1011.00"
        assert job.occupation_name == "Chief Executives"
        assert job.job_title == "CEO"
        assert job.company_name == "Acme Corp"
        assert job.duration_months == 36

    def test_job_elements_copied(self):
        """Test that job gets a copy of occupation elements."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")
        job = add_job_experience(
            user=user,
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=12,
        )

        # Job should have elements copied from occupation
        assert len(job.elements) > 0
        assert "1.A.1.a.1" in job.elements  # Oral Comprehension

        # Check that values are copied
        oral_comp = job.elements["1.A.1.a.1"]
        im_scale = oral_comp.get_scale("IM")
        assert im_scale is not None
        assert im_scale.value is not None

    def test_user_attributes_updated(self):
        """Test that user attributes are updated after adding job."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")
        assert len(user.attributes) == 0

        add_job_experience(
            user=user,
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=36,  # 3 years
        )

        # User should now have some attributes
        assert len(user.attributes) > 0
        print(f"\nUser has {len(user.attributes)} attributes after adding job")

        # Check a specific attribute
        oral_comp_attr = user.get_attribute("1.A.1.a.1")
        if oral_comp_attr:
            print(f"  Oral Comprehension: capability={oral_comp_attr.capability}, "
                  f"preference={oral_comp_attr.preference}")
            assert oral_comp_attr.capability is not None
            assert oral_comp_attr.preference is not None


class TestUpdateAttributesWithElementMapping:
    """Tests for update_attributes_with_element_mapping function."""

    def test_capability_increases_with_years(self):
        """Test that capability increases based on years of experience."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")

        # Create job directly to test the update function
        job = Job.from_occupation(
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=36,  # 3 years
        )

        registry = get_attribute_template_registry()
        leaf_templates = registry.get_leaf_templates()
        mapped_templates = {
            attr_id: tmpl
            for attr_id, tmpl in leaf_templates.items()
            if tmpl.mapping_element_id is not None
        }

        update_attributes_with_element_mapping(user, job, mapped_templates)

        # Oral Comprehension (1.A.1.a.1) should have capability
        # LV=4.88, IM=4.62 → experience_score = 0.644
        # capability_delta = 3 * 0.644 = 1.93 → 1
        oral_comp = user.get_attribute("1.A.1.a.1")
        assert oral_comp is not None
        assert oral_comp.capability >= 1
        print(f"\nOral Comprehension capability after 3 years: {oral_comp.capability}")

    def test_preference_increases_with_years(self):
        """Test that preference increases at 2 points per year."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")
        job = Job.from_occupation(
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Acme Corp",
            duration_months=36,  # 3 years
        )

        registry = get_attribute_template_registry()
        leaf_templates = registry.get_leaf_templates()
        mapped_templates = {
            attr_id: tmpl
            for attr_id, tmpl in leaf_templates.items()
            if tmpl.mapping_element_id is not None
        }

        update_attributes_with_element_mapping(user, job, mapped_templates)

        # Preference should be 3 * 2 = 6 for any attribute
        oral_comp = user.get_attribute("1.A.1.a.1")
        assert oral_comp is not None
        assert oral_comp.preference == 6
        print(f"\nOral Comprehension preference after 3 years: {oral_comp.preference}")

    def test_capability_cumulative(self):
        """Test that capability accumulates across multiple jobs."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")

        registry = get_attribute_template_registry()
        leaf_templates = registry.get_leaf_templates()
        mapped_templates = {
            attr_id: tmpl
            for attr_id, tmpl in leaf_templates.items()
            if tmpl.mapping_element_id is not None
        }

        # First job: 2 years
        job1 = Job.from_occupation(
            occupation=ceo_occupation,
            job_title="VP",
            company_name="Company A",
            duration_months=24,
        )
        update_attributes_with_element_mapping(user, job1, mapped_templates)
        first_capability = user.get_attribute("1.A.1.a.1").capability
        first_preference = user.get_attribute("1.A.1.a.1").preference

        print(f"\nAfter 2 years: capability={first_capability}, preference={first_preference}")

        # Second job: 3 years
        job2 = Job.from_occupation(
            occupation=ceo_occupation,
            job_title="CEO",
            company_name="Company B",
            duration_months=36,
        )
        update_attributes_with_element_mapping(user, job2, mapped_templates)
        second_capability = user.get_attribute("1.A.1.a.1").capability
        second_preference = user.get_attribute("1.A.1.a.1").preference

        print(f"After 3 more years: capability={second_capability}, preference={second_preference}")

        # Capability should have increased
        assert second_capability > first_capability

        # Preference should be cumulative: 2*2 + 3*2 = 10
        assert second_preference == 10

    def test_capability_capped_at_100(self):
        """Test that capability is capped at 100."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        user = User(user_id="test-user-1")

        registry = get_attribute_template_registry()
        leaf_templates = registry.get_leaf_templates()
        mapped_templates = {
            attr_id: tmpl
            for attr_id, tmpl in leaf_templates.items()
            if tmpl.mapping_element_id is not None
        }

        # Add many years of experience
        for i in range(20):
            job = Job.from_occupation(
                occupation=ceo_occupation,
                job_title="CEO",
                company_name=f"Company {i}",
                duration_months=60,  # 5 years each = 100 years total
            )
            update_attributes_with_element_mapping(user, job, mapped_templates)

        # All attributes should be capped at 100
        for attr_id, attr in user.attributes.items():
            assert attr.capability <= 100
            assert attr.preference <= 100


class TestFullWorkflow:
    """Integration tests for the complete job experience workflow."""

    def test_complete_workflow(self):
        """Test the complete workflow of adding a job and updating attributes."""
        occupations = load_occupations()
        ceo_occupation = occupations["11-1011.00"]

        # Create a new user
        user = User(user_id="test-user-workflow", user_name="John Doe")

        # Add a job experience
        job = add_job_experience(
            user=user,
            occupation=ceo_occupation,
            job_title="Chief Executive Officer",
            company_name="TechCorp Inc.",
            start_date="2020-06-01",
            end_date="2023-06-01",
            salary=250000.0,
        )

        print("\n" + "="*80)
        print("COMPLETE WORKFLOW TEST")
        print("="*80)

        # Verify job was added
        print(f"\nUser: {user.user_name} (ID: {user.user_id})")
        print(f"Jobs: {len(user.jobs)}")
        print(f"  - {job.job_title} at {job.company_name}")
        print(f"    Occupation: {job.occupation_name} ({job.occupation_id})")

        # Verify attributes were updated
        print(f"\nAttributes updated: {len(user.attributes)}")

        # Show sample attributes
        sample_attrs = [
            ("1.A.1.a.1", "Oral Comprehension"),
            ("1.A.1.b.1", "Fluency of Ideas"),
            ("2.A.1.a", "Reading Comprehension"),
            ("2.C.1.a", "Administration and Management"),
        ]

        print("\nSample attribute values:")
        print("-"*60)
        for attr_id, name in sample_attrs:
            attr = user.get_attribute(attr_id)
            if attr:
                print(f"  {attr_id} ({name}):")
                print(f"    capability={attr.capability}, preference={attr.preference}")

        print("="*80)

        # Assertions
        assert len(user.jobs) == 1
        assert len(user.attributes) > 0

        # Check that mapped attributes have values
        oral_comp = user.get_attribute("1.A.1.a.1")
        assert oral_comp is not None
        assert oral_comp.capability is not None
        assert oral_comp.preference is not None


# Allow running directly for verbose output
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
