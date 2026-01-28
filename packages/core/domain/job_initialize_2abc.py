"""
job_initialize_2abc.py
======================

Initializes ElementScale information for 2.A, 2.B, and 2.C elements.

2.A (Basic Skills): 10 elements
2.B (Cross-Functional Skills): 25 elements
2.C (Knowledge): 33 elements

All elements use two scales:
- IM (Importance): Universal ordinal scale 1-5
- LV (Level): Ordinal scale 0-7 with element-specific anchors

Data sources:
- job_element_scale_mapping_2ABC.csv: Maps elements to scales
- job_scale_im_schema.json: IM scale definition and categories
- Level Scale Anchors.txt: Element-specific LV anchors
"""

import csv
import json
from typing import Dict, Optional
from pathlib import Path

from .job_class import (
    ScaleDefinition,
    ScaleType,
    Element,
    ElementScale,
    OrdinalSemantics,
)
from .job_initialize import get_elements, get_scale_definitions, get_data_dir
from .job_initialize_1a import load_im_scale_schema


def load_lv_anchors_2abc(file_path: Optional[Path] = None) -> Dict[str, OrdinalSemantics]:
    """
    Load LV (Level) anchors from Level Scale Anchors.txt for 2.A, 2.B, 2.C elements.

    The LV scale has element-specific anchors, so we return a dict
    mapping element_id to its OrdinalSemantics.

    Returns
    -------
    Dict[str, OrdinalSemantics]
        Dictionary mapping element_id to OrdinalSemantics with anchors.
    """
    if file_path is None:
        file_path = get_data_dir() / "Level Scale Anchors.txt"

    # Collect anchors per element
    element_anchors: Dict[str, Dict[int, str]] = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header: Element ID, Element Name, Scale ID, Anchor Value, Anchor Description

        for row in reader:
            if len(row) < 5:
                continue

            element_id = row[0].strip()
            scale_id = row[2].strip()
            anchor_value = row[3].strip()
            anchor_desc = row[4].strip()

            # Only process LV scale and 2.A, 2.B, 2.C elements
            if scale_id != "LV":
                continue
            if not (element_id.startswith("2.A") or
                    element_id.startswith("2.B") or
                    element_id.startswith("2.C")):
                continue

            try:
                anchor_int = int(anchor_value)
            except ValueError:
                continue

            if element_id not in element_anchors:
                element_anchors[element_id] = {}

            element_anchors[element_id][anchor_int] = anchor_desc

    # Convert to OrdinalSemantics
    result: Dict[str, OrdinalSemantics] = {}
    for element_id, anchors in element_anchors.items():
        result[element_id] = OrdinalSemantics(categories=anchors)

    return result


def load_element_scale_mapping_2abc(file_path: Optional[Path] = None) -> Dict[str, list[str]]:
    """
    Load element-to-scale mappings for 2.A, 2.B, 2.C elements from CSV.

    Returns
    -------
    Dict[str, list[str]]
        Dictionary mapping element_id to list of scale_ids.
    """
    if file_path is None:
        file_path = get_data_dir() / "job_element_scale_mapping_2ABC.csv"

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


def populate_2abc_element_scales(elements: Optional[Dict[str, Element]] = None) -> Dict[str, Element]:
    """
    Populate ElementScale information for 2.A, 2.B, 2.C elements.

    This function modifies the Element objects in-place, adding ElementScale
    objects to their scales dict for IM and LV scales.

    Parameters
    ----------
    elements : Optional[Dict[str, Element]]
        Dictionary of elements. If None, uses global elements from get_elements().

    Returns
    -------
    Dict[str, Element]
        The same elements dict with scales populated for 2.A, 2.B, 2.C elements.
    """
    if elements is None:
        elements = get_elements()

    # Load scale definitions
    scale_defs = get_scale_definitions()

    # Load IM scale schema (universal for all elements)
    im_scale_def, im_semantics = load_im_scale_schema()

    # Load LV anchors (element-specific)
    lv_anchors = load_lv_anchors_2abc()

    # Get LV scale definition from global scale defs
    lv_scale_def = scale_defs.get("LV")
    if lv_scale_def is None:
        # Create default LV scale definition if not in global defs
        lv_scale_def = ScaleDefinition(
            scale_id="LV",
            scale_name="Level",
            min_value=0,
            max_value=7,
            scale_type=ScaleType.ORDINAL,
        )

    # Load element-scale mappings
    mapping = load_element_scale_mapping_2abc()

    # Populate scales for each 2.A, 2.B, 2.C element
    for element_id, scale_ids in mapping.items():
        if element_id not in elements:
            continue

        element = elements[element_id]

        for scale_id in scale_ids:
            if scale_id == "IM":
                # IM scale uses universal semantics
                element_scale = ElementScale(
                    scale_def=im_scale_def,
                    ordinal_semantics=im_semantics,
                )
                element.scales["IM"] = element_scale

            elif scale_id == "LV":
                # LV scale uses element-specific anchors
                lv_semantics = lv_anchors.get(element_id)
                if lv_semantics:
                    element_scale = ElementScale(
                        scale_def=lv_scale_def,
                        ordinal_semantics=lv_semantics,
                    )
                    element.scales["LV"] = element_scale

    return elements


def get_2abc_elements() -> Dict[str, Element]:
    """
    Get all 2.A, 2.B, 2.C elements with their scales populated.

    Returns elements with IM and LV scales populated:
    - 2.A (Basic Skills): 10 elements
    - 2.B (Cross-Functional Skills): 25 elements
    - 2.C (Knowledge): 33 elements

    Returns
    -------
    Dict[str, Element]
        Dictionary of 2.A, 2.B, 2.C elements with scales populated (68 total).
    """
    elements = get_elements()
    populate_2abc_element_scales(elements)

    # Filter to only elements that have scales populated
    return {
        k: v for k, v in elements.items()
        if (k.startswith("2.A.") or k.startswith("2.B.") or k.startswith("2.C.") or k == "2.C.6" or k == "2.C.10")
        and len(v.scales) > 0
    }


def get_2a_elements() -> Dict[str, Element]:
    """Get only 2.A (Basic Skills) elements with scales populated."""
    all_elements = get_2abc_elements()
    return {k: v for k, v in all_elements.items() if k.startswith("2.A.")}


def get_2b_elements() -> Dict[str, Element]:
    """Get only 2.B (Cross-Functional Skills) elements with scales populated."""
    all_elements = get_2abc_elements()
    return {k: v for k, v in all_elements.items() if k.startswith("2.B.")}


def get_2c_elements() -> Dict[str, Element]:
    """Get only 2.C (Knowledge) elements with scales populated."""
    all_elements = get_2abc_elements()
    return {k: v for k, v in all_elements.items() if k.startswith("2.C")}