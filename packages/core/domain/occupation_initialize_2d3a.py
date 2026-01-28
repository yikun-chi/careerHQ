"""
occupation_initialize_2d3a.py
=============================

Initializes ElementScale information for 2.D (Education) and 3.A (Experience and Training) elements.

These elements use CATEGORY DISTRIBUTION scales where each category becomes a separate
interval scale measuring the percentage of respondents selecting that category.

Elements and their category scales:
- 2.D.1: Required Level of Education -> RL-1 through RL-12 (12 scales)
- 2.D.4.a: Job-Related Professional Certification -> IM (1 scale, ordinal)
- 3.A.1: Related Work Experience -> RW-1 through RW-11 (11 scales)
- 3.A.2: On-Site or In-Plant Training -> PT-1 through PT-9 (9 scales)
- 3.A.3: On-the-Job Training -> OJ-1 through OJ-9 (9 scales)
- 3.A.4.a: Job-related Apprenticeship -> IM (1 scale, ordinal)

Total: 6 elements, but 2.D.1 has 12 scales, 3.A.1 has 11, 3.A.2 has 9, 3.A.3 has 9.

--------------------------------------------------------------------------------
RATING DATA PARSING GUIDE
--------------------------------------------------------------------------------
Rating data file format (tab-separated):
    O*NET-SOC Code | Element ID | Element Name | Scale ID | Category | Data Value | ...

Example rows:
    11-1011.00  2.D.1  Required Level of Education  RL  1   0.00   ...
    11-1011.00  2.D.1  Required Level of Education  RL  2   4.46   ...
    11-1011.00  2.D.1  Required Level of Education  RL  6   32.29  ...

To parse into ElementScale values:
    1. Read Element ID (e.g., "2.D.1") to find the Element
    2. Read Scale ID (e.g., "RL") and Category (e.g., "6")
    3. Construct scale_id = f"{Scale ID}-{Category}" (e.g., "RL-6")
    4. Set element.scales["RL-6"].value = Data Value (e.g., 32.29)

The value represents: "32.29% of respondents indicated Bachelor's Degree is required"
--------------------------------------------------------------------------------

Data sources:
- occupation_element_scale_mapping_2D3A.csv: Maps elements to scale prefixes
- occupation_scale_rl_schema.json: RL category definitions (12 categories)
- occupation_scale_rw_schema.json: RW category definitions (11 categories)
- occupation_scale_pt_schema.json: PT category definitions (9 categories)
- occupation_scale_oj_schema.json: OJ category definitions (9 categories)
- occupation_scale_im_schema.json: IM scale (reused from 1.A)
"""

import csv
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from .occupation_class import (
    ScaleDefinition,
    ScaleType,
    Element,
    ElementScale,
    IntervalSemantics,
    OrdinalSemantics,
)
from .occupation_initialize import get_elements, get_data_dir
from .occupation_initialize_1a import load_im_scale_schema


def load_category_scale_schema(
    file_path: Path
) -> Tuple[str, str, Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]]:
    """
    Load a category distribution scale schema from JSON.

    Returns a dict mapping category number to (ScaleDefinition, IntervalSemantics).
    Each category becomes a separate interval scale (e.g., RL-1, RL-2, ... RL-12).

    Parameters
    ----------
    file_path : Path
        Path to the scale schema JSON file.

    Returns
    -------
    Tuple[str, str, Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]]
        - scale_id_prefix: e.g., "RL"
        - scale_name: e.g., "Required Level of Education"
        - scales: Dict mapping category int to (ScaleDefinition, IntervalSemantics)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scale_id_prefix = data["scale_id_prefix"]
    scale_name = data["scale_name"]
    meaning_template = data["meaning_template"]

    scales: Dict[int, Tuple[ScaleDefinition, IntervalSemantics]] = {}

    for cat_str, cat_label in data["categories"].items():
        cat_int = int(cat_str)

        # Create scale_id like "RL-6" for category 6
        scale_id = f"{scale_id_prefix}-{cat_int}"

        scale_def = ScaleDefinition(
            scale_id=scale_id,
            scale_name=f"{scale_name}: {cat_label[:50]}",
            min_value=data["min_value"],
            max_value=data["max_value"],
            scale_type=ScaleType.INTERVAL,
        )

        # Meaning is specific to this category (e.g., "Percentage of respondents
        # indicating 'Bachelor's Degree' is the required education level.")
        interval_semantics = IntervalSemantics(
            meaning=meaning_template.format(category=cat_label)
        )

        scales[cat_int] = (scale_def, interval_semantics)

    return scale_id_prefix, scale_name, scales


def load_rl_scale_schemas(file_path: Optional[Path] = None) -> Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]:
    """
    Load RL (Required Level of Education) category scales.

    Returns 12 scales: RL-1 through RL-12.
    Each is an interval scale (0-100%) representing percentage of respondents.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_rl_schema.json"

    _, _, scales = load_category_scale_schema(file_path)
    return scales


