"""
job_parser.py
================

This module provides classes and functions to parse the O*NET content model
data files and build a Python representation of occupations.  Each
occupation (job) includes its core descriptive information (code,
title, description, job zone), alternate titles, tasks and all
elements defined in the O*NET model (e.g. abilities, skills,
knowledge, work activities, work context, work styles, work values,
interests, and education/training/experience requirements).

Elements are represented by a hierarchical data structure.  At the
lowest level a ``Scale`` stores the scale identifier, human‐readable
scale name, numeric value, a computed interpretation and (optionally)
a distribution across categorical responses.  An ``Element`` groups
multiple scales together under a common element identifier and name.
``Task`` objects represent task statements along with their ratings.
Finally, a ``Job`` aggregates all of these pieces for a single
occupation.

The parser reads the supplied tab‑delimited text files exported from
O*NET and builds these objects.  It attempts to interpret numeric
values into human readable meanings using scale definitions from
``Scales Reference.txt``, anchor points from ``Level Scale
Anchors.txt`` for ``LV`` (level) scales, and category descriptions from
the various "…Categories.txt" files.  For distribution‐based scales
such as ``RL`` (required level of education) and ``CXP`` (work
context categories) it selects the category with the highest
percentage and uses the associated description as the interpretation.

Note that not every scale has an official set of anchors.  For
scales lacking published anchors the parser applies simple heuristic
interpretations based on the value and the allowed range from the
scales reference.  These heuristics are deliberately conservative and
can be adjusted as needed.

Example
-------
To build the full job repertoire from an unpacked O*NET data directory
and save it to a JSON file for later use::

    from job_parser import build_job_repertoire, save_jobs_json

    data_dir = "/path/to/db_30_1_text_unzipped/db_30_1_text"
    jobs = build_job_repertoire(data_dir)
    save_jobs_json(jobs, "/tmp/onet_jobs.json")

Once saved you can load the JSON back into memory without needing to
reparse the raw text files::

    from job_parser import load_jobs_json

    jobs = load_jobs_json("/tmp/onet_jobs.json")

See ``if __name__ == '__main__'`` at the bottom of this file for a
simple command‑line interface.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any, Iterable

###############################################################################
# Data structures
###############################################################################

@dataclass
class Scale:
    """Representation of a single scale value for an element.

    Parameters
    ----------
    scale_id: str
        The identifier of the scale (e.g. 'IM', 'LV', 'CXP').
    scale_name: str
        Human readable name of the scale (e.g. 'Importance', 'Level').
    value: Optional[float]
        The computed numeric value for the scale.  For distribution
        scales this holds the selected category (the one with the
        highest proportion).  For numeric scales it holds the mean
        value provided by O*NET.
    interpretation: Optional[str]
        A human readable interpretation of the value.  Where official
        anchors exist this uses them; otherwise simple heuristics are
        applied.  For distribution scales this is the category
        description.
    distribution: Optional[Dict[int, float]]
        When the scale is based on a distribution across categories,
        this holds the full distribution mapping category numbers to
        percentages.  For numeric scales this remains ``None``.
    """

    scale_id: str
    scale_name: str
    value: Optional[float]
    interpretation: Optional[str]
    distribution: Optional[Dict[int, float]] = None

    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover - simple wrapper
        return asdict(self)


@dataclass
class Element:
    """Representation of an O*NET element aggregating multiple scales."""

    element_id: str
    element_name: str
    scales: Dict[str, Scale] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover - simple wrapper
        return {
            "element_id": self.element_id,
            "element_name": self.element_name,
            "scales": {k: v.to_dict() for k, v in self.scales.items()},
        }


@dataclass
class Task:
    """Representation of a task statement and its ratings."""

    task_id: str
    description: str
    task_type: str
    scales: Dict[str, Scale] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover
        return {
            "task_id": self.task_id,
            "description": self.description,
            "task_type": self.task_type,
            "scales": {k: v.to_dict() for k, v in self.scales.items()},
        }


@dataclass
class Job:
    """Representation of an occupation (job) with its detailed profile."""

    code: str
    title: str
    description: str
    job_zone: Optional[int] = None
    alternate_titles: List[str] = field(default_factory=list)
    elements: Dict[str, Element] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:  # pragma: no cover
        return {
            "code": self.code,
            "title": self.title,
            "description": self.description,
            "job_zone": self.job_zone,
            "alternate_titles": list(self.alternate_titles),
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
            "tasks": {k: v.to_dict() for k, v in self.tasks.items()},
        }


###############################################################################
# Helper functions for loading reference data
###############################################################################

def _read_tsv_rows(path: str) -> Iterable[List[str]]:
    """Yield rows from a tab‑separated file, skipping empty lines.

    Parameters
    ----------
    path: str
        Path to the TSV file.
    """
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            # skip completely empty rows
            if not row or all(not c.strip() for c in row):
                continue
            yield row


def load_scales_reference(path: str) -> Dict[str, Dict[str, Any]]:
    """Load scale definitions from ``Scales Reference.txt``.

    Returns a dictionary keyed by scale ID.  Each entry contains the
    scale name, minimum, and maximum numeric values.  Missing values are
    represented as ``None``.
    """
    scales: Dict[str, Dict[str, Any]] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        if len(row) < 4:
            continue
        scale_id, scale_name, minimum, maximum = row[:4]
        try:
            min_val: Optional[float] = float(minimum) if minimum else None
        except ValueError:
            min_val = None
        try:
            max_val: Optional[float] = float(maximum) if maximum else None
        except ValueError:
            max_val = None
        scales[scale_id] = {
            "name": scale_name,
            "min": min_val,
            "max": max_val,
        }
    return scales


def load_level_anchors(path: str) -> Dict[str, Dict[str, Dict[int, str]]]:
    """Load anchor descriptions for level scales (LV).

    The returned dictionary is keyed by element ID and then by scale
    identifier ('LV') and then by integer anchor value.  Values are
    descriptive strings.
    """
    anchors: Dict[str, Dict[str, Dict[int, str]]] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        # expected columns: element_id, element_name, scale_id, anchor_value, anchor_description
        if len(row) < 5:
            continue
        element_id = row[0].strip()
        scale_id = row[2].strip()
        value_str = row[3].strip()
        anchor_desc = row[4].strip()
        try:
            value_int = int(float(value_str))
        except ValueError:
            continue
        anchors.setdefault(element_id, {}).setdefault(scale_id, {})[value_int] = anchor_desc
    return anchors


def load_education_training_categories(path: str) -> Dict[Tuple[str, int], str]:
    """Load category descriptions for education, training and experience.

    Returns a dictionary keyed by (element_id, category_number) mapping to
    category description.  The scale ID is not included in the key as
    each element has a single scale in this file.  For example,
    element '2.D.1' with category 6 maps to 'Bachelor's Degree'.
    """
    categories: Dict[Tuple[str, int], str] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        # columns: Element ID, Element Name, Scale ID, Category, Category Description
        if len(row) < 5:
            continue
        element_id = row[0].strip()
        category_str = row[3].strip()
        desc = row[4].strip()
        try:
            category = int(category_str)
        except ValueError:
            continue
        categories[(element_id, category)] = desc
    return categories


def load_work_context_categories(path: str) -> Dict[Tuple[str, int], str]:
    """Load category descriptions for work context (CXP) scale.

    Returns a dictionary keyed by (element_id, category_number) mapping
    to category description.
    """
    categories: Dict[Tuple[str, int], str] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        # columns: Element ID, Element Name, Scale ID, Category, Category Description
        if len(row) < 5:
            continue
        element_id = row[0].strip()
        category_str = row[3].strip()
        desc = row[4].strip()
        try:
            category = int(category_str)
        except ValueError:
            continue
        categories[(element_id, category)] = desc
    return categories


def load_task_categories(path: str) -> Dict[int, str]:
    """Load category descriptions for task frequency categories (FT).

    Returns a dictionary keyed by category number mapping to description.
    """
    categories: Dict[int, str] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        # columns: Scale ID, Category, Category Description
        if len(row) < 3:
            continue
        scale_id = row[0].strip()
        if scale_id != 'FT':
            continue
        category_str = row[1].strip()
        desc = row[2].strip()
        try:
            category = int(category_str)
        except ValueError:
            continue
        categories[category] = desc
    return categories


###############################################################################
# Interpretation helpers
###############################################################################

def interpret_value(scale_id: str, value: float, element_id: str,
                    scales_ref: Dict[str, Dict[str, Any]],
                    level_anchors: Dict[str, Dict[str, Dict[int, str]]],
                    category_desc: Optional[str] = None) -> Optional[str]:
    """Generate a human readable interpretation for a scale value.

    For level scales ('LV') official anchors are used if available.  For
    distribution scales the category description provided by the caller
    (``category_desc``) is returned.  For other scales simple heuristics
    are applied based on the numerical range defined in the scales
    reference.  If no reasonable interpretation can be made this
    function returns ``None``.

    Parameters
    ----------
    scale_id: str
        Identifier of the scale (e.g. 'IM', 'LV').
    value: float
        Numeric value or category number depending on scale.
    element_id: str
        The element identifier (for retrieving anchors).
    scales_ref: Dict[str, Dict[str, Any]]
        Reference definitions for scales including min and max values.
    level_anchors: Dict[str, Dict[str, Dict[int, str]]]
        Mapping of element and scale to anchor descriptions.
    category_desc: Optional[str]
        For distribution scales the caller may supply the category
        description directly.
    """
    # distribution scales: category description is already final
    if category_desc is not None:
        return category_desc
    # level scales: look up anchor based on nearest integer
    if scale_id == 'LV':
        rounded = int(round(value))
        anchors_for_element = level_anchors.get(element_id, {}).get('LV', {})
        return anchors_for_element.get(rounded)
    # importance scales
    if scale_id in ('IM', 'IJ'):
        if value <= 1.5:
            return 'Not important'
        elif value <= 2.5:
            return 'Somewhat important'
        elif value <= 3.5:
            return 'Important'
        elif value <= 4.5:
            return 'Very important'
        else:
            return 'Extremely important'
    # extent scales (work values)
    if scale_id == 'EX':
        # EX ranges from 1 to 7
        if value <= 2:
            return 'Very low'
        elif value <= 3:
            return 'Low'
        elif value <= 4:
            return 'Moderate'
        elif value <= 5:
            return 'High'
        elif value <= 6:
            return 'Very high'
        else:
            return 'Extremely high'
    # work styles impact (WI) ranges -3 to 3
    if scale_id == 'WI':
        if value < -2:
            return 'Very negative'
        elif value < -1:
            return 'Negative'
        elif value < 1:
            return 'Neutral'
        elif value < 2:
            return 'Positive'
        else:
            return 'Very positive'
    # distinctiveness rank (DR) 0 to 10
    if scale_id == 'DR':
        if value == 0:
            return 'Not distinctive'
        elif value <= 3:
            return 'Low distinctiveness'
        elif value <= 6:
            return 'Moderate distinctiveness'
        elif value <= 8:
            return 'High distinctiveness'
        else:
            return 'Very high distinctiveness'
    # work schedule (WS) 1-3
    if scale_id == 'WS':
        if value <= 1.5:
            return 'Standard schedule'
        elif value <= 2.5:
            return 'Flexible schedule'
        else:
            return 'Irregular schedule'
    # default: no interpretation
    return None


###############################################################################
# Parsing of occupational data files
###############################################################################

def parse_element_file(path: str,
                       scales_ref: Dict[str, Dict[str, Any]],
                       level_anchors: Dict[str, Dict[str, Dict[int, str]]],
                       edu_categories: Dict[Tuple[str, int], str],
                       ctx_categories: Dict[Tuple[str, int], str],
                       task_categories: Dict[int, str]) -> Dict[str, Dict[str, Element]]:
    """Parse a data file containing element ratings for occupations.

    This generic parser reads a TSV file with columns including the
    O*NET occupation code, element ID and name, scale identifier, data
    value and optionally a category.  Distribution scales are
    recognized when the 'Category' column is present and numeric.  The
    parser accumulates all rows and later computes a single ``Scale``
    object per (occupation, element, scale) using the highest
    percentage category for distribution scales and the numeric value
    directly for continuous scales.

    Parameters
    ----------
    path: str
        Path to the TSV file.
    scales_ref: dict
        Reference definitions for scales.
    level_anchors: dict
        Anchors for level scales.
    edu_categories: dict
        Category descriptions for education/training/experience elements.
    ctx_categories: dict
        Category descriptions for work context elements.
    task_categories: dict
        Category descriptions for task frequency categories (not used here
        but kept for signature consistency).

    Returns
    -------
    Dict[str, Dict[str, Element]]
        A nested dictionary keyed first by occupation code and then by
        element ID.  Each value is an ``Element`` with its scales
        populated.
    """
    elements_by_job: Dict[str, Dict[str, Element]] = {}
    # detect if file has a Category column
    header: List[str] = []
    for row in _read_tsv_rows(path):
        header = [c.strip() for c in row]
        break
    # compute column indices
    col_index = {name: i for i, name in enumerate(header)}
    has_category = 'Category' in col_index
    job_idx = col_index.get('O*NET-SOC Code')
    elem_id_idx = col_index.get('Element ID')
    elem_name_idx = col_index.get('Element Name')
    scale_id_idx = col_index.get('Scale ID')
    value_idx = col_index.get('Data Value')
    category_idx = col_index.get('Category') if has_category else None
    if None in (job_idx, elem_id_idx, elem_name_idx, scale_id_idx, value_idx):
        return elements_by_job  # missing key columns
    # accumulate raw scale values
    # nested: job_code -> element_id -> (element_name) -> scale_id -> data
    raw_data: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for row in _read_tsv_rows(path):
        # skip header row already processed
        if row == header:
            continue
        if job_idx >= len(row) or elem_id_idx >= len(row) or scale_id_idx >= len(row) or value_idx >= len(row):
            continue
        job_code = row[job_idx].strip()
        element_id = row[elem_id_idx].strip()
        element_name = row[elem_name_idx].strip() if elem_name_idx is not None and elem_name_idx < len(row) else ''
        scale_id = row[scale_id_idx].strip()
        value_str = row[value_idx].strip()
        # Skip rows with missing or not applicable data values
        if not value_str or value_str.lower() == 'n/a':
            continue
        # distribution category (if present)
        category: Optional[int] = None
        if has_category and category_idx is not None and category_idx < len(row):
            cat_str = row[category_idx].strip()
            if cat_str and cat_str.lower() != 'n/a':
                try:
                    category = int(cat_str)
                except ValueError:
                    # Some files have categories like 'n/a' or blank; ignore
                    category = None
        # parse numeric value; if not numeric skip
        try:
            data_value = float(value_str)
        except ValueError:
            continue
        # store data
        job_entry = raw_data.setdefault(job_code, {})
        elem_entry = job_entry.setdefault(element_id, {
            'name': element_name,
            'scales': {},  # type: ignore
        })
        scale_entry = elem_entry['scales'].setdefault(scale_id, {
            'values': [],  # numeric values (for continuous scales)
            'distribution': {},  # category -> value
        })
        if category is not None:
            # distribution: accumulate percentage
            prev = scale_entry['distribution'].get(category, 0.0)
            scale_entry['distribution'][category] = prev + data_value
        else:
            # continuous numeric scale: store value (should be single value per scale)
            scale_entry['values'].append(data_value)
    # now build Elements and Scales from raw data
    for job_code, elem_map in raw_data.items():
        job_elements = elements_by_job.setdefault(job_code, {})
        for element_id, elem_data in elem_map.items():
            element_name = elem_data['name']
            element_obj = job_elements.setdefault(element_id, Element(element_id, element_name))
            for scale_id, scale_data in elem_data['scales'].items():
                distribution_map: Dict[int, float] = scale_data['distribution']
                values_list: List[float] = scale_data['values']
                if distribution_map:
                    # Distribution scale: compute category with max proportion
                    # Determine interpretation using category descriptions
                    if scale_id in ('RL', 'RW', 'PT', 'OJ'):
                        # education/training categories
                        cat_desc_map = edu_categories
                    elif scale_id == 'CXP':
                        cat_desc_map = ctx_categories
                    elif scale_id == 'FT':
                        cat_desc_map = { (None, k): v for k, v in task_categories.items() }  # will map by (None, category)
                    else:
                        # fallback: no category descriptions available
                        cat_desc_map = {}
                    # find category with max value
                    max_category = max(distribution_map.items(), key=lambda kv: kv[1])[0]
                    # find description; for RL etc., categories keyed by (element_id, category)
                    if scale_id in ('RL', 'RW', 'PT', 'OJ'):
                        interpretation = edu_categories.get((element_id, max_category))
                    elif scale_id == 'CXP':
                        interpretation = ctx_categories.get((element_id, max_category))
                    elif scale_id == 'FT':
                        interpretation = task_categories.get(max_category)
                    else:
                        interpretation = None
                    # value is category number (int)
                    value = float(max_category)
                    scale_name = scales_ref.get(scale_id, {}).get('name', scale_id)
                    scale_obj = Scale(scale_id, scale_name, value, interpretation, distribution=distribution_map.copy())
                else:
                    # numeric scale: average values_list (should usually contain a single entry)
                    if not values_list:
                        continue
                    value = sum(values_list) / len(values_list)
                    scale_name = scales_ref.get(scale_id, {}).get('name', scale_id)
                    interpretation = interpret_value(scale_id, value, element_id,
                                                   scales_ref, level_anchors)
                    scale_obj = Scale(scale_id, scale_name, value, interpretation)
                element_obj.scales[scale_id] = scale_obj
    return elements_by_job


def parse_occupation_data(path: str) -> Dict[str, Dict[str, str]]:
    """Parse basic occupation data from ``Occupation Data.txt``.

    Returns a dictionary keyed by job code with 'title' and
    'description'.
    """
    jobs: Dict[str, Dict[str, str]] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        if len(row) < 3:
            continue
        job_code = row[0].strip()
        title = row[1].strip()
        description = row[2].strip()
        jobs[job_code] = {'title': title, 'description': description}
    return jobs


def parse_alternate_titles(path: str) -> Dict[str, List[str]]:
    """Parse alternate titles from ``Alternate Titles.txt``.

    Returns a dictionary mapping job code to a list of alternate titles.
    """
    alt_titles: Dict[str, List[str]] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        if len(row) < 2:
            continue
        job_code = row[0].strip()
        title = row[1].strip()
        if title:
            alt_titles.setdefault(job_code, []).append(title)
    return alt_titles


def parse_job_zones(path: str) -> Dict[str, int]:
    """Parse job zone information from ``Job Zones.txt``.

    Returns a dictionary mapping job code to the integer job zone.
    """
    zones: Dict[str, int] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        if len(row) < 2:
            continue
        job_code = row[0].strip()
        zone_str = row[1].strip()
        try:
            zone = int(float(zone_str))
        except ValueError:
            continue
        zones[job_code] = zone
    return zones


def parse_task_statements(path: str) -> Dict[str, Dict[str, Task]]:
    """Parse task statements from ``Task Statements.txt``.

    Returns a nested dictionary keyed by job code and then task ID,
    mapping to ``Task`` objects with description and type; scales
    remain empty until ratings are attached.
    """
    tasks: Dict[str, Dict[str, Task]] = {}
    rows = list(_read_tsv_rows(path))
    # skip header
    for row in rows[1:]:
        # columns: O*NET-SOC Code, Task ID, Task, Task Type, Incumbents Responding, Date, Domain Source
        if len(row) < 4:
            continue
        job_code = row[0].strip()
        task_id = row[1].strip()
        description = row[2].strip()
        task_type = row[3].strip()
        if not (job_code and task_id and description):
            continue
        tasks.setdefault(job_code, {})[task_id] = Task(task_id=task_id, description=description, task_type=task_type)
    return tasks


def parse_task_ratings(path: str,
                       tasks: Dict[str, Dict[str, Task]],
                       scales_ref: Dict[str, Dict[str, Any]],
                       level_anchors: Dict[str, Dict[str, Dict[int, str]]],
                       task_categories: Dict[int, str]) -> None:
    """Attach ratings to tasks using data from ``Task Ratings.txt``.

    The provided ``tasks`` dictionary is modified in place.  Each
    rating row includes a scale (IM, RT or FT).  For FT the ratings
    represent a distribution across categories.  For IM and RT the
    numeric value is stored directly.
    """
    # accumulate raw ratings per task
    raw_ratings: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    header: List[str] = []
    for row in _read_tsv_rows(path):
        header = [c.strip() for c in row]
        break
    col_index = {name: i for i, name in enumerate(header)}
    has_category = 'Category' in col_index
    job_idx = col_index.get('O*NET-SOC Code')
    task_idx = col_index.get('Task ID')
    scale_idx = col_index.get('Scale ID')
    value_idx = col_index.get('Data Value')
    cat_idx = col_index.get('Category') if has_category else None
    if None in (job_idx, task_idx, scale_idx, value_idx):
        return
    for row in _read_tsv_rows(path):
        if row == header:
            continue
        if job_idx >= len(row) or task_idx >= len(row) or scale_idx >= len(row) or value_idx >= len(row):
            continue
        job_code = row[job_idx].strip()
        task_id = row[task_idx].strip()
        scale_id = row[scale_idx].strip()
        value_str = row[value_idx].strip()
        if not (job_code and task_id and scale_id and value_str):
            continue
        try:
            data_value = float(value_str)
        except ValueError:
            continue
        category: Optional[int] = None
        if has_category and cat_idx is not None and cat_idx < len(row):
            cat_str = row[cat_idx].strip()
            if cat_str and cat_str.lower() != 'n/a':
                try:
                    category = int(cat_str)
                except ValueError:
                    category = None
        key = (job_code, task_id, scale_id)
        entry = raw_ratings.setdefault(key, {'values': [], 'distribution': {}})
        if category is not None:
            # distribution across categories
            entry['distribution'][category] = entry['distribution'].get(category, 0.0) + data_value
        else:
            entry['values'].append(data_value)
    # create scales and attach to tasks
    for (job_code, task_id, scale_id), data in raw_ratings.items():
        if job_code not in tasks or task_id not in tasks[job_code]:
            continue
        dist = data['distribution']
        values = data['values']
        if dist:
            # distribution scale (FT)
            max_cat = max(dist.items(), key=lambda kv: kv[1])[0]
            interpretation = task_categories.get(max_cat)
            value = float(max_cat)
            scale_name = scales_ref.get(scale_id, {}).get('name', scale_id)
            scale_obj = Scale(scale_id, scale_name, value, interpretation, distribution=dist.copy())
        else:
            if not values:
                continue
            value = sum(values) / len(values)
            scale_name = scales_ref.get(scale_id, {}).get('name', scale_id)
            # for tasks we don't use anchors since anchors are defined for elements; use heuristics
            interpretation = interpret_value(scale_id, value, '', scales_ref, level_anchors)
            scale_obj = Scale(scale_id, scale_name, value, interpretation)
        tasks[job_code][task_id].scales[scale_id] = scale_obj


###############################################################################
# Build jobs and persistence helpers
###############################################################################

def build_job_repertoire(data_dir: str) -> Dict[str, Job]:
    """Build a repertoire of ``Job`` objects from the O*NET data directory.

    Parameters
    ----------
    data_dir: str
        Path to the directory containing the unpacked O*NET text files.

    Returns
    -------
    Dict[str, Job]
        A dictionary keyed by occupation code mapping to fully populated
        ``Job`` objects.  Each job contains its elements, tasks, alternate
        titles and job zone.
    """
    # Load reference data
    scales_ref = load_scales_reference(os.path.join(data_dir, 'Scales Reference.txt'))
    level_anchors = load_level_anchors(os.path.join(data_dir, 'Level Scale Anchors.txt'))
    edu_categories = load_education_training_categories(os.path.join(data_dir, 'Education, Training, and Experience Categories.txt'))
    ctx_categories = load_work_context_categories(os.path.join(data_dir, 'Work Context Categories.txt'))
    task_categories = load_task_categories(os.path.join(data_dir, 'Task Categories.txt'))
    # Parse job basic information
    occ_data = parse_occupation_data(os.path.join(data_dir, 'Occupation Data.txt'))
    alt_titles = parse_alternate_titles(os.path.join(data_dir, 'Alternate Titles.txt'))
    job_zones = parse_job_zones(os.path.join(data_dir, 'Job Zones.txt'))
    # Parse element files
    element_files = [
        'Abilities.txt',
        'Skills.txt',
        'Knowledge.txt',
        'Work Activities.txt',
        'Work Context.txt',
        'Work Styles.txt',
        'Work Values.txt',
        'Interests.txt',
        'Education, Training, and Experience.txt',
    ]
    elements_by_job: Dict[str, Dict[str, Element]] = {}
    for filename in element_files:
        file_path = os.path.join(data_dir, filename)
        if not os.path.exists(file_path):
            continue
        file_elements = parse_element_file(file_path, scales_ref, level_anchors,
                                           edu_categories, ctx_categories, task_categories)
        # merge into global elements_by_job
        for job_code, elems in file_elements.items():
            job_map = elements_by_job.setdefault(job_code, {})
            for elem_id, element in elems.items():
                if elem_id not in job_map:
                    job_map[elem_id] = element
                else:
                    # merge scales if element already exists
                    job_map[elem_id].scales.update(element.scales)
    # Parse tasks
    tasks = parse_task_statements(os.path.join(data_dir, 'Task Statements.txt'))
    parse_task_ratings(os.path.join(data_dir, 'Task Ratings.txt'), tasks,
                       scales_ref, level_anchors, task_categories)
    # Assemble final jobs
    jobs: Dict[str, Job] = {}
    for job_code, info in occ_data.items():
        title = info['title']
        description = info['description']
        job = Job(code=job_code,
                  title=title,
                  description=description,
                  job_zone=job_zones.get(job_code),
                  alternate_titles=alt_titles.get(job_code, []),
                  elements=elements_by_job.get(job_code, {}),
                  tasks=tasks.get(job_code, {}))
        jobs[job_code] = job
    return jobs


def save_jobs_json(jobs: Dict[str, Job], path: str) -> None:
    """Serialize the job repertoire to a JSON file.

    Parameters
    ----------
    jobs: Dict[str, Job]
        The job repertoire generated by :func:`build_job_repertoire`.
    path: str
        File path where the JSON should be written.
    """
    # Convert to serializable dict
    jobs_dict = {code: job.to_dict() for code, job in jobs.items()}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(jobs_dict, f, ensure_ascii=False, indent=2)


def load_jobs_json(path: str) -> Dict[str, Job]:
    """Load a job repertoire from a JSON file created by :func:`save_jobs_json`.

    Returns a dictionary mapping occupation codes to ``Job`` objects.
    """
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    jobs: Dict[str, Job] = {}
    for job_code, job_data in data.items():
        # reconstruct Job
        job = Job(
            code=job_data['code'],
            title=job_data['title'],
            description=job_data['description'],
            job_zone=job_data.get('job_zone'),
            alternate_titles=job_data.get('alternate_titles', []),
            elements={},
            tasks={},
        )
        # reconstruct elements
        for elem_id, elem_data in job_data.get('elements', {}).items():
            element = Element(
                element_id=elem_id,
                element_name=elem_data['element_name'],
                scales={},
            )
            for scale_id, sc_data in elem_data.get('scales', {}).items():
                scale = Scale(
                    scale_id=sc_data['scale_id'],
                    scale_name=sc_data['scale_name'],
                    value=sc_data['value'],
                    interpretation=sc_data['interpretation'],
                    distribution=sc_data.get('distribution'),
                )
                element.scales[scale_id] = scale
            job.elements[elem_id] = element
        # reconstruct tasks
        for task_id, task_data in job_data.get('tasks', {}).items():
            task = Task(
                task_id=task_id,
                description=task_data['description'],
                task_type=task_data['task_type'],
                scales={},
            )
            for scale_id, sc_data in task_data.get('scales', {}).items():
                scale = Scale(
                    scale_id=sc_data['scale_id'],
                    scale_name=sc_data['scale_name'],
                    value=sc_data['value'],
                    interpretation=sc_data['interpretation'],
                    distribution=sc_data.get('distribution'),
                )
                task.scales[scale_id] = scale
            job.tasks[task_id] = task
        jobs[job_code] = job
    return jobs


def _demo(data_dir: str, out_json: str) -> None:
    """Run a simple demonstration by building the repertoire and saving it.

    This helper is intended to be called from the command line.  It
    builds the job repertoire from ``data_dir`` and writes it to
    ``out_json``.  It also prints a summary of a few jobs to standard
    output for inspection.
    """
    jobs = build_job_repertoire(data_dir)
    save_jobs_json(jobs, out_json)
    # Print summary of first five jobs
    print(f"Parsed {len(jobs)} occupations. Writing JSON to {out_json}")
    for i, (code, job) in enumerate(jobs.items()):
        if i >= 5:
            break
        print(f"\nJob: {code} - {job.title}")
        print(f"  Description: {job.description[:100]}{'...' if len(job.description) > 100 else ''}")
        print(f"  Job Zone: {job.job_zone}")
        print(f"  Alternate titles: {', '.join(job.alternate_titles[:5])}")
        print(f"  Number of elements: {len(job.elements)}")
        print(f"  Number of tasks: {len(job.tasks)}")


if __name__ == '__main__':  # pragma: no cover
    import argparse
    parser = argparse.ArgumentParser(description='Build job repertoire from O*NET data and save to JSON.')
    parser.add_argument('data_dir', help='Path to the directory containing O*NET TSV files')
    parser.add_argument('output', help='Path to output JSON file')
    args = parser.parse_args()
    _demo(args.data_dir, args.output)