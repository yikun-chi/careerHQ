"""
occupation_initialize_1a.py
===========================

Initializes ElementScale information for 1.A (Abilities) elements.

1.A elements use two scales:
- IM (Importance): Universal ordinal scale 1-5
- LV (Level): Ordinal scale 0-7 with element-specific anchors

Data sources:
- occupation_element_scale_mapping_1A.csv: Maps elements to scales
- occupation_scale_im_schema.json: IM scale definition and categories
- Level Scale Anchors.txt: Element-specific LV anchors
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
    OrdinalSemantics,
)
from .occupation_initialize import get_elements, get_scale_definitions, get_data_dir


def load_im_scale_schema(file_path: Optional[Path] = None) -> tuple[ScaleDefinition, OrdinalSemantics]:
    """
    Load the IM (Importance) scale schema from JSON.

    Returns
    -------
    tuple[ScaleDefinition, OrdinalSemantics]
        The scale definition and ordinal semantics for the IM scale.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_scale_im_schema.json"

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


def load_lv_anchors(file_path: Optional[Path] = None) -> Dict[str, OrdinalSemantics]:
    """
    Load LV (Level) anchors from Level Scale Anchors.txt.

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

            # Only process LV scale and 1.A elements
            if scale_id != "LV" or not element_id.startswith("1.A"):
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


def load_element_scale_mapping(file_path: Optional[Path] = None) -> Dict[str, list[str]]:
    """
    Load element-to-scale mappings from CSV.

    Returns
    -------
    Dict[str, list[str]]
        Dictionary mapping element_id to list of scale_ids.
    """
    if file_path is None:
        file_path = get_data_dir() / "occupation_element_scale_mapping_1A.csv"

    mapping: Dict[str, list[str]] = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header: element_id, element_name, scale_id

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


def populate_1a_element_scales(elements: Optional[Dict[str, Element]] = None) -> Dict[str, Element]:
    """
    Populate ElementScale information for all 1.A (Abilities) elements.

    This function modifies the Element objects in-place, adding ElementScale
    objects to their scales dict for IM and LV scales.

    Parameters
    ----------
    elements : Optional[Dict[str, Element]]
        Dictionary of elements. If None, uses global elements from get_elements().

    Returns
    -------
    Dict[str, Element]
        The same elements dict with scales populated for 1.A elements.
    """
    if elements is None:
        elements = get_elements()

    # Load scale definitions
    scale_defs = get_scale_definitions()

    # Load IM scale schema (universal for all elements)
    im_scale_def, im_semantics = load_im_scale_schema()

    # Load LV anchors (element-specific)
    lv_anchors = load_lv_anchors()

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
    mapping = load_element_scale_mapping()

    # Populate scales for each 1.A element
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


def get_1a_elements() -> Dict[str, Element]:
    """
    Get all 1.A elements with their scales populated.

    Returns
    -------
    Dict[str, Element]
        Dictionary of 1.A elements with IM and LV scales populated.
    """
    elements = get_elements()
    populate_1a_element_scales(elements)

    # Filter to only 1.A elements
    return {k: v for k, v in elements.items() if k.startswith("1.A.")}