def load_rw_scale_schemas(file_path: Optional[Path] = None) -> Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]:
    """
    Load RW (Related Work Experience) category scales.

    Returns 11 scales: RW-1 through RW-11.
    Each is an interval scale (0-100%) representing percentage of respondents.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_rw_schema.json"

    _, _, scales = load_category_scale_schema(file_path)
    return scales


def load_pt_scale_schemas(file_path: Optional[Path] = None) -> Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]:
    """
    Load PT (On-Site or In-Plant Training) category scales.

    Returns 9 scales: PT-1 through PT-9.
    Each is an interval scale (0-100%) representing percentage of respondents.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_pt_schema.json"

    _, _, scales = load_category_scale_schema(file_path)
    return scales


def load_oj_scale_schemas(file_path: Optional[Path] = None) -> Dict[int, Tuple[ScaleDefinition, IntervalSemantics]]:
    """
    Load OJ (On-the-Job Training) category scales.

    Returns 9 scales: OJ-1 through OJ-9.
    Each is an interval scale (0-100%) representing percentage of respondents.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_oj_schema.json"

    _, _, scales = load_category_scale_schema(file_path)
    return scales


def load_element_scale_mapping_2d3a(file_path: Optional[Path] = None) -> Dict[str, List[str]]:
    """
    Load element-to-scale prefix mappings for 2.D and 3.A elements from CSV.

    Note: The CSV file may contain many empty rows which are skipped.

    The mapping returns scale PREFIXES (e.g., "RL", "RW"), not full scale IDs.
    For category scales, the actual scales are "RL-1", "RL-2", etc.

    Returns
    -------
    Dict[str, List[str]]
        Dictionary mapping element_id to list of scale prefixes.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_element_scale_mapping_2D3A.csv"

    mapping: Dict[str, List[str]] = {}

    with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.reader(f)
        next(reader)  # Skip header: Element ID, Element Name, Scale ID, Scale Name

        for row in reader:
            if len(row) < 3:
                continue

            element_id = row[0].strip()
            scale_id = row[2].strip()

            # Skip empty rows (the CSV has many trailing empty rows)
            if not element_id or not scale_id:
                continue

            if element_id not in mapping:
                mapping[element_id] = []
            if scale_id not in mapping[element_id]:
                mapping[element_id].append(scale_id)

    return mapping


