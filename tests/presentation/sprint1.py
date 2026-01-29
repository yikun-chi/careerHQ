"""
Sprint 1 Presentation Script
============================

Demonstrates the initialized occupation data with element scales.

Run with: python tests/presentation/sprint1.py
"""

import sys
import random
from pathlib import Path

# Add parent directory to path to import from packages
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from packages.core.domain.occupation_populate import load_occupations
from packages.core.domain.occupation_class import ScaleType
from packages.core.domain.user_class import User
from packages.core.domain.user_service import add_job_experience
from packages.core.domain.user_initialize import get_attribute_template_registry


def get_scale_interpretation(scale, value):
    """Get human-readable interpretation of a scale value."""
    if value is None:
        return "N/A"

    # For ordinal scales, look up the category meaning
    if scale.scale_def.scale_type == ScaleType.ORDINAL and scale.ordinal_semantics:
        # Find the closest integer category
        int_value = int(round(value))
        if int_value in scale.ordinal_semantics.categories:
            return scale.ordinal_semantics.categories[int_value]
        # If exact match not found, show range
        categories = scale.ordinal_semantics.categories
        if categories:
            min_cat = min(categories.keys())
            max_cat = max(categories.keys())
            if int_value < min_cat:
                return f"Below {categories[min_cat]}"
            elif int_value > max_cat:
                return f"Above {categories[max_cat]}"

    # For interval scales, show the meaning
    if scale.scale_def.scale_type == ScaleType.INTERVAL and scale.interval_semantics:
        return f"{scale.interval_semantics.meaning}"

    return ""


def main():
    print("=" * 80)
    print("SPRINT 1: Occupation Data with Element Scales")
    print("=" * 80)
    print()

    # Load all initialized occupations
    print("Loading occupations...")
    occupations = load_occupations()

    # Calculate statistics
    total_occupations = len(occupations)
    occupations_with_scales = 0
    total_elements_across_all = 0
    total_scales_across_all = 0

    for occ in occupations.values():
        elements_with_values = 0
        for element in occ.elements.values():
            scales_with_values = sum(
                1 for s in element.scales.values() if s.value is not None
            )
            if scales_with_values > 0:
                elements_with_values += 1
                total_scales_across_all += scales_with_values

        if elements_with_values > 0:
            occupations_with_scales += 1
            total_elements_across_all += elements_with_values

    # Calculate averages
    avg_elements_per_occupation = (
        total_elements_across_all / occupations_with_scales
        if occupations_with_scales > 0
        else 0
    )
    avg_scales_per_element = (
        total_scales_across_all / total_elements_across_all
        if total_elements_across_all > 0
        else 0
    )

    print()
    print("-" * 80)
    print("SUMMARY STATISTICS")
    print("-" * 80)
    print(f"Total occupations loaded:                    {total_occupations:,}")
    print(f"Occupations with initialized element scales: {occupations_with_scales:,}")
    print(f"Average elements per occupation:             {avg_elements_per_occupation:.1f}")
    print(f"Average scales per element:                  {avg_scales_per_element:.1f}")
    print()

    # Randomly select 2 occupations
    print("-" * 80)
    print("SAMPLE OCCUPATIONS (2 randomly selected)")
    print("-" * 80)
    print()

    random.seed(42)  # For reproducibility in presentation
    sample_occupations = random.sample(list(occupations.values()), 2)

    for i, occ in enumerate(sample_occupations, 1):
        print(f"{'='*80}")
        print(f"[{i}] {occ.occupation_name}")
        print(f"{'='*80}")
        print(f"    Occupation ID: {occ.occupation_id}")

        # Count elements with values
        elements_with_values = [
            (elem_id, elem)
            for elem_id, elem in occ.elements.items()
            if any(scale.value is not None for scale in elem.scales.values())
        ]
        print(f"    Elements with scale values: {len(elements_with_values)}")
        print()

        if not elements_with_values:
            print("    No elements with scale values found.")
            print()
            continue

        # Randomly select 5 elements (or fewer if not available)
        sample_size = min(5, len(elements_with_values))
        sample_elements = random.sample(elements_with_values, sample_size)

        print(f"    Sample Element Scales ({sample_size} randomly selected):")
        print()

        for elem_id, elem in sample_elements:
            print(f"    {'-'*72}")
            print(f"    ELEMENT: {elem.element_name}")
            print(f"    ID: {elem_id}")
            print()

            # Print all scales for this element with interpretations
            for scale_id, scale in elem.scales.items():
                if scale.value is not None:
                    interpretation = get_scale_interpretation(scale, scale.value)
                    value_str = f"{scale.value:.2f}" if isinstance(scale.value, float) else str(scale.value)

                    print(f"        {scale.scale_name} ({scale_id})")
                    print(f"          Value: {value_str}")
                    if interpretation:
                        print(f"          Interpretation: {interpretation}")

                    # For ordinal scales, show the full category scale for context
                    if scale.scale_def.scale_type == ScaleType.ORDINAL and scale.ordinal_semantics:
                        cats = scale.ordinal_semantics.categories
                        if cats:
                            min_cat = min(cats.keys())
                            max_cat = max(cats.keys())
                            print(f"          Scale range: {min_cat} ({cats[min_cat]}) to {max_cat} ({cats[max_cat]})")
                    print()

        print()


