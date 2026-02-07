"""Worker task for resume parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from packages.core.ports.llm_provider import LLMProvider
from packages.core.use_cases.process_resume import parse_resume_file, parse_resume_with_openai


def parse_resume_task(
    resume_path: Union[str, Path],
    *,
    llm_provider: Optional[LLMProvider] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Parse a resume and return structured output payload for downstream tasks."""
    normalized_path = Path(resume_path)
    if llm_provider is not None:
        parsed = parse_resume_file(normalized_path, llm_provider=llm_provider)
    else:
        parsed = parse_resume_with_openai(normalized_path, model=model)

    return {
        "resume_path": str(normalized_path),
        "parsed_resume": parsed.to_dict(),
    }
