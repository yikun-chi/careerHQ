"""
Test suite for user_class and user_initialize modules.

Tests the User, UserAttribute, UserAttributeTemplate, and Job classes,
as well as loading of user attribute templates from CSV.

Run with: pytest tests/test_user_class.py -v -s
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import from packages
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.user_class import (
    UserAttribute,
    UserAttributeTemplate,
    Job,
    User,
)
from packages.core.domain.user_initialize import (
    load_user_attribute_templates,
    get_user_attribute_templates,
    get_user_attribute_template,
)


class TestUserAttribute:
    """Tests for UserAttribute class."""

    def test_create_basic_attribute(self):
        """Test creating a basic user attribute."""
        attr = UserAttribute(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
        )
        assert attr.attribute_id == "1.A.1.a.1"
        assert attr.attribute_name == "Oral Comprehension"
        assert attr.capability is None
        assert attr.preference is None
        assert attr.binary is None

    def test_create_attribute_with_values(self):
        """Test creating an attribute with all values."""
        attr = UserAttribute(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
            mapping_element_id="1.A.1.a.1",
            element_name="Oral Comprehension",
            description="The ability to listen and understand",
            capability=75,
            preference=80,
            binary=True,
        )
        assert attr.capability == 75
        assert attr.preference == 80
        assert attr.binary is True
        assert attr.mapping_element_id == "1.A.1.a.1"

    def test_capability_validation_valid_range(self):
        """Test that capability values in valid range are accepted."""
        # Test boundary values
        attr_min = UserAttribute("test", "Test", capability=0)
        assert attr_min.capability == 0

        attr_max = UserAttribute("test", "Test", capability=100)
        assert attr_max.capability == 100

        attr_mid = UserAttribute("test", "Test", capability=50)
        assert attr_mid.capability == 50

    def test_capability_validation_invalid_range(self):
        """Test that capability values outside range raise ValueError."""
        with pytest.raises(ValueError, match="capability must be an integer"):
            UserAttribute("test", "Test", capability=-1)

        with pytest.raises(ValueError, match="capability must be an integer"):
            UserAttribute("test", "Test", capability=101)

    def test_preference_validation_valid_range(self):
        """Test that preference values in valid range are accepted."""
        attr = UserAttribute("test", "Test", preference=50)
        assert attr.preference == 50

    def test_preference_validation_invalid_range(self):
        """Test that preference values outside range raise ValueError."""
        with pytest.raises(ValueError, match="preference must be an integer"):
            UserAttribute("test", "Test", preference=-1)

        with pytest.raises(ValueError, match="preference must be an integer"):
            UserAttribute("test", "Test", preference=101)

    def test_validate_method(self):
        """Test the validate method directly."""
        attr = UserAttribute("test", "Test")
        attr.capability = 50
        attr.validate()  # Should not raise

        attr.capability = 150
        with pytest.raises(ValueError):
            attr.validate()


class TestUserAttributeTemplate:
    """Tests for UserAttributeTemplate class."""

    def test_template_is_frozen(self):
        """Test that template is immutable (frozen)."""
        template = UserAttributeTemplate(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
        )
        with pytest.raises(AttributeError):
            template.attribute_id = "changed"

    def test_template_instantiate(self):
        """Test creating a UserAttribute from template."""
        template = UserAttributeTemplate(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
            mapping_element_id="1.A.1.a.1",
            element_name="Oral Comprehension",
            description="The ability to listen and understand",
        )

        attr = template.instantiate()

        assert attr.attribute_id == "1.A.1.a.1"
        assert attr.attribute_name == "Oral Comprehension"
        assert attr.mapping_element_id == "1.A.1.a.1"
        assert attr.element_name == "Oral Comprehension"
        assert attr.description == "The ability to listen and understand"
        assert attr.capability is None
        assert attr.preference is None
        assert attr.binary is None


class TestJob:
    """Tests for Job class."""

    def test_create_basic_job(self):
        """Test creating a basic job."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
        )
        assert job.occupation_id == "11-1011.00"
        assert job.occupation_name == "Chief Executives"
        assert job.job_title == "CEO"
        assert job.company_name == "Acme Corp"
        assert job.salary is None
        assert job.elements == {}

    def test_create_job_with_all_fields(self):
        """Test creating a job with all fields."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
            salary=250000.0,
            start_date="2020-01-15",
            end_date="2023-06-30",
            duration_months=42,
        )
        assert job.salary == 250000.0
        assert job.start_date == "2020-01-15"
        assert job.end_date == "2023-06-30"
        assert job.duration_months == 42

    def test_current_job_no_end_date(self):
        """Test that current job has no end date."""
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
            start_date="2023-01-01",
        )
        assert job.end_date is None


class TestJobFromOccupation:
    """Tests for Job.from_occupation factory method."""

    def test_from_occupation(self):
        """Test creating a Job from an Occupation."""
        # Import here to avoid circular imports if occupation isn't loaded
        try:
            from packages.core.domain.occupation_populate import load_occupations

            occupations = load_occupations()
            if occupations and "11-1011.00" in occupations:
                ceo_occupation = occupations["11-1011.00"]

                job = Job.from_occupation(
                    occupation=ceo_occupation,
                    job_title="Chief Executive Officer",
                    company_name="Tech Corp",
                    salary=300000.0,
                    start_date="2022-01-01",
                    duration_months=24,
                )

                assert job.occupation_id == "11-1011.00"
                assert job.occupation_name == "Chief Executives"
                assert job.job_title == "Chief Executive Officer"
                assert job.company_name == "Tech Corp"
                assert job.salary == 300000.0
                assert len(job.elements) > 0
                # Verify elements are copied
                assert "1.A.1.a.1" in job.elements
        except (ImportError, FileNotFoundError):
            pytest.skip("Occupation data not available")


class TestUser:
    """Tests for User class."""

    def test_create_basic_user(self):
        """Test creating a basic user."""
        user = User(user_id="user123")
        assert user.user_id == "user123"
        assert user.user_name is None
        assert user.attributes == {}
        assert user.jobs == []

    def test_create_user_with_name(self):
        """Test creating a user with name."""
        user = User(user_id="user123", user_name="John Doe")
        assert user.user_name == "John Doe"

    def test_add_attribute(self):
        """Test adding an attribute to a user."""
        user = User(user_id="user123")
        attr = UserAttribute(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
            capability=75,
        )
        user.add_attribute(attr)

        assert "1.A.1.a.1" in user.attributes
        assert user.attributes["1.A.1.a.1"].capability == 75

    def test_get_attribute(self):
        """Test getting an attribute from a user."""
        user = User(user_id="user123")
        attr = UserAttribute(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
        )
        user.add_attribute(attr)

        retrieved = user.get_attribute("1.A.1.a.1")
        assert retrieved is not None
        assert retrieved.attribute_name == "Oral Comprehension"

        # Non-existent attribute
        assert user.get_attribute("nonexistent") is None

    def test_add_job(self):
        """Test adding a job to a user."""
        user = User(user_id="user123")
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
        )
        user.add_job(job)

        assert len(user.jobs) == 1
        assert user.jobs[0].job_title == "CEO"

    def test_add_multiple_jobs_order(self):
        """Test that jobs are added in most-recent-first order."""
        user = User(user_id="user123")

        job1 = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="First Job",
            company_name="Company A",
        )
        job2 = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="Second Job",
            company_name="Company B",
        )

        user.add_job(job1)
        user.add_job(job2)

        # job2 should be first (most recent)
        assert user.jobs[0].job_title == "Second Job"
        assert user.jobs[1].job_title == "First Job"

    def test_get_jobs(self):
        """Test getting all jobs from a user."""
        user = User(user_id="user123")
        job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="CEO",
            company_name="Acme Corp",
        )
        user.add_job(job)

        jobs = user.get_jobs()
        assert len(jobs) == 1
        assert jobs[0].job_title == "CEO"

    def test_get_current_job(self):
        """Test getting the current job (no end date)."""
        user = User(user_id="user123")

        past_job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="Former CEO",
            company_name="Old Corp",
            end_date="2022-12-31",
        )
        current_job = Job(
            occupation_id="11-1021.00",
            occupation_name="General Managers",
            job_title="Current GM",
            company_name="New Corp",
            end_date=None,
        )

        user.add_job(past_job)
        user.add_job(current_job)

        current = user.get_current_job()
        assert current is not None
        assert current.job_title == "Current GM"

    def test_get_current_job_none(self):
        """Test getting current job when all jobs have ended."""
        user = User(user_id="user123")

        past_job = Job(
            occupation_id="11-1011.00",
            occupation_name="Chief Executives",
            job_title="Former CEO",
            company_name="Old Corp",
            end_date="2022-12-31",
        )
        user.add_job(past_job)

        assert user.get_current_job() is None


class TestUserAttributeTemplateLoading:
    """Tests for loading user attribute templates from CSV."""

    def test_templates_load(self):
        """Test that templates load successfully from CSV."""
        templates = get_user_attribute_templates()
        assert templates is not None
        assert len(templates) > 0
        print(f"\nTotal attribute templates: {len(templates)}")

    def test_template_count(self):
        """Test that we have the expected number of templates."""
        templates = get_user_attribute_templates()
        # Based on user_attribute.csv, we expect ~308 attributes
        assert len(templates) >= 300
        print(f"\nLoaded {len(templates)} attribute templates")

    def test_sample_template_lookup(self):
        """Test looking up specific templates."""
        templates = get_user_attribute_templates()

        # Test a standard O*NET-mapped attribute
        oral_comp = templates.get("1.A.1.a.1")
        assert oral_comp is not None
        assert oral_comp.attribute_name == "Oral Comprehension"
        assert oral_comp.mapping_element_id == "1.A.1.a.1"
        print(f"\n1.A.1.a.1: {oral_comp.attribute_name}")

        # Test a custom attribute (MBTI)
        intj = templates.get("1.N.2.a")
        assert intj is not None
        assert intj.attribute_name == "INTJ"
        # Custom attributes may not have element mapping
        print(f"1.N.2.a: {intj.attribute_name}")

    def test_get_user_attribute_template_helper(self):
        """Test the helper function for getting single template."""
        template = get_user_attribute_template("1.A.1.a.1")
        assert template is not None
        assert template.attribute_name == "Oral Comprehension"

        # Non-existent template
        assert get_user_attribute_template("nonexistent") is None

    def test_template_instantiation(self):
        """Test instantiating attributes from loaded templates."""
        template = get_user_attribute_template("1.A.1.a.1")
        assert template is not None

        attr = template.instantiate()
        assert attr.attribute_id == "1.A.1.a.1"
        assert attr.attribute_name == "Oral Comprehension"
        assert attr.capability is None

        # Now set values
        attr.capability = 85
        attr.preference = 70
        attr.validate()  # Should not raise

    def test_template_categories(self):
        """Test that we have templates from various categories."""
        templates = get_user_attribute_templates()

        # Check various category prefixes
        categories = {
            "1.A": 0,  # Abilities
            "1.D": 0,  # Work Styles
            "1.N": 0,  # Custom innate characteristics
            "2.D": 0,  # Education
            "2.N": 0,  # Custom education
            "3.A": 0,  # Basic Skills
            "3.B": 0,  # Cross-Functional Skills
            "3.C": 0,  # Knowledge
            "4.B": 0,  # Interests and Work Values
            "4.N": 0,  # Custom interests
        }

        for attr_id in templates.keys():
            for prefix in categories.keys():
                if attr_id.startswith(prefix):
                    categories[prefix] += 1
                    break

        print("\nAttribute counts by category:")
        for prefix, count in sorted(categories.items()):
            print(f"  {prefix}: {count}")
            assert count > 0, f"Expected at least one attribute in category {prefix}"


class TestIntegration:
    """Integration tests for User with loaded templates."""

    def test_create_user_with_templates(self):
        """Test creating a user and populating from templates."""
        user = User(user_id="test_user", user_name="Test User")

        # Load some templates and instantiate attributes
        templates = get_user_attribute_templates()

        # Add a few attributes
        for attr_id in ["1.A.1.a.1", "1.A.1.a.2", "1.D.1.a"]:
            template = templates.get(attr_id)
            if template:
                attr = template.instantiate()
                attr.capability = 75
                attr.preference = 80
                user.add_attribute(attr)

        assert len(user.attributes) == 3
        assert user.get_attribute("1.A.1.a.1").capability == 75

    def test_full_user_profile(self):
        """Test creating a complete user profile with jobs and attributes."""
        user = User(user_id="complete_user", user_name="Complete User")

        # Add some attributes
        attr1 = UserAttribute(
            attribute_id="1.A.1.a.1",
            attribute_name="Oral Comprehension",
            capability=85,
            preference=90,
        )
        attr2 = UserAttribute(
            attribute_id="1.D.1.a",
            attribute_name="Innovation",
            capability=70,
            preference=95,
            binary=True,
        )
        user.add_attribute(attr1)
        user.add_attribute(attr2)

        # Add some jobs
        past_job = Job(
            occupation_id="15-1252.00",
            occupation_name="Software Developers",
            job_title="Junior Developer",
            company_name="StartupCo",
            salary=80000.0,
            start_date="2018-06-01",
            end_date="2021-05-31",
            duration_months=36,
        )
        current_job = Job(
            occupation_id="15-1252.00",
            occupation_name="Software Developers",
            job_title="Senior Developer",
            company_name="BigTech Inc",
            salary=150000.0,
            start_date="2021-06-01",
            duration_months=30,
        )
        user.add_job(past_job)
        user.add_job(current_job)

        # Verify
        assert len(user.attributes) == 2
        assert len(user.jobs) == 2
        assert user.get_current_job().job_title == "Senior Developer"
        assert user.get_attribute("1.A.1.a.1").capability == 85