def demo_user_job_experience():
    """Demonstrate user initialization and job experience attribute updates."""
    print()
    print("=" * 80)
    print("DEMO: User Job Experience & Attribute Updates")
    print("=" * 80)
    print()

    # Load occupations
    print("Loading occupations...")
    occupations = load_occupations()

    # Select an occupation for the demo
    occupation = occupations["11-1011.00"]  # Chief Executives
    print(f"Selected occupation: {occupation.occupation_name} ({occupation.occupation_id})")
    print()

    # Select 2 attributes to track
    attr_registry = get_attribute_template_registry()
    tracked_attributes = [
        ("1.A.1.a.1", "Oral Comprehension"),  # Ability with LV + IM scales
        ("2.C.1.a", "Administration and Management"),  # Knowledge with LV + IM scales
    ]

    print("-" * 80)
    print("STEP 1: Initialize a new user")
    print("-" * 80)
    print()

    user = User(user_id="demo-user-001", user_name="Jane Doe")
    print(f"  User ID:   {user.user_id}")
    print(f"  User Name: {user.user_name}")
    print(f"  Jobs:      {len(user.jobs)}")
    print(f"  Attributes: {len(user.attributes)}")
    print()

    # Show initial state of tracked attributes
    print("-" * 80)
    print("STEP 2: Check initial state of tracked attributes")
    print("-" * 80)
    print()

    print("  Attributes being tracked:")
    for attr_id, attr_name in tracked_attributes:
        attr = user.get_attribute(attr_id)
        if attr:
            print(f"    {attr_id} ({attr_name}):")
            print(f"      capability: {attr.capability}")
            print(f"      preference: {attr.preference}")
        else:
            print(f"    {attr_id} ({attr_name}): NOT YET CREATED")
    print()

    # Show the occupation's element data for these attributes
    print("-" * 80)
    print("STEP 3: Inspect occupation element data for these attributes")
    print("-" * 80)
    print()

    print(f"  Occupation: {occupation.occupation_name}")
    print()
    for attr_id, attr_name in tracked_attributes:
        element = occupation.elements.get(attr_id)
        if element:
            lv = element.get_scale("LV")
            im = element.get_scale("IM")
            print(f"    {attr_id} ({attr_name}):")
            if lv and lv.value is not None:
                print(f"      LV (Level): {lv.value:.2f}")
            if im and im.value is not None:
                print(f"      IM (Importance): {im.value:.2f}")
            if lv and im and lv.value and im.value:
                exp_score = (lv.value * im.value) / 35.0
                print(f"      Experience Score: {exp_score:.3f} (LV * IM / 35)")
        print()

    # Add a job experience
    print("-" * 80)
    print("STEP 4: Add job experience (3 years as CEO)")
    print("-" * 80)
    print()

    job = add_job_experience(
        user=user,
        occupation=occupation,
        job_title="Chief Executive Officer",
        company_name="TechCorp Inc.",
        duration_months=36,  # 3 years
        salary=250000.0,
    )

    print(f"  Added job:")
    print(f"    Job Title:    {job.job_title}")
    print(f"    Company:      {job.company_name}")
    print(f"    Occupation:   {job.occupation_name}")
    print(f"    Duration:     {job.duration_months} months (3 years)")
    print(f"    Salary:       ${job.salary:,.0f}")
    print()

    # Show updated state
    print("-" * 80)
    print("STEP 5: Check updated state of tracked attributes")
    print("-" * 80)
    print()

    print(f"  User now has {len(user.jobs)} job(s) and {len(user.attributes)} attributes")
    print()
    print("  Tracked attributes after adding job experience:")
    print()

    for attr_id, attr_name in tracked_attributes:
        attr = user.get_attribute(attr_id)
        if attr:
            print(f"    {attr_id} ({attr_name}):")
            print(f"      capability: {attr.capability}")
            print(f"      preference: {attr.preference}")

            # Explain the calculation
            element = occupation.elements.get(attr_id)
            if element:
                lv = element.get_scale("LV")
                im = element.get_scale("IM")
                if lv and im and lv.value and im.value:
                    exp_score = (lv.value * im.value) / 35.0
                    years = 3.0
                    cap_delta = years * exp_score
                    pref_delta = years * 2
                    print(f"      Calculation:")
                    print(f"        experience_score = {lv.value:.2f} * {im.value:.2f} / 35 = {exp_score:.3f}")
                    print(f"        capability_delta = {years:.0f} years * {exp_score:.3f} = {cap_delta:.1f} -> {int(cap_delta)}")
                    print(f"        preference_delta = {years:.0f} years * 2 = {int(pref_delta)}")
        print()

    # Add another job to show cumulative effect
    print("-" * 80)
    print("STEP 6: Add another job (2 more years at same occupation)")
    print("-" * 80)
    print()

    job2 = add_job_experience(
        user=user,
        occupation=occupation,
        job_title="CEO",
        company_name="StartupXYZ",
        duration_months=24,  # 2 years
    )

    print(f"  Added second job:")
    print(f"    Job Title:    {job2.job_title}")
    print(f"    Company:      {job2.company_name}")
    print(f"    Duration:     {job2.duration_months} months (2 years)")
    print()

    print(f"  User now has {len(user.jobs)} job(s)")
    print()
    print("  Tracked attributes after 5 total years of experience:")
    print()

    for attr_id, attr_name in tracked_attributes:
        attr = user.get_attribute(attr_id)
        if attr:
            print(f"    {attr_id} ({attr_name}):")
            print(f"      capability: {attr.capability} (cumulative)")
            print(f"      preference: {attr.preference} (cumulative: 3*2 + 2*2 = 10)")
        print()

    print("=" * 80)
    print("END OF DEMO")
    print("=" * 80)


if __name__ == "__main__":
    main()
    demo_user_job_experience()
