"""User service functions for CareerHQ.

This module provides service-layer functions for user operations,
including adding job experiences and updating user attributes.
"""

from datetime import datetime
from typing import Dict, Optional

from .user_class import Job, User, UserAttribute, UserAttributeTemplate
from .user_initialize import get_attribute_template_registry
from .occupation_class import Element, Occupation


def add_job_experience(
    user: User,
    occupation: Occupation,
    job_title: str,
    company_name: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    duration_months: Optional[int] = None,
    salary: Optional[float] = None,
) -> Job:
    """Add a job experience to the user's profile.

    This function:
    1. Creates a Job from the Occupation (copying element data)
    2. Adds it to user.jobs
    3. Triggers attribute updates based on the job

    Parameters
    ----------
    user : User
        The user to add the job to.
    occupation : Occupation
        The O*NET occupation for this job.
    job_title : str
        The user's actual job title.
    company_name : str
        Name of the company/employer.
    start_date : Optional[str]
        Start date in ISO format (optional).
    end_date : Optional[str]
        End date in ISO format (optional, None if current job).
    duration_months : Optional[int]
        Duration in months (alternative to start/end dates).
    salary : Optional[float]
        Salary (optional).

    Returns
    -------
    Job
        The created Job instance.
    """
    # Create job from occupation (copies element data)
    job = Job.from_occupation(
        occupation=occupation,
        job_title=job_title,
        company_name=company_name,
        salary=salary,
        start_date=start_date,
        end_date=end_date,
        duration_months=duration_months,
    )

    # Add to user profile
    user.add_job(job)

    # Update user attributes based on this job
    update_user_attributes_from_job(user, job)

    return job


def update_user_attributes_from_job(user: User, job: Job) -> None:
    """Update user attributes based on a job experience.

    This function dispatches to two different update functions:
    1. Attributes WITH element_id mapping (O*NET mapped)
    2. Attributes WITHOUT element_id mapping (custom attributes)

    Parameters
    ----------
    user : User
        The user whose attributes to update.
    job : Job
        The job experience to derive attributes from.
    """
    # Get attribute templates (only leaf attributes)
    registry = get_attribute_template_registry()
    leaf_templates = registry.get_leaf_templates()

    # Separate into two sets based on element mapping
    mapped_templates: Dict[str, UserAttributeTemplate] = {
        attr_id: tmpl
        for attr_id, tmpl in leaf_templates.items()
        if tmpl.mapping_element_id is not None
    }
    unmapped_templates: Dict[str, UserAttributeTemplate] = {
        attr_id: tmpl
        for attr_id, tmpl in leaf_templates.items()
        if tmpl.mapping_element_id is None
    }

    # Update each set with different logic
    update_attributes_with_element_mapping(user, job, mapped_templates)
    update_attributes_without_element_mapping(user, job, unmapped_templates)


def update_attributes_with_element_mapping(
    user: User,
    job: Job,
    templates: Dict[str, UserAttributeTemplate],
) -> None:
    """Update user attributes that have O*NET element mappings.

    These attributes can be derived from the job's element data
    (e.g., skills, abilities from the occupation).

    For each attribute template with a mapping_element_id:
    - Look up the corresponding element in job.elements
    - Extract relevant scale values (e.g., importance, level)
    - Update or create the user attribute with derived values

    Formulas:
    - capability += years * experience_score (capped at 100)
    - preference += years * 2 (capped at 100)

    See docs/attribute_update_logic.md for detailed formula documentation.

    Parameters
    ----------
    user : User
        The user whose attributes to update.
    job : Job
        The job experience containing element data.
    templates : Dict[str, UserAttributeTemplate]
        Attribute templates that have element_id mappings.
    """
    years = _get_job_years(job)

    for attr_id, template in templates.items():
        element_id = template.mapping_element_id
        if element_id is None:
            continue

        element = job.elements.get(element_id)
        if element is None:
            continue

        # Calculate experience score based on element scales
        experience_score = _calculate_experience_score(element)

        # Get existing attribute or create from template
        attr = user.get_attribute(attr_id)
        if attr is None:
            attr = template.instantiate()
            user.add_attribute(attr)

        # Update capability (cumulative, capped at 100)
        capability_delta = years * experience_score
        current_capability = attr.capability or 0
        attr.capability = min(100, current_capability + int(capability_delta))

        # Update preference (cumulative, capped at 100)
        preference_delta = years * 2
        current_preference = attr.preference or 0
        attr.preference = min(100, current_preference + int(preference_delta))


