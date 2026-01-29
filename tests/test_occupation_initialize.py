"""
Test suite for occupation_initialize module.

Tests the loading of OrganizationRegistry, ScaleDefinitions, and Elements.
Run with: pytest tests/test_occupation_initialize.py -v -s
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path to import from packages
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.domain.occupation_initialize import (
    get_organization_registry,
    get_scale_definitions,
    get_elements,
)
from packages.core.domain.occupation_initialize_1a import (
    load_im_scale_schema,
    load_lv_anchors,
    load_element_scale_mapping,
    populate_1a_element_scales,
    get_1a_elements,
)
from packages.core.domain.occupation_initialize_1b import (
    load_oi_scale_schema,
    load_ex_scale_schema,
    load_element_scale_mapping_1b,
    populate_1b_element_scales,
    get_1b_elements,
)
from packages.core.domain.occupation_initialize_1d import (
    load_wi_scale_schema,
    load_dr_scale_schema,
    load_element_scale_mapping_1d,
    populate_1d_element_scales,
    get_1d_elements,
)
from packages.core.domain.occupation_initialize_2abc import (
    load_lv_anchors_2abc,
    load_element_scale_mapping_2abc,
    populate_2abc_element_scales,
    get_2abc_elements,
    get_2a_elements,
    get_2b_elements,
    get_2c_elements,
)
from packages.core.domain.occupation_initialize_2d3a import (
    load_rl_scale_schemas,
    load_rw_scale_schemas,
    load_pt_scale_schemas,
    load_oj_scale_schemas,
    load_element_scale_mapping_2d3a,
    populate_2d3a_element_scales,
    get_2d3a_elements,
    get_2d_elements,
    get_3a_elements,
    get_category_scale_info,
)
from packages.core.domain.occupation_class import ScaleType
from packages.core.domain.occupation_populate import (
    populate_all_occupations,
    load_occupations,
    create_occupation_schema,
    load_occupations_list,
    create_empty_occupations,
    parse_rating_file,
    RATING_FILE_CONFIGS,
)
from packages.core.domain.occupation_initialize import get_data_dir


class TestOrganizationRegistry:
    """Tests for OrganizationRegistry loading."""

    def test_registry_loads(self):
        """Test that organization registry loads successfully."""
        org_registry = get_organization_registry()
        assert org_registry is not None
        assert len(org_registry.nodes) > 0

    def test_registry_node_count(self):
        """Test organization registry has expected nodes."""
        org_registry = get_organization_registry()
        print(f"\nTotal organization nodes: {len(org_registry.nodes)}")
        # Should have a reasonable number of organization nodes
        assert len(org_registry.nodes) >= 50

    def test_registry_sample_lookup(self):
        """Test looking up specific organization nodes."""
        org_registry = get_organization_registry()

        # These top-level categories should exist (only 1, 2, 3 after filtering)
        expected_ids = ["1", "1.A", "2", "2.A", "3"]

        print("\nSample organization nodes:")
        print("-" * 60)
        for org_id in expected_ids:
            node = org_registry.get(org_id)
            assert node is not None
            assert node.org_id == org_id
            print(f"  {org_id:10s} -> {node.name}")

    def test_registry_hierarchy_structure(self):
        """Test that hierarchy structure is correct."""
        org_registry = get_organization_registry()

        # 1.A should be under 1 (Abilities under Worker Characteristics)
        node_1 = org_registry.get("1")
        node_1a = org_registry.get("1.A")

        assert node_1.name == "Worker Characteristics"
        assert node_1a.name == "Abilities"


class TestScaleDefinitions:
    """Tests for ScaleDefinition loading."""

    def test_scales_load(self):
        """Test that scale definitions load successfully."""
        scale_defs = get_scale_definitions()
        assert scale_defs is not None
        assert len(scale_defs) > 0

    def test_scales_count(self):
        """Test scale definitions count."""
        scale_defs = get_scale_definitions()
        print(f"\nTotal scales: {len(scale_defs)}")
        # Should have multiple scales
        assert len(scale_defs) >= 5

    def test_scales_have_required_fields(self):
        """Test that all scales have required fields."""
        scale_defs = get_scale_definitions()

        for scale_id, scale_def in scale_defs.items():
            assert scale_def.scale_id == scale_id
            assert scale_def.scale_name is not None
            assert scale_def.min_value is not None
            assert scale_def.max_value is not None
            assert scale_def.scale_type in [ScaleType.ORDINAL, ScaleType.INTERVAL]

    def test_scales_by_type(self):
        """Test grouping scales by type."""
        scale_defs = get_scale_definitions()

        ordinal_scales = {k: v for k, v in scale_defs.items() if v.scale_type == ScaleType.ORDINAL}
        interval_scales = {k: v for k, v in scale_defs.items() if v.scale_type == ScaleType.INTERVAL}

        print(f"\nOrdinal scales: {len(ordinal_scales)}")
        print(f"Interval scales: {len(interval_scales)}")

        # Should have both types
        assert len(ordinal_scales) + len(interval_scales) == len(scale_defs)

    def test_scales_sample_display(self):
        """Display sample scales for inspection."""
        scale_defs = get_scale_definitions()

        print("\nSample scale definitions:")
        print("-" * 60)
        for scale_id, scale_def in list(scale_defs.items())[:5]:
            print(f"  {scale_id:6s} {scale_def.scale_name[:40]:40s} "
                  f"[{scale_def.min_value}-{scale_def.max_value}] {scale_def.scale_type.value}")


class TestElements:
    """Tests for Element loading."""

    def test_elements_load(self):
        """Test that elements load successfully."""
        elements = get_elements()
        assert elements is not None
        assert len(elements) > 0

    def test_element_count(self):
        """Test element count and print summary."""
        elements = get_elements()
        print(f"\nTotal leaf elements loaded: {len(elements)}")
        # Should have a substantial number of elements
        assert len(elements) >= 100

    def test_elements_are_leaf_nodes(self):
        """Test that loaded elements are leaf nodes (no children)."""
        elements = get_elements()
        element_ids = set(elements.keys())

        # No element should be a prefix of another element
        for elem_id in element_ids:
            for other_id in element_ids:
                if other_id != elem_id:
                    assert not other_id.startswith(elem_id + "."), \
                        f"Element {elem_id} has child {other_id}, should not be loaded as leaf"

    def test_elements_have_organizations(self):
        """Test that elements have computed organization prefixes."""
        elements = get_elements()

        # Pick a specific element to test
        # 1.A.1.a.1 (Oral Comprehension) should have organizations (1, 1.A, 1.A.1, 1.A.1.a)
        if "1.A.1.a.1" in elements:
            elem = elements["1.A.1.a.1"]
            assert elem.organizations == ("1", "1.A", "1.A.1", "1.A.1.a")
            print(f"\nElement 1.A.1.a.1 organizations: {elem.organizations}")

    def test_element_sample_display(self):
        """Display sample elements for inspection."""
        elements = get_elements()

        # Sort by element_id for consistent output
        sorted_elements = sorted(elements.items(), key=lambda x: x[0])

        print(f"\nFirst 20 elements (of {len(elements)} total):")
        print("-" * 80)
        for element_id, element in sorted_elements[:20]:
            print(f"  {element_id:15s} {element.element_name[:50]}")

        print(f"\n... and {len(elements) - 20} more elements")

    def test_element_categories_represented(self):
        """Test that elements from different categories are loaded."""
        elements = get_elements()

        # Count elements by top-level category
        categories = {}
        for element_id in elements.keys():
            top_level = element_id.split(".")[0]
            categories[top_level] = categories.get(top_level, 0) + 1

        print("\nElements by top-level category:")
        print("-" * 40)
        for cat_id, count in sorted(categories.items()):
            print(f"  Category {cat_id}: {count} elements")

        # Should have elements from multiple categories
        assert len(categories) >= 3


class TestIntegration:
    """Integration tests for all components."""

    def test_all_registries_load(self):
        """Test that all registries load without error."""
        org_registry = get_organization_registry()
        scale_defs = get_scale_definitions()
        elements = get_elements()

        assert org_registry is not None
        assert scale_defs is not None
        assert elements is not None

        print(f"\nLoaded successfully:")
        print(f"  - {len(org_registry.nodes)} organization nodes")
        print(f"  - {len(scale_defs)} scale definitions")
        print(f"  - {len(elements)} elements")

    def test_element_organizations_exist_in_registry(self):
        """Test that element organization references exist in the registry."""
        org_registry = get_organization_registry()
        elements = get_elements()

        missing_orgs = set()
        for element in elements.values():
            for org_id in element.organizations:
                if org_id not in org_registry.nodes:
                    missing_orgs.add(org_id)

        if missing_orgs:
            print(f"\nWarning: {len(missing_orgs)} organization IDs referenced by elements "
                  f"but not in registry: {sorted(missing_orgs)[:10]}...")

        # Most organizations should exist (allow some tolerance)
        total_refs = sum(len(e.organizations) for e in elements.values())
        missing_ratio = len(missing_orgs) / max(total_refs, 1)
        assert missing_ratio < 0.1, f"Too many missing organizations: {missing_ratio:.1%}"


class TestElementScales1A:
    """Tests for 1.A element scale initialization."""

    def test_im_scale_schema_loads(self):
        """Test that IM scale schema loads correctly."""
        scale_def, semantics = load_im_scale_schema()

        assert scale_def.scale_id == "IM"
        assert scale_def.scale_name == "Importance"
        assert scale_def.min_value == 1
        assert scale_def.max_value == 5
        assert scale_def.scale_type == ScaleType.ORDINAL

        # Check categories
        assert len(semantics.categories) == 5
        assert semantics.categories[1] == "Not important"
        assert semantics.categories[5] == "Extremely important"

        print("\nIM Scale Categories:")
        for val, label in sorted(semantics.categories.items()):
            print(f"  {val}: {label}")

    def test_lv_anchors_load(self):
        """Test that LV anchors load for 1.A elements."""
        lv_anchors = load_lv_anchors()

        assert len(lv_anchors) > 0
        print(f"\nLoaded LV anchors for {len(lv_anchors)} elements")

        # Check a specific element (Oral Comprehension)
        if "1.A.1.a.1" in lv_anchors:
            anchors = lv_anchors["1.A.1.a.1"]
            print(f"\n1.A.1.a.1 (Oral Comprehension) LV anchors:")
            for val, desc in sorted(anchors.categories.items()):
                print(f"  {val}: {desc}")

            # Should have anchors at levels 2, 4, 6
            assert 2 in anchors.categories
            assert 4 in anchors.categories
            assert 6 in anchors.categories

    def test_element_scale_mapping_loads(self):
        """Test that element-scale mapping loads correctly."""
        mapping = load_element_scale_mapping()

        assert len(mapping) > 0
        print(f"\nLoaded scale mappings for {len(mapping)} elements")

        # Each 1.A element should have IM and LV
        for element_id, scales in list(mapping.items())[:5]:
            print(f"  {element_id}: {scales}")
            assert "IM" in scales
            assert "LV" in scales

    def test_populate_1a_element_scales(self):
        """Test that 1.A elements get their scales populated."""
        elements = get_elements()
        populate_1a_element_scales(elements)

        # Check that 1.A elements have scales
        elements_with_scales = 0
        for element_id, element in elements.items():
            if element_id.startswith("1.A."):
                if len(element.scales) > 0:
                    elements_with_scales += 1

        print(f"\n1.A elements with scales populated: {elements_with_scales}")
        assert elements_with_scales >= 50  # Should have ~52 abilities

    def test_1a_element_scale_details(self):
        """Test details of populated scales on a specific element."""
        elements = get_1a_elements()

        # Check Oral Comprehension (1.A.1.a.1)
        if "1.A.1.a.1" in elements:
            elem = elements["1.A.1.a.1"]

            print(f"\n{elem.element_id}: {elem.element_name}")
            print(f"Scales: {list(elem.scales.keys())}")

            # Should have IM and LV scales
            assert "IM" in elem.scales
            assert "LV" in elem.scales

            # Check IM scale
            im_scale = elem.scales["IM"]
            assert im_scale.scale_def.scale_id == "IM"
            assert im_scale.ordinal_semantics is not None
            print(f"\nIM scale semantics: {im_scale.ordinal_semantics.categories}")

            # Check LV scale
            lv_scale = elem.scales["LV"]
            assert lv_scale.scale_def.scale_id == "LV"
            assert lv_scale.ordinal_semantics is not None
            print(f"LV scale anchors: {lv_scale.ordinal_semantics.categories}")

    def test_1a_elements_count(self):
        """Test that we get the right number of 1.A elements."""
        elements = get_1a_elements()

        print(f"\nTotal 1.A elements: {len(elements)}")
        assert len(elements) == 52  # 52 abilities in O*NET

        # Show sample elements
        print("\nSample 1.A elements with scales:")
        for element_id, element in list(elements.items())[:5]:
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")


class TestElementScales1B:
    """Tests for 1.B element scale initialization."""

    def test_oi_scale_schema_loads(self):
        """Test that OI scale schema loads correctly."""
        scale_def, semantics = load_oi_scale_schema()

        assert scale_def.scale_id == "OI"
        assert scale_def.scale_name == "Occupational Interests"
        assert scale_def.min_value == 1
        assert scale_def.max_value == 7
        assert scale_def.scale_type == ScaleType.INTERVAL

        assert semantics.meaning is not None
        print(f"\nOI Scale meaning: {semantics.meaning}")

    def test_ex_scale_schema_loads(self):
        """Test that EX scale schema loads correctly."""
        scale_def, semantics = load_ex_scale_schema()

        assert scale_def.scale_id == "EX"
        assert scale_def.scale_name == "Extent"
        assert scale_def.min_value == 1
        assert scale_def.max_value == 7
        assert scale_def.scale_type == ScaleType.INTERVAL

        assert semantics.meaning is not None
        print(f"\nEX Scale meaning: {semantics.meaning}")

    def test_element_scale_mapping_1b_loads(self):
        """Test that element-scale mapping for 1.B loads correctly."""
        mapping = load_element_scale_mapping_1b()

        assert len(mapping) > 0
        print(f"\nLoaded scale mappings for {len(mapping)} 1.B elements")

        # 1.B.1 elements should have OI scale
        for element_id, scales in mapping.items():
            if element_id.startswith("1.B.1."):
                print(f"  {element_id}: {scales}")
                assert "OI" in scales

        # 1.B.2 elements should have EX scale
        for element_id, scales in mapping.items():
            if element_id.startswith("1.B.2."):
                print(f"  {element_id}: {scales}")
                assert "EX" in scales

    def test_populate_1b_element_scales(self):
        """Test that 1.B elements get their scales populated."""
        elements = get_elements()
        populate_1b_element_scales(elements)

        # Check that 1.B.1 elements have scales
        # NOTE: 1.B.2.a-f in the mapping are NOT leaf elements (they have children),
        # so only 1.B.1.a-f (6 elements) actually get scales populated.
        elements_with_scales = 0
        for element_id, element in elements.items():
            if element_id.startswith("1.B.1.") or element_id.startswith("1.B.2."):
                if len(element.scales) > 0:
                    elements_with_scales += 1

        print(f"\n1.B elements with scales populated: {elements_with_scales}")
        assert elements_with_scales == 12  # 6 OI (1.B.1) + 6 EX (1.B.2)

    def test_1b_element_scale_details(self):
        """Test details of populated scales on specific elements."""
        elements = get_1b_elements()

        # Check a 1.B.1 element (Realistic) with OI scale
        assert "1.B.1.a" in elements, "1.B.1.a should be in elements"
        elem = elements["1.B.1.a"]
        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Scales: {list(elem.scales.keys())}")

        assert "OI" in elem.scales
        oi_scale = elem.scales["OI"]
        assert oi_scale.scale_def.scale_id == "OI"
        assert oi_scale.interval_semantics is not None
        print(f"OI scale meaning: {oi_scale.interval_semantics.meaning[:50]}...")

        # Check a 1.B.2 element (Achievement) with EX scale
        assert "1.B.2.a" in elements, "1.B.2.a should be in elements"
        elem = elements["1.B.2.a"]
        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Scales: {list(elem.scales.keys())}")

        assert "EX" in elem.scales
        ex_scale = elem.scales["EX"]
        assert ex_scale.scale_def.scale_id == "EX"
        assert ex_scale.interval_semantics is not None
        print(f"EX scale meaning: {ex_scale.interval_semantics.meaning[:50]}...")

    def test_1b_elements_count(self):
        """Test that we get the right number of 1.B elements."""
        elements = get_1b_elements()

        print(f"\nTotal 1.B elements (with scales): {len(elements)}")
        # 6 from 1.B.1 (OI) + 6 from 1.B.2 (EX) = 12 total
        assert len(elements) == 12

        # Show all elements
        print("\n1.B elements with scales:")
        for element_id, element in sorted(elements.items()):
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")

    def test_1b3_elements_not_populated(self):
        """Test that 1.B.3 elements are intentionally not populated with scales."""
        elements = get_elements()
        populate_1b_element_scales(elements)

        # 1.B.3 elements should have no scales (by design)
        for element_id, element in elements.items():
            if element_id.startswith("1.B.3."):
                assert len(element.scales) == 0, \
                    f"1.B.3 element {element_id} should not have scales"

        print("\n1.B.3 elements correctly have no scales (by design)")


class TestElementScales1D:
    """Tests for 1.D element scale initialization."""

    def test_wi_scale_schema_loads(self):
        """Test that WI scale schema loads correctly."""
        scale_def, semantics = load_wi_scale_schema()

        assert scale_def.scale_id == "WI"
        assert scale_def.scale_name == "Work Styles Impact"
        assert scale_def.min_value == -3.0
        assert scale_def.max_value == 3.0
        assert scale_def.scale_type == ScaleType.INTERVAL

        assert semantics.meaning is not None
        print(f"\nWI Scale meaning: {semantics.meaning[:80]}...")

    def test_dr_scale_schema_loads(self):
        """Test that DR scale schema loads correctly."""
        scale_def, semantics = load_dr_scale_schema()

        assert scale_def.scale_id == "DR"
        assert scale_def.scale_name == "Distinctiveness Rank"
        assert scale_def.min_value == 0
        assert scale_def.max_value == 10
        assert scale_def.scale_type == ScaleType.ORDINAL

        # Check categories
        assert len(semantics.categories) == 11  # 0-10
        assert 0 in semantics.categories
        assert 1 in semantics.categories
        assert 10 in semantics.categories

        print("\nDR Scale Categories:")
        for val, label in sorted(semantics.categories.items()):
            print(f"  {val}: {label}")

    def test_element_scale_mapping_1d_loads(self):
        """Test that element-scale mapping for 1.D loads correctly."""
        mapping = load_element_scale_mapping_1d()

        assert len(mapping) > 0
        print(f"\nLoaded scale mappings for {len(mapping)} 1.D elements")

        # Each 1.D element should have both WI and DR scales
        for element_id, scales in list(mapping.items())[:5]:
            print(f"  {element_id}: {scales}")
            assert "WI" in scales
            assert "DR" in scales

    def test_populate_1d_element_scales(self):
        """Test that 1.D elements get their scales populated."""
        elements = get_elements()
        populate_1d_element_scales(elements)

        # Check that 1.D elements have scales
        elements_with_scales = 0
        for element_id, element in elements.items():
            if element_id.startswith("1.D."):
                if len(element.scales) > 0:
                    elements_with_scales += 1

        print(f"\n1.D elements with scales populated: {elements_with_scales}")
        assert elements_with_scales == 21  # 21 Work Styles

    def test_1d_element_scale_details(self):
        """Test details of populated scales on a specific element."""
        elements = get_1d_elements()

        # Check Innovation (1.D.1.a)
        assert "1.D.1.a" in elements, "1.D.1.a should be in elements"
        elem = elements["1.D.1.a"]

        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Scales: {list(elem.scales.keys())}")

        # Should have both WI and DR scales
        assert "WI" in elem.scales
        assert "DR" in elem.scales

        # Check WI scale (interval)
        wi_scale = elem.scales["WI"]
        assert wi_scale.scale_def.scale_id == "WI"
        assert wi_scale.interval_semantics is not None
        print(f"\nWI scale meaning: {wi_scale.interval_semantics.meaning[:50]}...")

        # Check DR scale (ordinal)
        dr_scale = elem.scales["DR"]
        assert dr_scale.scale_def.scale_id == "DR"
        assert dr_scale.ordinal_semantics is not None
        print(f"DR scale categories: {list(dr_scale.ordinal_semantics.categories.keys())}")

    def test_1d_elements_count(self):
        """Test that we get the right number of 1.D elements."""
        elements = get_1d_elements()

        print(f"\nTotal 1.D elements: {len(elements)}")
        # 9 from 1.D.1 + 6 from 1.D.2 + 4 from 1.D.3 + 2 from 1.D.4 = 21 total
        assert len(elements) == 21

        # Show all elements by subcategory
        print("\n1.D elements with scales:")
        for element_id, element in sorted(elements.items()):
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")

    def test_1d_subcategory_counts(self):
        """Test element counts by subcategory."""
        elements = get_1d_elements()

        subcategories = {}
        for element_id in elements.keys():
            # Get subcategory like "1.D.1", "1.D.2", etc.
            parts = element_id.split(".")
            subcat = ".".join(parts[:3])
            subcategories[subcat] = subcategories.get(subcat, 0) + 1

        print("\n1.D elements by subcategory:")
        for subcat, count in sorted(subcategories.items()):
            print(f"  {subcat}: {count} elements")

        # Verify expected counts
        assert subcategories.get("1.D.1", 0) == 9   # Achievement/Innovation
        assert subcategories.get("1.D.2", 0) == 6   # Interpersonal Orientation
        assert subcategories.get("1.D.3", 0) == 4   # Conscientiousness
        assert subcategories.get("1.D.4", 0) == 2   # Adjustment


class TestElementScales2ABC:
    """Tests for 2.A, 2.B, 2.C element scale initialization."""

    def test_lv_anchors_2abc_load(self):
        """Test that LV anchors load for 2.A, 2.B, 2.C elements."""
        lv_anchors = load_lv_anchors_2abc()

        assert len(lv_anchors) > 0
        print(f"\nLoaded LV anchors for {len(lv_anchors)} 2.A/B/C elements")

        # Check a specific element (Reading Comprehension)
        if "2.A.1.a" in lv_anchors:
            anchors = lv_anchors["2.A.1.a"]
            print(f"\n2.A.1.a (Reading Comprehension) LV anchors:")
            for val, desc in sorted(anchors.categories.items()):
                print(f"  {val}: {desc}")

            # Should have anchors at levels 2, 4, 6
            assert 2 in anchors.categories
            assert 4 in anchors.categories
            assert 6 in anchors.categories

    def test_element_scale_mapping_2abc_loads(self):
        """Test that element-scale mapping for 2ABC loads correctly."""
        mapping = load_element_scale_mapping_2abc()

        assert len(mapping) > 0
        print(f"\nLoaded scale mappings for {len(mapping)} 2.A/B/C elements")

        # Each element should have IM and LV
        for element_id, scales in list(mapping.items())[:5]:
            print(f"  {element_id}: {scales}")
            assert "IM" in scales
            assert "LV" in scales

    def test_populate_2abc_element_scales(self):
        """Test that 2.A, 2.B, 2.C elements get their scales populated."""
        elements = get_elements()
        populate_2abc_element_scales(elements)

        # Count elements with scales
        elements_with_scales = 0
        for element_id, element in elements.items():
            if element_id.startswith("2.A.") or element_id.startswith("2.B.") or element_id.startswith("2.C"):
                if len(element.scales) > 0:
                    elements_with_scales += 1

        print(f"\n2.A/B/C elements with scales populated: {elements_with_scales}")
        assert elements_with_scales == 68  # 10 + 25 + 33

    def test_2abc_element_scale_details(self):
        """Test details of populated scales on a specific element."""
        elements = get_2abc_elements()

        # Check Reading Comprehension (2.A.1.a)
        assert "2.A.1.a" in elements, "2.A.1.a should be in elements"
        elem = elements["2.A.1.a"]

        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Scales: {list(elem.scales.keys())}")

        # Should have IM and LV scales
        assert "IM" in elem.scales
        assert "LV" in elem.scales

        # Check IM scale
        im_scale = elem.scales["IM"]
        assert im_scale.scale_def.scale_id == "IM"
        assert im_scale.ordinal_semantics is not None
        print(f"\nIM scale semantics: {im_scale.ordinal_semantics.categories}")

        # Check LV scale
        lv_scale = elem.scales["LV"]
        assert lv_scale.scale_def.scale_id == "LV"
        assert lv_scale.ordinal_semantics is not None
        print(f"LV scale anchors: {lv_scale.ordinal_semantics.categories}")

    def test_2abc_elements_count(self):
        """Test that we get the right number of 2.A, 2.B, 2.C elements."""
        elements = get_2abc_elements()

        print(f"\nTotal 2.A/B/C elements: {len(elements)}")
        assert len(elements) == 68  # 10 + 25 + 33

    def test_2a_elements_count(self):
        """Test 2.A (Basic Skills) element count."""
        elements = get_2a_elements()

        print(f"\n2.A elements: {len(elements)}")
        assert len(elements) == 10

        print("\n2.A elements with scales:")
        for element_id, element in sorted(elements.items()):
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")

    def test_2b_elements_count(self):
        """Test 2.B (Cross-Functional Skills) element count."""
        elements = get_2b_elements()

        print(f"\n2.B elements: {len(elements)}")
        assert len(elements) == 25

        print("\n2.B elements with scales:")
        for element_id, element in sorted(elements.items()):
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")

    def test_2c_elements_count(self):
        """Test 2.C (Knowledge) element count."""
        elements = get_2c_elements()

        print(f"\n2.C elements: {len(elements)}")
        assert len(elements) == 33

        print("\n2.C elements with scales:")
        for element_id, element in sorted(elements.items()):
            scales_info = ", ".join(element.scales.keys())
            print(f"  {element_id}: {element.element_name} [{scales_info}]")

    def test_2abc_subcategory_breakdown(self):
        """Test element counts by major subcategory."""
        elements = get_2abc_elements()

        subcategories = {}
        for element_id in elements.keys():
            # Get prefix like "2.A", "2.B", "2.C"
            parts = element_id.split(".")
            prefix = ".".join(parts[:2])
            subcategories[prefix] = subcategories.get(prefix, 0) + 1

        print("\n2.A/B/C elements by category:")
        for cat, count in sorted(subcategories.items()):
            print(f"  {cat}: {count} elements")

        # Verify expected counts
        assert subcategories.get("2.A", 0) == 10   # Basic Skills
        assert subcategories.get("2.B", 0) == 25   # Cross-Functional Skills
        assert subcategories.get("2.C", 0) == 33   # Knowledge


class TestElementScales2D3A:
    """Tests for 2.D and 3.A element scale initialization (category distribution scales).

    These scales use the "Option 3" design: each category becomes a separate interval scale.
    For example, RL (Required Level of Education) becomes 12 scales: RL-1, RL-2, ... RL-12.
    Each scale is interval (0-100%) representing percentage of respondents.
    """

    def test_rl_scale_schemas_load(self):
        """Test that RL (Required Level of Education) category scales load correctly."""
        scales = load_rl_scale_schemas()

        # Should have 12 scales (RL-1 through RL-12)
        assert len(scales) == 12

        # Check a specific scale (RL-6 = Bachelor's Degree)
        scale_def, semantics = scales[6]
        assert scale_def.scale_id == "RL-6"
        assert "Bachelor's Degree" in scale_def.scale_name
        assert scale_def.min_value == 0.0
        assert scale_def.max_value == 100.0
        assert scale_def.scale_type == ScaleType.INTERVAL

        # Check interval semantics
        assert semantics.meaning is not None
        assert "Bachelor's Degree" in semantics.meaning

        print("\nRL Scales (12 education level categories):")
        for cat_id, (scale_def, semantics) in sorted(scales.items()):
            print(f"  {scale_def.scale_id}: {scale_def.scale_name[:50]}...")

    def test_rw_scale_schemas_load(self):
        """Test that RW (Related Work Experience) category scales load correctly."""
        scales = load_rw_scale_schemas()

        # Should have 11 scales (RW-1 through RW-11)
        assert len(scales) == 11

        # Check first scale (RW-1 = None)
        scale_def, semantics = scales[1]
        assert scale_def.scale_id == "RW-1"
        assert scale_def.scale_type == ScaleType.INTERVAL
        assert "None" in semantics.meaning

        print("\nRW Scales (11 work experience categories):")
        for cat_id, (scale_def, semantics) in sorted(scales.items()):
            print(f"  {scale_def.scale_id}: {scale_def.scale_name[:50]}...")

    def test_pt_scale_schemas_load(self):
        """Test that PT (On-Site or In-Plant Training) category scales load correctly."""
        scales = load_pt_scale_schemas()

        # Should have 9 scales (PT-1 through PT-9)
        assert len(scales) == 9

        scale_def, semantics = scales[1]
        assert scale_def.scale_id == "PT-1"
        assert scale_def.scale_type == ScaleType.INTERVAL

        print("\nPT Scales (9 on-site training categories):")
        for cat_id, (scale_def, semantics) in sorted(scales.items()):
            print(f"  {scale_def.scale_id}: {scale_def.scale_name[:50]}...")

    def test_oj_scale_schemas_load(self):
        """Test that OJ (On-the-Job Training) category scales load correctly."""
        scales = load_oj_scale_schemas()

        # Should have 9 scales (OJ-1 through OJ-9)
        assert len(scales) == 9

        scale_def, semantics = scales[1]
        assert scale_def.scale_id == "OJ-1"
        assert scale_def.scale_type == ScaleType.INTERVAL
        assert "None or short demonstration" in semantics.meaning

        print("\nOJ Scales (9 on-the-job training categories):")
        for cat_id, (scale_def, semantics) in sorted(scales.items()):
            print(f"  {scale_def.scale_id}: {scale_def.scale_name[:50]}...")

    def test_element_scale_mapping_2d3a_loads(self):
        """Test that element-scale mapping for 2D3A loads correctly."""
        mapping = load_element_scale_mapping_2d3a()

        assert len(mapping) == 6  # 6 elements total
        print(f"\nLoaded scale prefix mappings for {len(mapping)} 2.D/3.A elements")

        # Verify specific mappings (these are PREFIXES, not full scale IDs)
        assert "2.D.1" in mapping
        assert "RL" in mapping["2.D.1"]  # Will expand to RL-1, RL-2, ... RL-12

        assert "3.A.1" in mapping
        assert "RW" in mapping["3.A.1"]  # Will expand to RW-1, RW-2, ... RW-11

        assert "3.A.2" in mapping
        assert "PT" in mapping["3.A.2"]  # Will expand to PT-1, PT-2, ... PT-9

        assert "3.A.3" in mapping
        assert "OJ" in mapping["3.A.3"]  # Will expand to OJ-1, OJ-2, ... OJ-9

        # Print all mappings
        for element_id, scale_prefixes in sorted(mapping.items()):
            print(f"  {element_id}: {scale_prefixes}")

    def test_populate_2d3a_element_scales(self):
        """Test that 2.D and 3.A elements get their scales populated."""
        elements = get_elements()
        populate_2d3a_element_scales(elements)

        # Count elements with scales
        elements_with_scales = 0
        for element_id, element in elements.items():
            if element_id.startswith("2.D.") or element_id.startswith("3.A."):
                if len(element.scales) > 0:
                    elements_with_scales += 1

        print(f"\n2.D/3.A elements with scales populated: {elements_with_scales}")
        assert elements_with_scales == 6

    def test_2d3a_element_scale_details(self):
        """Test details of populated scales on specific elements."""
        elements = get_2d3a_elements()

        # Check 2.D.1 (Required Level of Education) - should have 12 RL scales
        assert "2.D.1" in elements, "2.D.1 should be in elements"
        elem = elements["2.D.1"]

        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Number of scales: {len(elem.scales)}")
        print(f"Scale IDs: {sorted(elem.scales.keys())}")

        # Should have 12 scales: RL-1 through RL-12
        assert len(elem.scales) == 12
        assert "RL-1" in elem.scales
        assert "RL-6" in elem.scales
        assert "RL-12" in elem.scales

        # Check RL-6 (Bachelor's Degree) - should be interval
        rl6_scale = elem.scales["RL-6"]
        assert rl6_scale.scale_def.scale_id == "RL-6"
        assert rl6_scale.scale_def.scale_type == ScaleType.INTERVAL
        assert rl6_scale.interval_semantics is not None
        assert "Bachelor's Degree" in rl6_scale.interval_semantics.meaning
        print(f"\nRL-6 meaning: {rl6_scale.interval_semantics.meaning[:80]}...")

        # Check 3.A.1 (Related Work Experience) - should have 11 RW scales
        assert "3.A.1" in elements, "3.A.1 should be in elements"
        elem = elements["3.A.1"]

        print(f"\n{elem.element_id}: {elem.element_name}")
        print(f"Number of scales: {len(elem.scales)}")

        assert len(elem.scales) == 11
        assert "RW-1" in elem.scales
        assert "RW-11" in elem.scales

    def test_2d3a_elements_count(self):
        """Test that we get the right number of 2.D and 3.A elements."""
        elements = get_2d3a_elements()

        print(f"\nTotal 2.D/3.A elements: {len(elements)}")
        assert len(elements) == 6

        # Show all elements with scale counts
        print("\n2.D/3.A elements with scales:")
        for element_id, element in sorted(elements.items()):
            print(f"  {element_id}: {element.element_name} [{len(element.scales)} scales]")

    def test_2d_elements_count(self):
        """Test 2.D (Education) element count."""
        elements = get_2d_elements()

        print(f"\n2.D elements: {len(elements)}")
        assert len(elements) == 2  # 2.D.1 (12 RL scales) and 2.D.4.a (1 IM scale)

        for element_id, element in sorted(elements.items()):
            print(f"  {element_id}: {element.element_name} [{len(element.scales)} scales]")

    def test_3a_elements_count(self):
        """Test 3.A (Experience and Training) element count."""
        elements = get_3a_elements()

        print(f"\n3.A elements: {len(elements)}")
        assert len(elements) == 4

        for element_id, element in sorted(elements.items()):
            print(f"  {element_id}: {element.element_name} [{len(element.scales)} scales]")

    def test_category_scale_info(self):
        """Test the category scale info helper function."""
        info = get_category_scale_info()

        assert "RL" in info
        assert info["RL"]["element_id"] == "2.D.1"
        assert len(info["RL"]["categories"]) == 12
        assert info["RL"]["scale_ids"] == [f"RL-{i}" for i in range(1, 13)]

        assert "RW" in info
        assert len(info["RW"]["categories"]) == 11

        print("\nCategory scale info (for parsing rating data):")
        for prefix, data in info.items():
            print(f"  {prefix}: element={data['element_id']}, "
                  f"categories={len(data['categories'])}, "
                  f"scales={data['scale_ids'][0]}...{data['scale_ids'][-1]}")

    def test_sample_elementscale_with_value(self):
        """
        Display the raw content of a category scale (RL-6) with a sample value.
        Shows the actual data structure without any interpretation.
        """
        elements = get_2d3a_elements()
        elem = elements["2.D.1"]

        # Get a single category scale
        scale = elem.scales["RL-6"]

        # Simulate setting a value (what happens when rating data is loaded)
        scale.value = 32.29

        print("\n" + "="*80)
        print("ElementScale Content for RL-6 (Bachelor's Degree)")
        print("="*80)

        print(f"\nscale_def.scale_id: {scale.scale_def.scale_id}")
        print(f"scale_def.scale_name: {scale.scale_def.scale_name}")
        print(f"scale_def.scale_type: {scale.scale_def.scale_type}")
        print(f"scale_def.min_value: {scale.scale_def.min_value}")
        print(f"scale_def.max_value: {scale.scale_def.max_value}")

        assert scale.interval_semantics is not None
        print(f"\ninterval_semantics.meaning: {scale.interval_semantics.meaning}")

        print(f"\nvalue: {scale.value}")

        print("="*80)

        # Clean up
        scale.value = None


class TestOccupationPopulate:
    """Tests for occupation population with rating data."""

    def test_occupation_schema_creation(self):
        """Test that occupation schema is created with all elements."""
        schema = create_occupation_schema()

        print(f"\nOccupation schema elements: {len(schema.elements)}")
        # Should have 159 elements total (52 + 12 + 21 + 68 + 6)
        assert len(schema.elements) == 159

    def test_occupation_list_loading(self):
        """Test that occupation list loads correctly."""
        occupation_list = load_occupations_list()

        print(f"\nLoaded {len(occupation_list)} occupations")
        assert len(occupation_list) > 900  # Should have ~1000 occupations

        # Check first few occupations
        print("\nFirst 5 occupations:")
        for occ_id, occ_name, _ in occupation_list[:5]:
            print(f"  {occ_id}: {occ_name}")

    def test_empty_occupations_creation(self):
        """Test that empty occupations are created correctly."""
        schema = create_occupation_schema()
        occupation_list = load_occupations_list()[:5]  # Just test first 5

        occupations = create_empty_occupations(occupation_list, schema)

        assert len(occupations) == 5

        # Check that all elements have scales with None values
        for occ_id, occupation in occupations.items():
            assert len(occupation.elements) == len(schema.elements)
            for elem_id, element in occupation.elements.items():
                for scale_id, scale in element.scales.items():
                    assert scale.value is None

    def test_rating_file_parsing(self):
        """Test that rating files parse correctly."""
        for config in RATING_FILE_CONFIGS:
            ratings = parse_rating_file(config)
            print(f"\n{config.file_name}: {len(ratings)} ratings")
            assert len(ratings) > 0

    def test_spot_check_abilities_values(self):
        """Spot check that populated values match rating file for Abilities."""
        import csv
        import random

        # Parse rating file directly
        rating_dir = get_data_dir() / "occupation_rating"
        file_path = rating_dir / "Abilities.txt"

        # Collect all ratings from file
        file_ratings = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # Skip header

            for row in reader:
                if len(row) < 5:
                    continue
                occ_id = row[0].strip()
                elem_id = row[1].strip()
                scale_id = row[3].strip()
                value_str = row[4].strip()

                if not value_str or value_str.lower() == "n/a":
                    continue

                try:
                    value = float(value_str)
                    file_ratings[(occ_id, elem_id, scale_id)] = value
                except ValueError:
                    continue

        print(f"\nLoaded {len(file_ratings)} ratings from Abilities.txt")

        # Try to load existing occupations, or create new ones
        try:
            occupations = load_occupations()
            print("Loaded existing occupations from pickle")
        except FileNotFoundError:
            print("No existing occupations found, populating...")
            occupations = populate_all_occupations()

        # Randomly sample 20 ratings to spot check
        sample_keys = random.sample(list(file_ratings.keys()), min(20, len(file_ratings)))

        print(f"\nSpot checking {len(sample_keys)} random values:")
        print("-" * 80)

        mismatches = 0
        for occ_id, elem_id, scale_id in sample_keys:
            expected = file_ratings[(occ_id, elem_id, scale_id)]

            if occ_id not in occupations:
                print(f"  SKIP: Occupation {occ_id} not found")
                continue

            occupation = occupations[occ_id]

            if elem_id not in occupation.elements:
                print(f"  SKIP: Element {elem_id} not found in {occ_id}")
                continue

            element = occupation.elements[elem_id]

            if scale_id not in element.scales:
                print(f"  SKIP: Scale {scale_id} not found for {elem_id}")
                continue

            actual = element.scales[scale_id].value

            if actual is None:
                print(f"  MISS: {occ_id}/{elem_id}/{scale_id} = None (expected {expected})")
                mismatches += 1
            elif abs(actual - expected) > 0.01:
                print(f"  FAIL: {occ_id}/{elem_id}/{scale_id} = {actual} (expected {expected})")
                mismatches += 1
            else:
                print(f"  OK:   {occ_id}/{elem_id}/{scale_id} = {actual}")

        print("-" * 80)
        print(f"Mismatches: {mismatches}/{len(sample_keys)}")
        assert mismatches == 0, f"Found {mismatches} mismatches in spot check"

    def test_spot_check_education_category_values(self):
        """Spot check category distribution values (RL scales) from Education file."""
        import csv
        import random

        # Parse rating file directly
        rating_dir = get_data_dir() / "occupation_rating"
        file_path = rating_dir / "Education, Training, and Experience.txt"

        # Collect RL category ratings from file
        file_ratings = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # Skip header

            for row in reader:
                if len(row) < 6:
                    continue
                occ_id = row[0].strip()
                elem_id = row[1].strip()
                raw_scale_id = row[3].strip()
                category = row[4].strip()
                value_str = row[5].strip()

                # Only check RL scales for this test
                if raw_scale_id != "RL":
                    continue

                if not value_str or value_str.lower() == "n/a":
                    continue

                try:
                    value = float(value_str)
                    scale_id = f"RL-{category}"
                    file_ratings[(occ_id, elem_id, scale_id)] = value
                except ValueError:
                    continue

        print(f"\nLoaded {len(file_ratings)} RL category ratings from Education file")

        # Try to load existing occupations
        try:
            occupations = load_occupations()
        except FileNotFoundError:
            occupations = populate_all_occupations()

        # Randomly sample 20 ratings to spot check
        sample_keys = random.sample(list(file_ratings.keys()), min(20, len(file_ratings)))

        print(f"\nSpot checking {len(sample_keys)} random RL category values:")
        print("-" * 80)

        mismatches = 0
        for occ_id, elem_id, scale_id in sample_keys:
            expected = file_ratings[(occ_id, elem_id, scale_id)]

            if occ_id not in occupations:
                continue

            occupation = occupations[occ_id]

            if elem_id not in occupation.elements:
                continue

            element = occupation.elements[elem_id]

            if scale_id not in element.scales:
                print(f"  SKIP: Scale {scale_id} not found for {elem_id}")
                continue

            actual = element.scales[scale_id].value

            if actual is None:
                print(f"  MISS: {occ_id}/{elem_id}/{scale_id} = None (expected {expected})")
                mismatches += 1
            elif abs(actual - expected) > 0.01:
                print(f"  FAIL: {occ_id}/{elem_id}/{scale_id} = {actual} (expected {expected})")
                mismatches += 1
            else:
                print(f"  OK:   {occ_id}/{elem_id}/{scale_id} = {actual:.2f}%")

        print("-" * 80)
        print(f"Mismatches: {mismatches}/{len(sample_keys)}")
        assert mismatches == 0, f"Found {mismatches} mismatches in spot check"

    def test_spot_check_work_styles_values(self):
        """Spot check Work Styles values (WI and DR scales)."""
        import csv
        import random

        # Parse rating file directly
        rating_dir = get_data_dir() / "occupation_rating"
        file_path = rating_dir / "Work Styles.txt"

        # Collect ratings from file
        file_ratings = {}
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # Skip header

            for row in reader:
                if len(row) < 5:
                    continue
                occ_id = row[0].strip()
                elem_id = row[1].strip()
                scale_id = row[3].strip()
                value_str = row[4].strip()

                if not value_str or value_str.lower() == "n/a":
                    continue

                try:
                    value = float(value_str)
                    file_ratings[(occ_id, elem_id, scale_id)] = value
                except ValueError:
                    continue

        print(f"\nLoaded {len(file_ratings)} ratings from Work Styles.txt")

        # Try to load existing occupations
        try:
            occupations = load_occupations()
        except FileNotFoundError:
            occupations = populate_all_occupations()

        # Randomly sample 20 ratings to spot check
        sample_keys = random.sample(list(file_ratings.keys()), min(20, len(file_ratings)))

        print(f"\nSpot checking {len(sample_keys)} random Work Styles values:")
        print("-" * 80)

        mismatches = 0
        for occ_id, elem_id, scale_id in sample_keys:
            expected = file_ratings[(occ_id, elem_id, scale_id)]

            if occ_id not in occupations:
                continue

            occupation = occupations[occ_id]

            if elem_id not in occupation.elements:
                continue

            element = occupation.elements[elem_id]

            if scale_id not in element.scales:
                continue

            actual = element.scales[scale_id].value

            if actual is None:
                print(f"  MISS: {occ_id}/{elem_id}/{scale_id} = None (expected {expected})")
                mismatches += 1
            elif abs(actual - expected) > 0.01:
                print(f"  FAIL: {occ_id}/{elem_id}/{scale_id} = {actual} (expected {expected})")
                mismatches += 1
            else:
                print(f"  OK:   {occ_id}/{elem_id}/{scale_id} = {actual}")

        print("-" * 80)
        print(f"Mismatches: {mismatches}/{len(sample_keys)}")
        assert mismatches == 0, f"Found {mismatches} mismatches in spot check"

    def test_known_values_chief_executives(self):
        """Test specific known values for Chief Executives (11-1011.00)."""
        # Try to load existing occupations
        try:
            occupations = load_occupations()
        except FileNotFoundError:
            occupations = populate_all_occupations()

        ceo = occupations["11-1011.00"]
        assert ceo.occupation_name == "Chief Executives"

        print("\nChief Executives (11-1011.00) known values:")
        print("-" * 60)

        # Known values from Abilities.txt
        oral_comp_im = ceo.elements["1.A.1.a.1"].scales["IM"].value
        oral_comp_lv = ceo.elements["1.A.1.a.1"].scales["LV"].value
        print(f"  Oral Comprehension IM: {oral_comp_im} (expected 4.62)")
        print(f"  Oral Comprehension LV: {oral_comp_lv} (expected 4.88)")
        assert abs(oral_comp_im - 4.62) < 0.01
        assert abs(oral_comp_lv - 4.88) < 0.01

        # Known values from Education file (RL category scales)
        rl_6 = ceo.elements["2.D.1"].scales["RL-6"].value
        rl_8 = ceo.elements["2.D.1"].scales["RL-8"].value
        print(f"  Education RL-6 (Bachelor's): {rl_6:.2f}% (expected 32.29%)")
        print(f"  Education RL-8 (Master's): {rl_8:.2f}% (expected 45.91%)")
        assert abs(rl_6 - 32.29) < 0.01
        assert abs(rl_8 - 45.91) < 0.01

        print("-" * 60)
        print("All known values match!")


# Allow running directly for verbose output
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
