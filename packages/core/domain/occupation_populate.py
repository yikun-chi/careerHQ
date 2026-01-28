"""
occupation_populate.py
======================

Populates Occupation objects with rating data from O*NET files.

This module:
1. Creates an OccupationSchema by combining all initialized elements
2. Loads occupation list from "Occupation Data.txt"
3. Parses rating files to extract values
4. Populates Occupation objects with actual values
5. Saves/loads populated occupations to/from initialized/ folder

Usage:
    from packages.core.domain.occupation_populate import populate_all_occupations, load_occupations

    # First time: populate and save
    occupations = populate_all_occupations()

    # Later: load from saved file
    occupations = load_occupations()

    # Access data
    ceo = occupations["11-1011.00"]
    oral_comp_importance = ceo.elements["1.A.1.a.1"].scales["IM"].value
"""

import csv
import pickle
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

from .occupation_class import (
    Occupation,
    OccupationSchema,
    Element,
    ElementTemplate,
)
from .occupation_initialize import get_data_dir, load_elements
from .occupation_initialize_1a import populate_1a_element_scales
from .occupation_initialize_1b import populate_1b_element_scales
from .occupation_initialize_1d import populate_1d_element_scales
from .occupation_initialize_2abc import populate_2abc_element_scales
from .occupation_initialize_2d3a import populate_2d3a_element_scales


@dataclass
class RatingFileConfig:
    """Configuration for parsing a rating file."""
    file_name: str
    has_category_column: bool  # True for Education file
    category_scales: Set[str]  # {"RL", "RW", "PT", "OJ"} for Education file
    value_column_index: int  # Column index for Data Value (0-based)