def _get_job_years(job: Job) -> float:
    """Calculate the number of years for a job experience.

    Parameters
    ----------
    job : Job
        The job to calculate years for.

    Returns
    -------
    float
        Number of years (can be fractional).
    """
    # Prefer explicit duration_months if provided
    if job.duration_months is not None:
        return job.duration_months / 12.0

    # Calculate from start_date and end_date if available
    if job.start_date:
        try:
            start = datetime.fromisoformat(job.start_date)
            if job.end_date:
                end = datetime.fromisoformat(job.end_date)
            else:
                end = datetime.now()
            delta = end - start
            return delta.days / 365.25
        except ValueError:
            pass

    # Default to 1 year if no duration info
    return 1.0


def _calculate_experience_score(element: Element) -> float:
    """Calculate experience score (0-1) from element scales.

    The experience score represents how much capability a user gains
    per year of experience with this element.

    Different element types use different scale combinations:
    - LV + IM scales (Abilities, Skills, Knowledge): (LV * IM) / 35
    - OI scale (Interests): OI / 7
    - EX scale (Work Values): EX / 7
    - WI scale (Work Styles): (WI + 3) / 6
    - Category distributions (RL, RW, PT, OJ): highest percentage / 100

    Parameters
    ----------
    element : Element
        The element to calculate score for.

    Returns
    -------
    float
        Experience score between 0 and 1.
    """
    # Check for LV + IM scales (most common: Abilities 1.A, Skills 2.A/2.B, Knowledge 2.C)
    lv_scale = element.get_scale("LV")
    im_scale = element.get_scale("IM")
    if lv_scale and im_scale and lv_scale.value is not None and im_scale.value is not None:
        # LV range: 0-7, IM range: 1-5, max product = 35
        return (lv_scale.value * im_scale.value) / 35.0

    # OI scale (Occupational Interests 1.B.1)
    oi_scale = element.get_scale("OI")
    if oi_scale and oi_scale.value is not None:
        # OI range: 1-7
        return oi_scale.value / 7.0

    # EX scale (Work Values extent 1.B.2)
    ex_scale = element.get_scale("EX")
    if ex_scale and ex_scale.value is not None:
        # EX range: 1-7
        return ex_scale.value / 7.0

    # WI scale (Work Styles Impact 1.D)
    wi_scale = element.get_scale("WI")
    if wi_scale and wi_scale.value is not None:
        # WI range: -3 to 3, normalize to 0-1
        return (wi_scale.value + 3) / 6.0

    # Category distribution scales (Education 2.D, Training 3.A)
    # Find the highest percentage among category scales
    max_pct = 0.0
    for scale_id, scale in element.scales.items():
        if scale_id.startswith(("RL-", "RW-", "PT-", "OJ-")):
            if scale.value is not None and scale.value > max_pct:
                max_pct = scale.value
    if max_pct > 0:
        return max_pct / 100.0

    # Default fallback
    return 0.5


def update_attributes_without_element_mapping(
    user: User,
    job: Job,
    templates: Dict[str, UserAttributeTemplate],
) -> None:
    """Update user attributes that do NOT have O*NET element mappings.

    These are custom attributes (e.g., personality types, age, custom work values)
    that require different logic to update. Many of these may not be derivable
    from job experience and may require direct user input.

    Parameters
    ----------
    user : User
        The user whose attributes to update.
    job : Job
        The job experience (may not be directly used for all custom attributes).
    templates : Dict[str, UserAttributeTemplate]
        Attribute templates without element_id mappings.
    """
    # TODO: Implementation details
    # Custom attributes may include:
    #   - 1.N.1 (Age) - not derivable from job
    #   - 1.N.2.x (Personality types) - not derivable from job
    #   - 2.N.x (Custom education) - may need separate input
    #   - 4.N.x (Custom work values) - may need user preference input
    pass
