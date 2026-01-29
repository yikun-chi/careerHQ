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


if __name__ == "__main__":
    main()
