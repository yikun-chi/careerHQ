"""
Test script for job_initialize module.

This tests the loading of OrganizationRegistry and ScaleDefinitions.
"""

import sys
from pathlib import Path

# Add parent directory to path to import from packages
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.job_initialize import (
    get_organization_registry,
    get_scale_definitions,
)
from packages.core.domain.job_class import ScaleType


def test_organization_registry():
    """Test loading and displaying organization registry."""
    print("=" * 80)
    print("ORGANIZATION REGISTRY")
    print("=" * 80)

    org_registry = get_organization_registry()
    print(f"\nTotal organization nodes: {len(org_registry.nodes)}\n")

    # Sort by org_id for better readability
    sorted_orgs = sorted(org_registry.nodes.items(), key=lambda x: x[0])

    print("First 50 organization nodes:")
    print("-" * 80)
    for org_id, org_node in sorted_orgs[:50]:
        desc_str = f" - {org_node.description}" if org_node.description else ""
        print(f"{org_id:20s} {org_node.name}{desc_str}")

    if len(sorted_orgs) > 50:
        print(f"\n... and {len(sorted_orgs) - 50} more organization nodes")

    # Show some specific examples
    print("\n" + "-" * 80)
    print("Sample hierarchy lookup:")
    print("-" * 80)

    sample_ids = ["1", "1.A", "1.A.1", "2", "2.A", "2.B", "4", "4.A"]
    for org_id in sample_ids:
        try:
            node = org_registry.get(org_id)
            print(f"{org_id:10s} -> {node.name}")
        except KeyError:
            print(f"{org_id:10s} -> NOT FOUND")


def test_scale_definitions():
    """Test loading and displaying scale definitions."""
    print("\n" + "=" * 80)
    print("SCALE DEFINITIONS")
    print("=" * 80)

    scale_defs = get_scale_definitions()
    print(f"\nTotal scales: {len(scale_defs)}\n")

    # Group by scale type
    ordinal_scales = {k: v for k, v in scale_defs.items() if v.scale_type == ScaleType.ORDINAL}
    interval_scales = {k: v for k, v in scale_defs.items() if v.scale_type == ScaleType.INTERVAL}

    print(f"ORDINAL SCALES (distribution-based): {len(ordinal_scales)}")
    print("-" * 80)
    for scale_id, scale_def in sorted(ordinal_scales.items()):
        print(f"  {scale_id:6s} {scale_def.scale_name:50s} [{scale_def.min_value}-{scale_def.max_value}]")

    print(f"\nINTERVAL SCALES (continuous): {len(interval_scales)}")
    print("-" * 80)
    for scale_id, scale_def in sorted(interval_scales.items()):
        print(f"  {scale_id:6s} {scale_def.scale_name:50s} [{scale_def.min_value}-{scale_def.max_value}]")

    # Show details of a few scales
    print("\n" + "-" * 80)
    print("Detailed scale examples:")
    print("-" * 80)

    sample_scale_ids = ["IM", "LV", "RL", "CXP", "FT"]
    for scale_id in sample_scale_ids:
        if scale_id in scale_defs:
            sd = scale_defs[scale_id]
            print(f"\n{scale_id} - {sd.scale_name}")
            print(f"  Type: {sd.scale_type.value}")
            print(f"  Range: {sd.min_value} to {sd.max_value}")


if __name__ == "__main__":
    test_organization_registry()
    test_scale_definitions()
    print("\n" + "=" * 80)
    print("Tests completed successfully!")
    print("=" * 80)
