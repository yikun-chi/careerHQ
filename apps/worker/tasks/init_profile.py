"""Profile initialization task — seeds user attributes after resume parsing."""

from __future__ import annotations

from packages.core.domain.resume import ParsedResume
from packages.core.domain.user_class import User
from packages.core.use_cases.init_profile_from_resume import (
    ProfileInitResult,
    init_profile_from_resume,
)
from packages.infra.llm.client import OpenAIResponsesClient


def run_init_profile(user: User, parsed_resume: ParsedResume) -> ProfileInitResult:
    """Entry point for the worker task.

    Creates an OpenAI client and delegates to the use case.
    """
    provider = OpenAIResponsesClient()
    return init_profile_from_resume(user, parsed_resume, provider)
