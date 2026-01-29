"""Domain package for CareerHQ.

This package contains domain entities, value objects, and service functions
for users, occupations, and their attributes.
"""

from .user_class import (
    User,
    Job,
    UserAttribute,
    UserAttributeTemplate,
    AttributeOrganizationNode,
    AttributeOrganizationRegistry,
    AttributeTemplateRegistry,
)

from .user_initialize import (
    get_user_attribute_templates,
    get_user_attribute_template,
    get_attribute_template_registry,
    get_attribute_organization_registry,
    get_leaf_attribute_templates,
    initialize_user_attributes,
)

from .user_service import (
    add_job_experience,
    update_user_attributes_from_job,
    update_attributes_with_element_mapping,
    update_attributes_without_element_mapping,
)

__all__ = [
    # User classes
    "User",
    "Job",
    "UserAttribute",
    "UserAttributeTemplate",
    "AttributeOrganizationNode",
    "AttributeOrganizationRegistry",
    "AttributeTemplateRegistry",
    # User initialization
    "get_user_attribute_templates",
    "get_user_attribute_template",
    "get_attribute_template_registry",
    "get_attribute_organization_registry",
    "get_leaf_attribute_templates",
    "initialize_user_attributes",
    # User service
    "add_job_experience",
    "update_user_attributes_from_job",
    "update_attributes_with_element_mapping",
    "update_attributes_without_element_mapping",
]