# Rating file configurations
RATING_FILE_CONFIGS: List[RatingFileConfig] = [
    # Standard format: O*NET Code, Element ID, Element Name, Scale ID, Data Value, ...
    RatingFileConfig(
        file_name="Abilities.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    RatingFileConfig(
        file_name="Skills.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    RatingFileConfig(
        file_name="Knowledge.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    # Simple format: O*NET Code, Element ID, Element Name, Scale ID, Data Value, Date, Source
    RatingFileConfig(
        file_name="Work Styles.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    RatingFileConfig(
        file_name="Interests.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    RatingFileConfig(
        file_name="Work Values.txt",
        has_category_column=False,
        category_scales=set(),
        value_column_index=4,
    ),
    # Category format: O*NET Code, Element ID, Element Name, Scale ID, Category, Data Value, ...
    RatingFileConfig(
        file_name="Education, Training, and Experience.txt",
        has_category_column=True,
        category_scales={"RL", "RW", "PT", "OJ"},
        value_column_index=5,  # Data Value is after Category column
    ),
]


def create_occupation_schema() -> OccupationSchema:
    """
    Build the canonical OccupationSchema by combining all element templates.

    This calls all populate_*_element_scales functions to build fully-defined
    Element objects with scales, then converts them to ElementTemplates.

    Returns
    -------
    OccupationSchema
        Schema containing all elements as templates (159 elements with scales).
    """
    # Load fresh elements (not from cache to avoid side effects)
    elements = load_elements()

    # Populate scales for all element categories
    populate_1a_element_scales(elements)
    populate_1b_element_scales(elements)
    populate_1d_element_scales(elements)
    populate_2abc_element_scales(elements)
    populate_2d3a_element_scales(elements)

    # Filter to only elements with scales and convert to templates
    templates: Dict[str, ElementTemplate] = {}

    for element_id, element in elements.items():
        if len(element.scales) > 0:
            template = ElementTemplate(
                element_id=element.element_id,
                element_name=element.element_name,
                scales=element.scales,
            )
            templates[element_id] = template

    return OccupationSchema(elements=templates)


def load_occupations_list(file_path: Optional[Path] = None) -> List[Tuple[str, str, str]]:
    """
    Parse Occupation Data.txt and return list of occupations.

    Parameters
    ----------
    file_path : Optional[Path]
        Path to Occupation Data.txt. If None, uses default location.

    Returns
    -------
    List[Tuple[str, str, str]]
        List of (occupation_id, occupation_name, description) tuples.
    """
    if file_path is None:
        file_path = get_data_dir() / "Occupation Data.txt"

    occupations: List[Tuple[str, str, str]] = []

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header: O*NET-SOC Code, Title, Description

        for row in reader:
            if len(row) < 2:
                continue

            occupation_id = row[0].strip()
            occupation_name = row[1].strip()
            description = row[2].strip() if len(row) > 2 else ""

            if not occupation_id or not occupation_name:
                continue

            occupations.append((occupation_id, occupation_name, description))

    return occupations


def create_empty_occupations(
    occupation_list: List[Tuple[str, str, str]],
    schema: OccupationSchema
) -> Dict[str, Occupation]:
    """
    Create Occupation objects for each occupation in the list.

    All occupations are initialized with the same element structure
    from the schema, but with all values set to None.

    Parameters
    ----------
    occupation_list : List[Tuple[str, str, str]]
        List of (occupation_id, occupation_name, description) tuples.
    schema : OccupationSchema
        The canonical schema defining all elements.

    Returns
    -------
    Dict[str, Occupation]
        Dictionary mapping occupation_id to Occupation objects.
    """
    occupations: Dict[str, Occupation] = {}

    for occupation_id, occupation_name, _description in occupation_list:
        occupation = Occupation.from_schema(
            occupation_id=occupation_id,
            occupation_name=occupation_name,
            schema=schema,
        )
        occupations[occupation_id] = occupation

    return occupations


def parse_rating_file(
    config: RatingFileConfig,
    rating_dir: Optional[Path] = None,
) -> Dict[Tuple[str, str, str], float]:
    """
    Parse a rating file and return mapping of (occupation_id, element_id, scale_id) -> value.

    Handles both standard format and category format files.

    Parameters
    ----------
    config : RatingFileConfig
        Configuration for the rating file.
    rating_dir : Optional[Path]
        Directory containing rating files. If None, uses default location.

    Returns
    -------
    Dict[Tuple[str, str, str], float]
        Dictionary mapping (occupation_id, element_id, scale_id) to value.
    """
    if rating_dir is None:
        rating_dir = get_data_dir() / "occupation_rating"

    file_path = rating_dir / config.file_name
    ratings: Dict[Tuple[str, str, str], float] = {}

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header

        for row in reader:
            if len(row) < config.value_column_index + 1:
                continue

            occupation_id = row[0].strip()
            element_id = row[1].strip()
            raw_scale_id = row[3].strip()

            if not occupation_id or not element_id or not raw_scale_id:
                continue

            # Handle category scales (RL -> RL-6)
            if config.has_category_column and raw_scale_id in config.category_scales:
                category = row[4].strip()
                scale_id = f"{raw_scale_id}-{category}"
                value_str = row[config.value_column_index].strip()
            else:
                scale_id = raw_scale_id
                value_str = row[config.value_column_index].strip()

            # Skip n/a or empty values
            if not value_str or value_str.lower() == "n/a":
                continue

            # Parse value
            try:
                value = float(value_str)
            except ValueError:
                continue

            key = (occupation_id, element_id, scale_id)
            ratings[key] = value

    return ratings


@dataclass
class PopulationStats:
    """Statistics about the population process."""
    total_occupations: int
    total_possible_scales: int
    populated_scales: int
    missing_scales: int


def populate_occupation_values(
    occupations: Dict[str, Occupation],
    ratings: Dict[Tuple[str, str, str], float],
) -> PopulationStats:
    """
    Apply rating values to occupations.

    Parameters
    ----------
    occupations : Dict[str, Occupation]
        Dictionary of occupation objects to populate.
    ratings : Dict[Tuple[str, str, str], float]
        Dictionary mapping (occupation_id, element_id, scale_id) to value.

    Returns
    -------
    PopulationStats
        Statistics about the population process.
    """
    populated = 0
    missing = 0
    total_possible = 0

    for occ_id, occupation in occupations.items():
        for elem_id, element in occupation.elements.items():
            for scale_id, element_scale in element.scales.items():
                total_possible += 1
                key = (occ_id, elem_id, scale_id)

                if key in ratings:
                    element_scale.value = ratings[key]
                    populated += 1
                else:
                    missing += 1

    return PopulationStats(
        total_occupations=len(occupations),
        total_possible_scales=total_possible,
        populated_scales=populated,
        missing_scales=missing,
    )


def save_occupations(
    occupations: Dict[str, Occupation],
    output_dir: Optional[Path] = None,
) -> None:
    """
    Save occupations to the initialized/ folder.

    Saves as pickle for fast loading, plus a JSON summary for inspection.

    Parameters
    ----------
    occupations : Dict[str, Occupation]
        Dictionary of occupation objects to save.
    output_dir : Optional[Path]
        Output directory. If None, uses default initialized/ folder.
    """
    if output_dir is None:
        output_dir = get_data_dir() / "initialized"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Save as pickle
    with open(output_dir / "occupations.pkl", "wb") as f:
        pickle.dump(occupations, f)

    # Generate JSON summary for inspection
    summary = {
        "total_occupations": len(occupations),
        "occupations": {
            occ_id: {
                "name": occ.occupation_name,
                "element_count": len(occ.elements),
                "populated_scales": sum(
                    1 for elem in occ.elements.values()
                    for scale in elem.scales.values()
                    if scale.value is not None
                ),
                "total_scales": sum(
                    len(elem.scales) for elem in occ.elements.values()
                ),
            }
            for occ_id, occ in occupations.items()
        },
    }

    with open(output_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def load_occupations(input_dir: Optional[Path] = None) -> Dict[str, Occupation]:
    """
    Load previously saved occupations from the initialized/ folder.

    Parameters
    ----------
    input_dir : Optional[Path]
        Input directory. If None, uses default initialized/ folder.

    Returns
    -------
    Dict[str, Occupation]
        Dictionary of occupation objects.
    """
    if input_dir is None:
        input_dir = get_data_dir() / "initialized"

    with open(input_dir / "occupations.pkl", "rb") as f:
        return pickle.load(f)


def populate_all_occupations(
    output_dir: Optional[Path] = None,
) -> Dict[str, Occupation]:
    """
    Main entry point: orchestrate the entire population process.

    1. Creates OccupationSchema from all element initializers
    2. Loads occupation list from Occupation Data.txt
    3. Creates empty occupations from schema
    4. Parses all rating files and populates values
    5. Saves populated occupations to initialized/ folder

    Parameters
    ----------
    output_dir : Optional[Path]
        Output directory for saving. If None, uses default initialized/ folder.

    Returns
    -------
    Dict[str, Occupation]
        Dictionary of populated occupation objects.
    """
    print("Creating occupation schema...")
    schema = create_occupation_schema()
    print(f"  Created schema with {len(schema.elements)} elements")

    print("Loading occupation list...")
    occupation_list = load_occupations_list()
    print(f"  Loaded {len(occupation_list)} occupations")

    print("Creating empty occupations...")
    occupations = create_empty_occupations(occupation_list, schema)

    print("Parsing rating files and populating values...")
    all_ratings: Dict[Tuple[str, str, str], float] = {}

    for config in RATING_FILE_CONFIGS:
        print(f"  Parsing {config.file_name}...")
        ratings = parse_rating_file(config)
        all_ratings.update(ratings)
        print(f"    Found {len(ratings)} ratings")

    print("Populating occupation values...")
    stats = populate_occupation_values(occupations, all_ratings)

    coverage = (stats.populated_scales / stats.total_possible_scales * 100) if stats.total_possible_scales > 0 else 0
    print(f"  Populated {stats.populated_scales}/{stats.total_possible_scales} scales ({coverage:.1f}% coverage)")

    print("Saving occupations...")
    save_occupations(occupations, output_dir)
    print(f"  Saved to {output_dir or get_data_dir() / 'initialized'}")

    return occupations
