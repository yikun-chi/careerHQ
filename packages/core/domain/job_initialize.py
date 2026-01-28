"""
job_initialize.py
=================

This module initializes all the static data structures needed for the O*NET job model:
- OrganizationRegistry: Hierarchical taxonomy of element categories
- Scale definitions from the scale reference file

It reads from the data files in packages/core/data/ and builds the registries.
"""

import csv
from typing import Dict, Optional, Tuple, Set
from pathlib import Path

from .job_class import (
    OrganizationRegistry,
    OrganizationNode,
    ScaleDefinition,
    ScaleType,
    Element,
)


def get_data_dir() -> Path:
    """Get the path to the data directory."""
    module_dir = Path(__file__).parent
    core_dir = module_dir.parent
    return core_dir / "data"


def load_organization_registry(file_path: Optional[Path] = None) -> OrganizationRegistry:
    """
    Load the O*NET Content Model hierarchy and create an OrganizationRegistry.

    This parses the Content Model Reference.txt file which contains the hierarchical
    structure of O*NET elements. Organization nodes are the intermediate levels in
    the hierarchy (e.g., "1.A", "2.B.3") that categorize individual elements.

    Parameters
    ----------
    file_path : Optional[Path]
        Path to Content Model Reference.txt. If None, uses default location.

    Returns
    -------
    OrganizationRegistry
        Registry containing all organization nodes from the content model.
    """
    if file_path is None:
        file_path = get_data_dir() / "Content Model Reference.txt"

    # First pass: Build a complete lookup of all elements
    element_lookup: Dict[str, Tuple[str, Optional[str]]] = {}
    all_element_ids: Set[str] = set()

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 3:
                continue

            element_id = row[0].strip()
            element_name = row[1].strip()
            description = row[2].strip() if len(row) > 2 else None

            if not element_id or not element_name:
                continue

            element_lookup[element_id] = (element_name, description)
            all_element_ids.add(element_id)

    # Second pass: Identify organization nodes
    # An element is an organization node if:
    # 1. It exists in the data AND
    # 2. Its name equals its description (category nodes) OR
    # 3. Other elements have it as a prefix (it has children)

    org_node_ids: Set[str] = set()

    # Check which IDs have children
    for element_id in all_element_ids:
        parts = element_id.split(".")
        # Add all prefixes as potential org nodes
        for i in range(1, len(parts)):
            prefix = ".".join(parts[:i])
            org_node_ids.add(prefix)

        # Also check if this element itself is an organization node
        if element_id in element_lookup:
            name, desc = element_lookup[element_id]
            # If name equals description, it's a category/organization node
            if name == desc or (desc and desc.startswith(name)):
                org_node_ids.add(element_id)

    # Build the final organization nodes
    final_org_nodes: Dict[str, OrganizationNode] = {}

    for org_id in org_node_ids:
        if org_id in element_lookup:
            name, desc = element_lookup[org_id]
            final_org_nodes[org_id] = OrganizationNode(
                org_id=org_id,
                name=name,
                description=desc if name != desc else None
            )

    return OrganizationRegistry(nodes=final_org_nodes)


def load_elements(file_path: Optional[Path] = None) -> Dict[str, Element]:
    """
    Load all leaf elements from the O*NET Content Model hierarchy.

    Leaf elements are those that don't have any children in the hierarchy.
    These are the actual measurable attributes (e.g., "1.A.1.a.1 Oral Comprehension")
    as opposed to organization nodes which are categories (e.g., "1.A Abilities").

    Parameters
    ----------
    file_path : Optional[Path]
        Path to Content Model Reference.txt. If None, uses default location.

    Returns
    -------
    Dict[str, Element]
        Dictionary mapping element_id to Element objects (without scales populated).
    """
    if file_path is None:
        file_path = get_data_dir() / "Content Model Reference.txt"

    # First pass: Read all entries and track which IDs exist
    all_entries: Dict[str, Tuple[str, Optional[str]]] = {}
    all_ids: Set[str] = set()

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 2:
                continue

            element_id = row[0].strip()
            element_name = row[1].strip()
            description = row[2].strip() if len(row) > 2 else None

            if not element_id or not element_name:
                continue

            all_entries[element_id] = (element_name, description)
            all_ids.add(element_id)

    # Second pass: Identify parent IDs (those that have children)
    parent_ids: Set[str] = set()
    for element_id in all_ids:
        parts = element_id.split(".")
        # Add all prefixes as parent IDs
        for i in range(1, len(parts)):
            prefix = ".".join(parts[:i])
            parent_ids.add(prefix)

    # Leaf elements are those that are NOT parents (have no children)
    leaf_ids = all_ids - parent_ids

    # Build Element objects for leaf nodes
    elements: Dict[str, Element] = {}
    for element_id in leaf_ids:
        if element_id in all_entries:
            element_name, _description = all_entries[element_id]
            elements[element_id] = Element(
                element_id=element_id,
                element_name=element_name,
            )

    return elements


