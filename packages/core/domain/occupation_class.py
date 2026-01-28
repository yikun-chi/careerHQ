from dataclasses import dataclass, field
from typing import Dict, Optional, Union, Tuple
from enum import Enum

Number = Union[int, float]

class ScaleType(Enum):
    ORDINAL = "ordinal"
    INTERVAL = "interval"


@dataclass
class OrganizationRegistry:
    """
    Maps organization IDs (e.g. '2.A') to semantic meaning.
    """
    nodes: Dict[str, "OrganizationNode"]

    def get(self, org_id: str) -> "OrganizationNode":
        if org_id not in self.nodes:
            raise KeyError(f"Unknown organization id: {org_id}")
        return self.nodes[org_id]


@dataclass(frozen=True)
class OrganizationNode:
    """
    Semantic meaning of a hierarchical organization code.
    """
    org_id: str           # e.g. "2.A"
    name: str             # e.g. "Technical Skills"
    description: Optional[str] = None


@dataclass(frozen=True)
class ScaleDefinition:
    scale_id: str
    scale_name: str
    min_value: Number
    max_value: Number
    scale_type: ScaleType

@dataclass(frozen=True)
class OrdinalSemantics:
    """
    Element-scoped meaning of each ordinal category.
    Example: {1: "Low", 2: "Medium", 3: "High"}
    """
    categories: Dict[int, str]

@dataclass(frozen=True)
class IntervalSemantics:
    """
    Element-scoped meaning of the numeric value.
    Example: "percentage (0–100)" or "mean rating across items".
    """
    meaning: str

@dataclass
class ElementScale:
    """
    One (Element × Scale) measurement.
    Scale metadata is global (scale_def); semantics can be element-scoped (semantics).
    """
    scale_def: ScaleDefinition
    value: Optional[Number] = None

    # Optional distribution representation (if you keep it)
    distribution: Optional[Dict[int, float]] = None

    # Element-scoped semantics (depends on scale_type)
    ordinal_semantics: Optional[OrdinalSemantics] = None
    interval_semantics: Optional[IntervalSemantics] = None

    @property
    def scale_id(self) -> str:
        return self.scale_def.scale_id

    @property
    def scale_name(self) -> str:
        return self.scale_def.scale_name

    def validate(self) -> None:
        st = self.scale_def.scale_type

        if st == ScaleType.ORDINAL:
            if self.ordinal_semantics is None:
                raise ValueError("ORDINAL scale requires ordinal_semantics with category meanings.")
            if self.interval_semantics is not None:
                raise ValueError("ORDINAL scale should not have interval_semantics.")
            # Optional: enforce integer category keys and value consistency
            if self.value is not None and int(self.value) != self.value:
                raise ValueError("ORDINAL value must be an integer category.")
            if self.value is not None and int(self.value) not in self.ordinal_semantics.categories:
                raise ValueError("ORDINAL value not found in ordinal_semantics.categories.")

        elif st == ScaleType.INTERVAL:
            if self.interval_semantics is None:
                raise ValueError("INTERVAL scale requires interval_semantics describing meaning/units.")
            if self.ordinal_semantics is not None:
                raise ValueError("INTERVAL scale should not have ordinal_semantics.")


@dataclass
class Element:
    element_id: str
    element_name: str

    # Derived taxonomy prefixes: ("2", "2.A", "2.A.c", "2.A.c.3")
    organizations: Tuple[str, ...] = field(init=False)

    scales: Dict[str, "ElementScale"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.organizations = self._compute_organizations(self.element_id)

    @staticmethod
    def _compute_organizations(element_id: str) -> Tuple[str, ...]:
        """
        Split a dotted hierarchy and return all proper prefixes.
        Example: "2.A.c.3.1" -> ("2", "2.A", "2.A.c", "2.A.c.3")
        """
        parts = [p for p in element_id.split(".") if p]  # guard empty segments
        if len(parts) <= 1:
            return tuple()
        prefixes = [".".join(parts[:i]) for i in range(1, len(parts))]  # exclude full id
        return tuple(prefixes)

    def upsert_scale(self, es: "ElementScale") -> None:
        self.scales[es.scale_id] = es

    def get_scale(self, scale_id: str) -> Optional["ElementScale"]:
        return self.scales.get(scale_id)
    


@dataclass(frozen=True)
class ElementTemplate:
    """
    Canonical definition of an Element and its scales,
    without any observed values.
    """
    element_id: str
    element_name: str
    scales: Dict[str, "ElementScale"]  # values must be None

    def instantiate(self) -> "Element":
        """
        Create a mutable Element instance with empty values.
        """
        return Element(
            element_id=self.element_id,
            element_name=self.element_name,
            scales={
                scale_id: ElementScale(
                    scale_def=es.scale_def,
                    value=None,
                    distribution=None,
                    ordinal_semantics=es.ordinal_semantics,
                    interval_semantics=es.interval_semantics,
                )
                for scale_id, es in self.scales.items()
            },
        )

@dataclass
class ElementTemplateRegistry:
    """
    Registry of all available element templates.
    """
    templates: Dict[str, ElementTemplate] = field(default_factory=dict)

    def register(self, template: ElementTemplate) -> None:
        if template.element_id in self.templates:
            raise ValueError(f"ElementTemplate '{template.element_id}' already exists")
        self.templates[template.element_id] = template

    def create_element(self, element_id: str) -> "Element":
        """
        Instantiate a concrete Element from its template.
        """
        if element_id not in self.templates:
            raise KeyError(f"Unknown element template: {element_id}")
        return self.templates[element_id].instantiate()



@dataclass(frozen=True)
class OccupationSchema:
    """
    Canonical element set shared by all occupations.
    """
    elements: Dict[str, "ElementTemplate"]

    def instantiate_elements(self) -> Dict[str, "Element"]:
        return {eid: tmpl.instantiate() for eid, tmpl in self.elements.items()}
    


@dataclass
class Occupation:
    """
    A concrete occupation profile. All occupations share the same element structure;
    they differ in the filled-in values.
    """
    occupation_id: str
    occupation_name: str
    elements: Dict[str, "Element"] = field(default_factory=dict)

    @classmethod
    def from_schema(
        cls,
        *,
        occupation_id: str,
        occupation_name: str,
        schema: "OccupationSchema",
    ) -> "Occupation":
        """
        Create an Occupation with the canonical element set. All values start as None.
        """
        return cls(
            occupation_id=occupation_id,
            occupation_name=occupation_name,
            elements=schema.instantiate_elements(),
        )

    def get_element(self, element_id: str) -> Optional["Element"]:
        return self.elements.get(element_id)

    def upsert_scale_value(
        self,
        *,
        element_id: str,
        scale_id: str,
        value: int | float | None,
    ) -> None:
        el = self.elements.get(element_id)
        if el is None:
            raise KeyError(f"Unknown element_id in occupation '{self.occupation_id}': {element_id}")

        es = el.get_scale(scale_id)
        if es is None:
            raise KeyError(
                f"Unknown scale_id '{scale_id}' for element '{element_id}' "
                f"in occupation '{self.occupation_id}'"
            )

        es.value = value
        if hasattr(es, "validate"):
            es.validate()
    