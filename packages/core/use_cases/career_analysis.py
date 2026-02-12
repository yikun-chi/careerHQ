"""Career analysis: match a user's attribute profile against O*NET occupations.

Pure data comparison — no LLM needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from packages.core.domain.occupation_class import Occupation
from packages.core.domain.user_class import User


@dataclass
class CareerMatch:
    occupation_id: str
    occupation_name: str
    match_count: int          # categories matched (out of total_categories)
    total_categories: int     # categories the user had enough data for
    matched_categories: List[str] = field(default_factory=list)


# (label, user_prefix, onet_prefix, scale_id)
# For Interests & Work Values the scale varies by sub-prefix, handled specially.
_CATEGORY_CONFIGS: List[Tuple[str, str, str, str]] = [
    ("Abilities",               "1.A", "1.A", "IM"),
    ("Work Styles",             "1.D", "1.D", "WI"),
    ("Basic Skills",            "3.A", "2.A", "IM"),
    ("Cross-Functional Skills", "3.B", "2.B", "IM"),
    ("Knowledge",               "3.C", "2.C", "IM"),
    ("Interests & Work Values", "4.B", "1.B", ""),   # special handling
]

_MIN_SCORED = 2   # need at least 2 scored attributes to consider a category
_TOP_N = 3        # compare top 3 in each category
_MIN_OVERLAP = 2  # need >= 2 overlapping elements for a category match


def _get_user_top3(user: User, prefix: str) -> List[str]:
    """Return mapping_element_ids for the user's top 3 attributes in a category."""
    leaf_prefix = prefix + "."
    scored = []
    for attr_id, attr in user.attributes.items():
        if attr_id.startswith(leaf_prefix) and attr.capability is not None and attr.capability > 0:
            scored.append((attr.capability, attr.mapping_element_id))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eid for _, eid in scored[:_TOP_N] if eid is not None]


def _get_occ_top3(occupation: Occupation, onet_prefix: str, scale_id: str) -> List[str]:
    """Return the top 3 element_ids for an occupation in a category."""
    elem_prefix = onet_prefix + "."
    scored = []
    for eid, element in occupation.elements.items():
        if not eid.startswith(elem_prefix):
            continue
        scale = element.get_scale(scale_id)
        if scale is not None and scale.value is not None:
            scored.append((scale.value, eid))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eid for _, eid in scored[:_TOP_N]]


def _get_occ_top3_interests(occupation: Occupation) -> List[str]:
    """Return the top 3 element_ids for the combined Interests & Work Values category.

    Interests (1.B.1.*) use OI scale (1-7).
    Work Values (1.B.2.*) use EX scale (1-7).
    Both are on the same numeric range, so they can be ranked together.
    """
    scored = []
    for eid, element in occupation.elements.items():
        if eid.startswith("1.B.1."):
            scale = element.get_scale("OI")
            if scale is not None and scale.value is not None:
                scored.append((scale.value, eid))
        elif eid.startswith("1.B.2."):
            scale = element.get_scale("EX")
            if scale is not None and scale.value is not None:
                scored.append((scale.value, eid))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eid for _, eid in scored[:_TOP_N]]


def find_matching_occupations(
    user: User,
    occupations: Dict[str, Occupation],
) -> List[CareerMatch]:
    """Find O*NET occupations matching the user's attribute profile.

    For each of 6 attribute categories, compares the user's top 3 attributes
    (by capability) against each occupation's top 3 elements (by scale value).
    Occupations matching >= 2 of 3 in a category count as a category match.
    Results are ranked by number of matching categories.
    """

    # --- Build user's top-3 sets per category ---
    user_tops: List[Tuple[str, set]] = []  # (label, set of mapping_element_ids)
    for label, user_prefix, _onet_prefix, _scale_id in _CATEGORY_CONFIGS:
        top_eids = _get_user_top3(user, user_prefix)
        if len(top_eids) >= _MIN_SCORED:
            user_tops.append((label, set(top_eids)))

    if not user_tops:
        return []

    total_categories = len(user_tops)

    # --- Score each occupation ---
    results: List[CareerMatch] = []
    for occ_id, occupation in occupations.items():
        matched_labels: List[str] = []

        for label, user_set in user_tops:
            # Find the config for this label to get onet_prefix / scale_id
            cfg = next(c for c in _CATEGORY_CONFIGS if c[0] == label)
            _label, _user_prefix, onet_prefix, scale_id = cfg

            if label == "Interests & Work Values":
                occ_top = _get_occ_top3_interests(occupation)
            else:
                occ_top = _get_occ_top3(occupation, onet_prefix, scale_id)

            overlap = len(user_set & set(occ_top))
            if overlap >= _MIN_OVERLAP:
                matched_labels.append(label)

        if matched_labels:
            results.append(CareerMatch(
                occupation_id=occ_id,
                occupation_name=occupation.occupation_name,
                match_count=len(matched_labels),
                total_categories=total_categories,
                matched_categories=matched_labels,
            ))

    results.sort(key=lambda m: m.match_count, reverse=True)
    return results[:15]