def load_scale_definitions(file_path: Optional[Path] = None) -> Dict[str, ScaleDefinition]:
    """
    Load scale definitions from job_scale_reference.txt or job_scale_def.csv.

    Parameters
    ----------
    file_path : Optional[Path]
        Path to scale definition file. If None, tries default locations.

    Returns
    -------
    Dict[str, ScaleDefinition]
        Dictionary mapping scale_id to ScaleDefinition objects.
    """
    if file_path is None:
        data_dir = get_data_dir()
        # Try CSV first, then TXT
        if (data_dir / "job_scale_def.csv").exists():
            file_path = data_dir / "job_scale_def.csv"
        else:
            file_path = data_dir / "job_scale_reference.txt"

    scale_defs: Dict[str, ScaleDefinition] = {}

    # Determine file format by extension
    is_csv = file_path.suffix.lower() == '.csv'
    delimiter = ',' if is_csv else '\t'

    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter=delimiter)
        next(reader)  # Skip header

        for row in reader:
            if len(row) < 4:
                continue

            scale_id = row[0].strip()
            scale_name = row[1].strip()
            min_str = row[2].strip()
            max_str = row[3].strip()

            # Parse min/max values
            try:
                min_value = float(min_str) if min_str else 0
            except ValueError:
                min_value = 0

            try:
                max_value = float(max_str) if max_str else 100
            except ValueError:
                max_value = 100

            # Determine scale type
            # Distribution scales: max=100, represent percentages across categories
            # Common distribution scales: CTP, CXP, FT, OJ, PT, RL, RW, RT
            is_distribution = (
                max_value == 100 and
                scale_id in ['CTP', 'CXP', 'FT', 'OJ', 'PT', 'RL', 'RW', 'RT']
            )

            scale_type = ScaleType.ORDINAL if is_distribution else ScaleType.INTERVAL

            scale_defs[scale_id] = ScaleDefinition(
                scale_id=scale_id,
                scale_name=scale_name,
                min_value=min_value,
                max_value=max_value,
                scale_type=scale_type
            )

    return scale_defs


# Global registries (initialized on first import)
_ORGANIZATION_REGISTRY: Optional[OrganizationRegistry] = None
_SCALE_DEFINITIONS: Optional[Dict[str, ScaleDefinition]] = None
_ELEMENTS: Optional[Dict[str, Element]] = None


def get_organization_registry() -> OrganizationRegistry:
    """Get or initialize the global OrganizationRegistry."""
    global _ORGANIZATION_REGISTRY
    if _ORGANIZATION_REGISTRY is None:
        _ORGANIZATION_REGISTRY = load_organization_registry()
    return _ORGANIZATION_REGISTRY


def get_scale_definitions() -> Dict[str, ScaleDefinition]:
    """Get or initialize the global scale definitions dictionary."""
    global _SCALE_DEFINITIONS
    if _SCALE_DEFINITIONS is None:
        _SCALE_DEFINITIONS = load_scale_definitions()
    return _SCALE_DEFINITIONS


def get_elements() -> Dict[str, Element]:
    """Get or initialize the global elements dictionary."""
    global _ELEMENTS
    if _ELEMENTS is None:
        _ELEMENTS = load_elements()
    return _ELEMENTS


def initialize_all() -> Tuple[OrganizationRegistry, Dict[str, ScaleDefinition], Dict[str, Element]]:
    """
    Initialize all registries and return them.

    Returns
    -------
    Tuple[OrganizationRegistry, Dict[str, ScaleDefinition], Dict[str, Element]]
        The organization registry, scale definitions, and elements.
    """
    return get_organization_registry(), get_scale_definitions(), get_elements()


# Auto-initialize on module import
try:
    initialize_all()
except FileNotFoundError:
    # If data files aren't available, skip initialization
    # This allows the module to be imported without data files for testing
    pass