def populate_2d3a_element_scales(elements: Optional[Dict[str, Element]] = None) -> Dict[str, Element]:
    """
    Populate ElementScale information for 2.D and 3.A elements.

    This function modifies the Element objects in-place, adding ElementScale
    objects to their scales dict.

    For category distribution scales (RL, RW, PT, OJ):
    - Each element gets multiple scales (e.g., RL-1, RL-2, ... RL-12)
    - Each scale is INTERVAL (0-100%) representing percentage of respondents
    - The value field will be populated later when rating data is loaded

    For ordinal scales (IM):
    - Element gets a single IM scale (Importance 1-5)

    Parameters
    ----------
    elements : Optional[Dict[str, Element]]
        Dictionary of elements. If None, uses global elements from get_elements().

    Returns
    -------
    Dict[str, Element]
        The same elements dict with scales populated for 2.D and 3.A elements.
    """
    if elements is None:
        elements = get_elements()

    # Load all category scale schemas
    rl_scales = load_rl_scale_schemas()  # Dict[int, (ScaleDef, Semantics)]
    rw_scales = load_rw_scale_schemas()
    pt_scales = load_pt_scale_schemas()
    oj_scales = load_oj_scale_schemas()

    # Load IM scale (ordinal, for 2.D.4.a and 3.A.4.a)
    im_scale_def, im_semantics = load_im_scale_schema()

    # Load element-scale mappings
    mapping = load_element_scale_mapping_2d3a()

    # Populate scales for each mapped element
    for element_id, scale_prefixes in mapping.items():
        if element_id not in elements:
            continue

        element = elements[element_id]

        for scale_prefix in scale_prefixes:
            if scale_prefix == "RL":
                # Add all 12 RL category scales
                for cat_int, (scale_def, semantics) in rl_scales.items():
                    element_scale = ElementScale(
                        scale_def=scale_def,
                        interval_semantics=semantics,
                    )
                    element.scales[scale_def.scale_id] = element_scale

            elif scale_prefix == "RW":
                # Add all 11 RW category scales
                for cat_int, (scale_def, semantics) in rw_scales.items():
                    element_scale = ElementScale(
                        scale_def=scale_def,
                        interval_semantics=semantics,
                    )
                    element.scales[scale_def.scale_id] = element_scale

            elif scale_prefix == "PT":
                # Add all 9 PT category scales
                for cat_int, (scale_def, semantics) in pt_scales.items():
                    element_scale = ElementScale(
                        scale_def=scale_def,
                        interval_semantics=semantics,
                    )
                    element.scales[scale_def.scale_id] = element_scale

            elif scale_prefix == "OJ":
                # Add all 9 OJ category scales
                for cat_int, (scale_def, semantics) in oj_scales.items():
                    element_scale = ElementScale(
                        scale_def=scale_def,
                        interval_semantics=semantics,
                    )
                    element.scales[scale_def.scale_id] = element_scale

            elif scale_prefix == "IM":
                # Add single IM ordinal scale
                element_scale = ElementScale(
                    scale_def=im_scale_def,
                    ordinal_semantics=im_semantics,
                )
                element.scales["IM"] = element_scale

    return elements


def get_2d3a_elements() -> Dict[str, Element]:
    """
    Get all 2.D and 3.A elements with their scales populated.

    Returns elements with scales populated:
    - 2.D.1: Required Level of Education (12 scales: RL-1 to RL-12)
    - 2.D.4.a: Job-Related Professional Certification (1 scale: IM)
    - 3.A.1: Related Work Experience (11 scales: RW-1 to RW-11)
    - 3.A.2: On-Site or In-Plant Training (9 scales: PT-1 to PT-9)
    - 3.A.3: On-the-Job Training (9 scales: OJ-1 to OJ-9)
    - 3.A.4.a: Job-related Apprenticeship (1 scale: IM)

    Returns
    -------
    Dict[str, Element]
        Dictionary of 2.D and 3.A elements with scales populated (6 elements).
    """
    elements = get_elements()
    populate_2d3a_element_scales(elements)

    # Filter to only elements that have scales populated
    return {
        k: v for k, v in elements.items()
        if (k.startswith("2.D.") or k.startswith("3.A.")) and len(v.scales) > 0
    }


def get_2d_elements() -> Dict[str, Element]:
    """Get only 2.D (Education) elements with scales populated."""
    all_elements = get_2d3a_elements()
    return {k: v for k, v in all_elements.items() if k.startswith("2.D.")}


def get_3a_elements() -> Dict[str, Element]:
    """Get only 3.A (Experience and Training) elements with scales populated."""
    all_elements = get_2d3a_elements()
    return {k: v for k, v in all_elements.items() if k.startswith("3.A.")}


def get_category_scale_info() -> Dict[str, Dict[str, any]]:
    """
    Get information about category scales for parsing rating data.

    Returns a dict mapping scale prefix to info needed for parsing:
    - element_id: The element that uses this scale
    - categories: List of category numbers
    - scale_ids: List of full scale IDs (e.g., ["RL-1", "RL-2", ...])

    Useful when implementing rating data parser.
    """
    return {
        "RL": {
            "element_id": "2.D.1",
            "categories": list(range(1, 13)),  # 1-12
            "scale_ids": [f"RL-{i}" for i in range(1, 13)],
        },
        "RW": {
            "element_id": "3.A.1",
            "categories": list(range(1, 12)),  # 1-11
            "scale_ids": [f"RW-{i}" for i in range(1, 12)],
        },
        "PT": {
            "element_id": "3.A.2",
            "categories": list(range(1, 10)),  # 1-9
            "scale_ids": [f"PT-{i}" for i in range(1, 10)],
        },
        "OJ": {
            "element_id": "3.A.3",
            "categories": list(range(1, 10)),  # 1-9
            "scale_ids": [f"OJ-{i}" for i in range(1, 10)],
        },
    }
