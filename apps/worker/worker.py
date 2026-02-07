"""Worker task registry entrypoint."""

from __future__ import annotations

from typing import Callable, Dict

from apps.worker.tasks import parse_resume_task


def get_registered_tasks() -> Dict[str, Callable]:
    """Return task names mapped to callables for worker bootstrap code."""
    return {
        "parse_resume": parse_resume_task,
    }
