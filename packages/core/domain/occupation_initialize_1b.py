"""
occupation_initialize_1b.py
===========================

Initializes ElementScale information for 1.B (Interests and Work Values) elements.

1.B elements use two scales:
- OI (Occupational Interests): Interval scale 1-7 for 1.B.1 elements
- EX (Extent): Interval scale 1-7 for 1.B.2 elements

NOTE: 1.B.3 (Basic Occupational Interests) elements are intentionally skipped.
They are not included in the mapping file by design.

Data sources:
- occupation_element_scale_mapping_1B.csv: Maps elements to scales
- occupation_scale_oi_schema.json: OI scale definition
- occupation_scale_ex_schema.json: EX scale definition
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
)
from .occupation_initialize import get_elements, get_scale_definitions, get_data_dir


def load_oi_scale_schema(file_path: Optional[Path] = None) -> tuple[ScaleDefinition, IntervalSemantics]:
    """
    Load the OI (Occupational Interests) scale schema from JSON.

    Returns
    -------
    tuple[ScaleDefinition, IntervalSemantics]
        The scale definition and interval semantics for the OI scale.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_oi_schema.json"

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


def load_ex_scale_schema(file_path: Optional[Path] = None) -> tuple[ScaleDefinition, IntervalSemantics]:
    """
    Load the EX (Extent) scale schema from JSON.

    Returns
    -------
    tuple[ScaleDefinition, IntervalSemantics]
        The scale definition and interval semantics for the EX scale.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_ex_schema.json"

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


def load_element_scale_mapping_1b(file_path: Optional[Path] = None) -> Dict[str, list[str]]:
    """
    Load element-to-scale mappings for 1.B elements from CSV.

    Returns
    -------
    Dict[str, list[str]]
        Dictionary mapping element_id to list of scale_ids.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_element_scale_mapping_1B.csv"

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


def populate_1b_element_scales(elements: Optional[Dict[str, Element]] = None) -> Dict[str, Element]:
    """
    Populate ElementScale information for 1.B (Interests and Work Values) elements.

    This function modifies the Element objects in-place, adding ElementScale
    objects to their scales dict for OI and EX scales.

    NOTE: 1.B.3 (Basic Occupational Interests) elements are intentionally not
    populated with scales. They are excluded from the mapping file by design.

    Parameters
    ----------
    elements : Optional[Dict[str, Element]]
        Dictionary of elements. If None, uses global elements from get_elements().

    Returns
    -------
    Dict[str, Element]
        The same elements dict with scales populated for 1.B.1 and 1.B.2 elements.
    """
    if elements is None:
        elements = get_elements()

    # Load scale schemas
    oi_scale_def, oi_semantics = load_oi_scale_schema()
    ex_scale_def, ex_semantics = load_ex_scale_schema()

    # Load element-scale mappings
    mapping = load_element_scale_mapping_1b()

    # Populate scales for each mapped 1.B element
    for element_id, scale_ids in mapping.items():
        if element_id not in elements:
            continue

        element = elements[element_id]

        for scale_id in scale_ids:
            if scale_id == "OI":
                element_scale = ElementScale(
                    scale_def=oi_scale_def,
                    interval_semantics=oi_semantics,
                )
                element.scales["OI"] = element_scale

            elif scale_id == "EX":
                element_scale = ElementScale(
                    scale_def=ex_scale_def,
                    interval_semantics=ex_semantics,
                )
                element.scales["EX"] = element_scale

    return elements


def get_1b_elements() -> Dict[str, Element]:
    """
    Get all 1.B elements with their scales populated.

    Returns only elements that have scales populated:
    - 1.B.1.a-f (6 elements) with OI scale
    - 1.B.2.a-f (6 elements) with EX scale

    1.B.3 elements are intentionally excluded as they don't have scale mappings.

    Returns
    -------
    Dict[str, Element]
        Dictionary of 1.B elements with scales populated (12 total).
    """
    elements = get_elements()
    populate_1b_element_scales(elements)

    # Filter to only elements that have scales populated
    return {
        k: v for k, v in elements.items()
        if k.startswith("1.B.") and len(v.scales) > 0
    }
