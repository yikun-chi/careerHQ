"""User domain classes for CareerHQ.

This module defines the User model and related classes for representing
user profiles with attributes (self-assessments) and job history.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple
import copy

if TYPE_CHECKING:
    from .occupation_class import Element, Occupation


@dataclass(frozen=True)
class AttributeOrganizationNode:
    """Semantic meaning of a hierarchical attribute organization code.

    Similar to OrganizationNode in occupation_class, this represents
    a category in the attribute hierarchy.

    Attributes:
        org_id: The organization ID (e.g., "1.A", "1.A.1")
        name: Human-readable name (e.g., "Abilities", "Cognitive Abilities")
        description: Optional description of this category
    """

    org_id: str
    name: str
    description: Optional[str] = None


@dataclass
class AttributeOrganizationRegistry:
    """Maps attribute organization IDs to semantic meaning.

    Similar to OrganizationRegistry in occupation_class.

    Attributes:
        nodes: Dictionary mapping org_id to AttributeOrganizationNode
    """

    nodes: Dict[str, AttributeOrganizationNode] = field(default_factory=dict)

    def get(self, org_id: str) -> AttributeOrganizationNode:
        """Get an organization node by ID.

        Args:
            org_id: The organization ID to look up

        Returns:
            The AttributeOrganizationNode for the given ID

        Raises:
            KeyError: If the org_id is not found
        """
        if org_id not in self.nodes:
            raise KeyError(f"Unknown attribute organization id: {org_id}")
        return self.nodes[org_id]

    def register(self, node: AttributeOrganizationNode) -> None:
        """Register an organization node.

        Args:
            node: The AttributeOrganizationNode to register
        """
        self.nodes[node.org_id] = node


@dataclass
class UserAttribute:
    """A user's self-assessment that can optionally map to an O*NET Element.

    Attributes:
        attribute_id: Unique identifier (e.g., "1.A.1.a.1", "1.N.2.a")
        attribute_name: Human-readable name (e.g., "Oral Comprehension", "INTJ")
        mapping_element_id: O*NET element ID if mapped (from Element ID column)
        element_name: O*NET element name if mapped (from Element Name column)
        description: Description of the attribute
        capability: Self-assessed capability (0-100, None if not set)
        preference: Self-assessed preference (0-100, None if not set)
        binary: Binary flag (True/False/None)
        organizations: Derived taxonomy prefixes for parent categories
    """

    attribute_id: str
    attribute_name: str
    mapping_element_id: Optional[str] = None
    element_name: Optional[str] = None
    description: Optional[str] = None
    capability: Optional[float] = None
    preference: Optional[float] = None
    binary: Optional[bool] = None

    # Derived taxonomy prefixes: ("1", "1.A", "1.A.1", "1.A.1.a")
    organizations: Tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        """Validate the attribute and compute organizations after initialization."""
        self.organizations = self._compute_organizations(self.attribute_id)
        self.validate()

    @staticmethod
    def _compute_organizations(attribute_id: str) -> Tuple[str, ...]:
        """Split a dotted hierarchy and return all proper prefixes.

        Example: "1.A.1.a.1" -> ("1", "1.A", "1.A.1", "1.A.1.a")

        Args:
            attribute_id: The full attribute ID

        Returns:
            Tuple of all parent organization prefixes (excluding the full ID)
        """
        parts = [p for p in attribute_id.split(".") if p]  # guard empty segments
        if len(parts) <= 1:
            return tuple()
        prefixes = [".".join(parts[:i]) for i in range(1, len(parts))]  # exclude full id
        return tuple(prefixes)

    def validate(self) -> None:
        """Validate that capability and preference are in range [0, 100] when set.

        Raises:
            ValueError: If capability or preference is outside the valid range.
        """
        if self.capability is not None:
            if not isinstance(self.capability, (int, float)) or not (0 <= self.capability <= 100):
                raise ValueError(
                    f"capability must be a number between 0 and 100, got {self.capability}"
                )
        if self.preference is not None:
            if not isinstance(self.preference, (int, float)) or not (0 <= self.preference <= 100):
                raise ValueError(
                    f"preference must be a number between 0 and 100, got {self.preference}"
                )


@dataclass(frozen=True)
class UserAttributeTemplate:
    """Blueprint for creating UserAttribute instances.

    This is an immutable template that defines the structure of a user attribute
    without any user-specific values. Similar to ElementTemplate in occupation_class.

    Attributes:
        attribute_id: Unique identifier
        attribute_name: Human-readable name
        mapping_element_id: O*NET element ID if mapped
        element_name: O*NET element name if mapped
        description: Description of the attribute
        organizations: Derived taxonomy prefixes for parent categories
    """

    attribute_id: str
    attribute_name: str
    mapping_element_id: Optional[str] = None
    element_name: Optional[str] = None
    description: Optional[str] = None

    @property
    def organizations(self) -> Tuple[str, ...]:
        """Compute parent organization prefixes from attribute_id.

        Returns:
            Tuple of all parent organization prefixes (excluding the full ID)
        """
        return UserAttribute._compute_organizations(self.attribute_id)

    def is_leaf(self) -> bool:
        """Check if this attribute is a leaf node (has no children).

        This is determined by checking if any other attribute_id starts with
        this attribute_id as a prefix. Since templates don't have access to
        the full registry, this method should be called from the registry level.

        For now, returns True by default - actual leaf detection should be done
        at the registry level.
        """
        # Leaf detection requires knowledge of all attributes in the registry
        # This is a placeholder - actual implementation at registry level
        return True

    def instantiate(self) -> UserAttribute:
        """Create a mutable UserAttribute instance from this template.

        Returns:
            A new UserAttribute with the same metadata but None values.
        """
        return UserAttribute(
            attribute_id=self.attribute_id,
            attribute_name=self.attribute_name,
            mapping_element_id=self.mapping_element_id,
            element_name=self.element_name,
            description=self.description,
            capability=None,
            preference=None,
            binary=None,
        )


@dataclass
class Job:
    """An occupation the user has held, with employment-specific details.

    Jobs reference O*NET occupations and include additional employment
    information like salary, company, and duration.

    Attributes:
        occupation_id: O*NET occupation code (e.g., "11-1011.00")
        occupation_name: O*NET occupation title (from initialized occupations)
        job_title: User's actual job title (what they call it)
        company_name: Name of the company/employer
        salary: Salary (None if not provided)
        start_date: Start date in ISO format (optional)
        end_date: End date in ISO format (optional, None if current job)
        duration_months: Duration in months (for flexibility)
        elements: Element data copied from Occupation for skill matching
    """

    occupation_id: str
    occupation_name: str
    job_title: str
    company_name: str
    salary: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = None
    elements: Dict[str, "Element"] = field(default_factory=dict)

    @classmethod
    def from_occupation(
        cls,
        occupation: "Occupation",
        job_title: str,
        company_name: str,
        salary: Optional[float] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        duration_months: Optional[int] = None,
    ) -> "Job":
        """Create a Job from an existing Occupation.

        This factory method copies the element data from the occupation
        for skill matching purposes.

        Args:
            occupation: The O*NET occupation to base this job on
            job_title: User's actual job title
            company_name: Name of the company/employer
            salary: Salary (optional)
            start_date: Start date in ISO format (optional)
            end_date: End date in ISO format (optional)
            duration_months: Duration in months (optional)

        Returns:
            A new Job instance with elements copied from the occupation.
        """
        # Deep copy elements to avoid sharing mutable state
        elements_copy = copy.deepcopy(occupation.elements)

        return cls(
            occupation_id=occupation.occupation_id,
            occupation_name=occupation.occupation_name,
            job_title=job_title,
            company_name=company_name,
            salary=salary,
            start_date=start_date,
            end_date=end_date,
            duration_months=duration_months,
            elements=elements_copy,
        )


@dataclass
class User:
    """The main user profile containing attributes and job history.

    Attributes:
        user_id: Unique user identifier
        user_name: Display name (optional)
        attributes: User attributes keyed by attribute_id
        jobs: Ordered list of jobs (most recent first)
    """

    user_id: str
    user_name: Optional[str] = None
    attributes: Dict[str, UserAttribute] = field(default_factory=dict)
    jobs: List[Job] = field(default_factory=list)

    def add_attribute(self, attr: UserAttribute) -> None:
        """Add or update a user attribute.

        Args:
            attr: The UserAttribute to add or update
        """
        self.attributes[attr.attribute_id] = attr

    def get_attribute(self, attribute_id: str) -> Optional[UserAttribute]:
        """Retrieve an attribute by ID.

        Args:
            attribute_id: The ID of the attribute to retrieve

        Returns:
            The UserAttribute if found, None otherwise.
        """
        return self.attributes.get(attribute_id)

    def add_job(self, job: Job) -> None:
        """Add a job to the user's job history.

        Jobs are inserted at the beginning of the list (most recent first).

        Args:
            job: The Job to add
        """
        self.jobs.insert(0, job)

    def get_jobs(self) -> List[Job]:
        """Get all jobs in the user's history.

        Returns:
            List of jobs ordered by most recent first.
        """
        return self.jobs

    def get_current_job(self) -> Optional[Job]:
        """Get the user's current job (most recent with no end date).

        Returns:
            The current Job if one exists, None otherwise.
        """
        for job in self.jobs:
            if job.end_date is None:
                return job
        return None


@dataclass
class AttributeTemplateRegistry:
    """Registry of all available attribute templates.

    Similar to ElementTemplateRegistry in occupation_class, this provides
    methods to register, retrieve, and query attribute templates.

    Attributes:
        templates: Dictionary mapping attribute_id to UserAttributeTemplate
    """

    templates: Dict[str, UserAttributeTemplate] = field(default_factory=dict)

    def register(self, template: UserAttributeTemplate) -> None:
        """Register an attribute template.

        Args:
            template: The UserAttributeTemplate to register

        Raises:
            ValueError: If a template with the same ID already exists
        """
        if template.attribute_id in self.templates:
            raise ValueError(
                f"AttributeTemplate '{template.attribute_id}' already exists"
            )
        self.templates[template.attribute_id] = template

    def get(self, attribute_id: str) -> Optional[UserAttributeTemplate]:
        """Get a template by ID.

        Args:
            attribute_id: The attribute ID to look up

        Returns:
            The UserAttributeTemplate if found, None otherwise
        """
        return self.templates.get(attribute_id)

    def create_attribute(self, attribute_id: str) -> UserAttribute:
        """Instantiate a concrete UserAttribute from its template.

        Args:
            attribute_id: The attribute ID to instantiate

        Returns:
            A new UserAttribute instance

        Raises:
            KeyError: If the attribute_id is not found
        """
        if attribute_id not in self.templates:
            raise KeyError(f"Unknown attribute template: {attribute_id}")
        return self.templates[attribute_id].instantiate()

    def is_leaf(self, attribute_id: str) -> bool:
        """Check if an attribute is a leaf node (has no children).

        A leaf node is one where no other attribute_id starts with this
        attribute_id followed by a dot.

        Args:
            attribute_id: The attribute ID to check

        Returns:
            True if this is a leaf node, False if it has children
        """
        prefix = attribute_id + "."
        for other_id in self.templates:
            if other_id.startswith(prefix):
                return False
        return True

    def get_leaf_templates(self) -> Dict[str, UserAttributeTemplate]:
        """Get all leaf attribute templates (those with no children).

        Returns:
            Dictionary mapping attribute_id to UserAttributeTemplate for leaf nodes only
        """
        return {
            attr_id: template
            for attr_id, template in self.templates.items()
            if self.is_leaf(attr_id)
        }

    def get_children(self, parent_id: str) -> Dict[str, UserAttributeTemplate]:
        """Get all direct children of a parent attribute.

        Args:
            parent_id: The parent attribute ID

        Returns:
            Dictionary of direct child templates
        """
        prefix = parent_id + "."
        children = {}
        for attr_id, template in self.templates.items():
            if attr_id.startswith(prefix):
                # Check if it's a direct child (no additional dots after the prefix)
                remainder = attr_id[len(prefix):]
                if "." not in remainder:
                    children[attr_id] = template
        return children

    def get_organization_nodes(self) -> Dict[str, AttributeOrganizationNode]:
        """Build organization nodes from non-leaf templates.

        Returns:
            Dictionary mapping org_id to AttributeOrganizationNode for all parent nodes
        """
        nodes = {}
        for attr_id, template in self.templates.items():
            if not self.is_leaf(attr_id):
                nodes[attr_id] = AttributeOrganizationNode(
                    org_id=attr_id,
                    name=template.attribute_name,
                    description=template.description,
                )
        return nodes
