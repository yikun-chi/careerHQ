"""
occupation_initialize_1d.py
===========================

Initializes ElementScale information for 1.D (Work Styles) elements.

1.D elements use two scales:
- WI (Work Styles Impact): Interval scale -3.0 to +3.0
- DR (Distinctiveness Rank): Ordinal scale 0-10

Data sources:
- occupation_element_scale_mapping_1D.csv: Maps elements to scales
- occupation_scale_wi_schema.json: WI scale definition
- occupation_scale_dr_schema.json: DR scale definition
"""

import csv
import json
from typing import Dict, Optional
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


def load_wi_scale_schema(file_path: Optional[Path] = None) -> tuple[ScaleDefinition, IntervalSemantics]:
    """
    Load the WI (Work Styles Impact) scale schema from JSON.

    Returns
    -------
    tuple[ScaleDefinition, IntervalSemantics]
        The scale definition and interval semantics for the WI scale.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_wi_schema.json"

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scale_def = ScaleDefinition(
        scale_id=data["scale_id"],
        scale_name=data["scale_name"],
        min_value=data["min_value"],
        max_value=data["max_value"],
        scale_type=ScaleType.INTERVAL,
    )

    interval_semantics = IntervalSemantics(meaning=data["meaning"])

    return scale_def, interval_semantics


def load_dr_scale_schema(file_path: Optional[Path] = None) -> tuple[ScaleDefinition, OrdinalSemantics]:
    """
    Load the DR (Distinctiveness Rank) scale schema from JSON.

    Returns
    -------
    tuple[ScaleDefinition, OrdinalSemantics]
        The scale definition and ordinal semantics for the DR scale.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_dr_schema.json"

    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scale_def = ScaleDefinition(
        scale_id=data["scale_id"],
        scale_name=data["scale_name"],
        min_value=data["min_value"],
        max_value=data["max_value"],
        scale_type=ScaleType.ORDINAL,
    )

    # Convert string keys to int for categories
    categories = {int(k): v for k, v in data["categories"].items()}
    ordinal_semantics = OrdinalSemantics(categories=categories)

    return scale_def, ordinal_semantics


def load_element_scale_mapping_1d(file_path: Optional[Path] = None) -> Dict[str, list[str]]:
    """
    Load element-to-scale mappings for 1.D elements from CSV.

    Returns
    -------
    Dict[str, list[str]]
        Dictionary mapping element_id to list of scale_ids.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_element_scale_mapping_1D.csv"

    mapping: Dict[str, list[str]] = {}

    with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        reader = csv.reader(f)
        next(reader)  # Skip header: Element ID, Element Name, Scale ID, Scale Name

        for row in reader:
            if len(row) < 3:
                continue

            element_id = row[0].strip()
            scale_id = row[2].strip()

            if element_id not in mapping:
                mapping[element_id] = []
            if scale_id not in mapping[element_id]:
                mapping[element_id].append(scale_id)

    return mapping


def populate_1d_element_scales(elements: Optional[Dict[str, Element]] = None) -> Dict[str, Element]:
    """
    Populate ElementScale information for 1.D (Work Styles) elements.

    This function modifies the Element objects in-place, adding ElementScale
    objects to their scales dict for WI and DR scales.

    Parameters
    ----------
    elements : Optional[Dict[str, Element]]
        Dictionary of elements. If None, uses global elements from get_elements().

    Returns
    -------
    Dict[str, Element]
        The same elements dict with scales populated for 1.D elements.
    """
    if elements is None:
        elements = get_elements()

    # Load scale schemas
    wi_scale_def, wi_semantics = load_wi_scale_schema()
    dr_scale_def, dr_semantics = load_dr_scale_schema()

    # Load element-scale mappings
    mapping = load_element_scale_mapping_1d()

    # Populate scales for each mapped 1.D element
    for element_id, scale_ids in mapping.items():
        if element_id not in elements:
            continue

        element = elements[element_id]

        for scale_id in scale_ids:
            if scale_id == "WI":
                element_scale = ElementScale(
                    scale_def=wi_scale_def,
                    interval_semantics=wi_semantics,
                )
                element.scales["WI"] = element_scale

            elif scale_id == "DR":
                element_scale = ElementScale(
                    scale_def=dr_scale_def,
                    ordinal_semantics=dr_semantics,
                )
                element.scales["DR"] = element_scale

    return elements


def get_1d_elements() -> Dict[str, Element]:
    """
    Get all 1.D elements with their scales populated.

    Returns only elements that have scales populated:
    - 1.D.1.a-i (9 elements): Achievement/Innovation Work Styles
    - 1.D.2.a-f (6 elements): Interpersonal Orientation Work Styles
    - 1.D.3.a-d (4 elements): Conscientiousness Work Styles
    - 1.D.4.a-b (2 elements): Adjustment Work Styles

    Each element has both WI and DR scales.

    Returns
    -------
    Dict[str, Element]
        Dictionary of 1.D elements with scales populated (21 total).
    """
    elements = get_elements()
    populate_1d_element_scales(elements)

    # Filter to only elements that have scales populated
    return {
        k: v for k, v in elements.items()
        if k.startswith("1.D.") and len(v.scales) > 0
    }