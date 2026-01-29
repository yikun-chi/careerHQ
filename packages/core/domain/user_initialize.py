"""
user_initialize.py
==================

This module initializes user attribute templates from the user_attribute.csv file.
It provides functions to load and access user attribute definitions.
"""

import csv
from typing import Dict, Optional
from pathlib import Path

from .user_class import (
    UserAttributeTemplate,
    AttributeTemplateRegistry,
    AttributeOrganizationNode,
    AttributeOrganizationRegistry,
)


def get_data_dir() -> Path:
    """Get the path to the data directory."""
    module_dir = Path(__file__).parent
    core_dir = module_dir.parent
    return core_dir / "data"


def load_user_attribute_templates(
    file_path: Optional[Path] = None,
) -> Dict[str, UserAttributeTemplate]:
    """
    Load user attribute templates from user_attribute.csv.

    The CSV file has columns:
    - Attribute ID: Unique identifier (e.g., "1.A.1.a.1", "1.N.2.a")
    - Attribute Name: Human-readable name
    - Element ID: O*NET element ID if mapped (may be empty)
    - Element Name: O*NET element name if mapped (may be empty)
    - Description: Description of the attribute

    Parameters
    ----------
    file_path : Optional[Path]
        Path to user_attribute.csv. If None, uses default location.

    Returns
    -------
    Dict[str, UserAttributeTemplate]
        Dictionary mapping attribute_id to UserAttributeTemplate objects.
    """
    if file_path is None:
        file_path = get_data_dir() / "user_attribute.csv"

    templates: Dict[str, UserAttributeTemplate] = {}

    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=",")
        header = next(reader)  # Skip header

        # Expected columns: Attribute ID, Attribute Name, Element ID, Element Name, Description
        for row in reader:
            if len(row) < 2:
                continue

            attribute_id = row[0].strip() if len(row) > 0 else ""
            attribute_name = row[1].strip() if len(row) > 1 else ""
            element_id = row[2].strip() if len(row) > 2 else ""
            element_name = row[3].strip() if len(row) > 3 else ""
            description = row[4].strip() if len(row) > 4 else ""

            if not attribute_id or not attribute_name:
                continue

            # Convert empty strings to None
            mapping_element_id = element_id if element_id else None
            elem_name = element_name if element_name else None
            desc = description if description else None

            templates[attribute_id] = UserAttributeTemplate(
                attribute_id=attribute_id,
                attribute_name=attribute_name,
                mapping_element_id=mapping_element_id,
                element_name=elem_name,
                description=desc,
            )

    return templates


# Global registries (initialized lazily)
_USER_ATTRIBUTE_TEMPLATES: Optional[Dict[str, UserAttributeTemplate]] = None
_ATTRIBUTE_TEMPLATE_REGISTRY: Optional[AttributeTemplateRegistry] = None
_ATTRIBUTE_ORGANIZATION_REGISTRY: Optional[AttributeOrganizationRegistry] = None


def get_user_attribute_templates() -> Dict[str, UserAttributeTemplate]:
    """Get or initialize the global user attribute templates dictionary.

    Returns
    -------
    Dict[str, UserAttributeTemplate]
        Dictionary mapping attribute_id to UserAttributeTemplate objects.
    """
    global _USER_ATTRIBUTE_TEMPLATES
    if _USER_ATTRIBUTE_TEMPLATES is None:
        _USER_ATTRIBUTE_TEMPLATES = load_user_attribute_templates()
    return _USER_ATTRIBUTE_TEMPLATES


def get_attribute_template_registry() -> AttributeTemplateRegistry:
    """Get or initialize the global attribute template registry.

    Returns
    -------
    AttributeTemplateRegistry
        Registry containing all attribute templates with helper methods.
    """
    global _ATTRIBUTE_TEMPLATE_REGISTRY
    if _ATTRIBUTE_TEMPLATE_REGISTRY is None:
        templates = get_user_attribute_templates()
        _ATTRIBUTE_TEMPLATE_REGISTRY = AttributeTemplateRegistry(templates=templates)
    return _ATTRIBUTE_TEMPLATE_REGISTRY


def get_attribute_organization_registry() -> AttributeOrganizationRegistry:
    """Get or initialize the global attribute organization registry.

    This registry contains organization nodes for all non-leaf attributes
    (i.e., category/parent nodes in the hierarchy).

    Returns
    -------
    AttributeOrganizationRegistry
        Registry mapping org_id to AttributeOrganizationNode.
    """
    global _ATTRIBUTE_ORGANIZATION_REGISTRY
    if _ATTRIBUTE_ORGANIZATION_REGISTRY is None:
        registry = get_attribute_template_registry()
        org_nodes = registry.get_organization_nodes()
        _ATTRIBUTE_ORGANIZATION_REGISTRY = AttributeOrganizationRegistry(nodes=org_nodes)
    return _ATTRIBUTE_ORGANIZATION_REGISTRY


def get_leaf_attribute_templates() -> Dict[str, UserAttributeTemplate]:
    """Get only leaf attribute templates (attributes with no children).

    Returns
    -------
    Dict[str, UserAttributeTemplate]
        Dictionary mapping attribute_id to UserAttributeTemplate for leaf nodes only.
    """
    registry = get_attribute_template_registry()
    return registry.get_leaf_templates()


def get_user_attribute_template(attribute_id: str) -> Optional[UserAttributeTemplate]:
    """Get a specific user attribute template by ID.

    Parameters
    ----------
    attribute_id : str
        The attribute ID to look up.

    Returns
    -------
    Optional[UserAttributeTemplate]
        The template if found, None otherwise.
    """
    templates = get_user_attribute_templates()
    return templates.get(attribute_id)


def initialize_user_attributes() -> Dict[str, UserAttributeTemplate]:
    """Initialize and return user attribute templates.

    This is a convenience function that ensures the templates are loaded
    and returns them.

    Returns
    -------
    Dict[str, UserAttributeTemplate]
        Dictionary mapping attribute_id to UserAttributeTemplate objects.
    """
    return get_user_attribute_templates()
