"""OpenAI Responses API adapter for structured resume parsing."""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional
from urllib import error, request

from packages.core.ports.llm_provider import LLMProvider

from packages.core.use_cases.refine_career_matches import build_refine_career_user_text

_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4.1"
_SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx"}
_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _load_api_key_from_dotenv(dotenv_path: Path) -> Optional[str]:
    """Read OPENAI_API_KEY from a .env file without third-party dependencies."""
    if not dotenv_path.exists():
        return None

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != "OPENAI_API_KEY":
            continue
        cleaned = value.strip().strip('"').strip("'")
        return cleaned or None
    return None


def _extract_output_text(response_payload: Mapping[str, Any]) -> str:
    """Extract assistant output text from a raw Responses API payload."""
    output_text = response_payload.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    output_items = response_payload.get("output")
    if isinstance(output_items, list):
        for item in output_items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != "message":
                continue
            content_items = item.get("content")
            if not isinstance(content_items, list):
                continue
            for content in content_items:
                if not isinstance(content, dict):
                    continue
                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    return text
                content_json = content.get("json")
                if isinstance(content_json, (dict, list)):
                    return json.dumps(content_json)

    raise ValueError("No text output found in Responses API payload")


class OpenAIResponsesClient(LLMProvider):
    """LLM adapter that parses resume files via the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = _DEFAULT_OPENAI_BASE_URL,
        timeout_seconds: int = 120,
    ) -> None:
        project_root = Path(__file__).resolve().parents[3]
        dotenv_api_key = _load_api_key_from_dotenv(project_root / ".env")
        resolved_api_key = api_key or os.getenv("OPENAI_API_KEY") or dotenv_api_key
        if not resolved_api_key:
            raise ValueError(
                "OPENAI_API_KEY not found. Set it in env vars or in .env at project root."
            )

        self.api_key = resolved_api_key
        self.model = model or os.getenv("OPENAI_RESUME_PARSER_MODEL", _DEFAULT_MODEL)
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def parse_resume(
        self,
        *,
        resume_path: Path,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        """Call the Responses API with a file input and strict JSON schema output."""
        normalized_path = Path(resume_path)
        if not normalized_path.exists():
            raise FileNotFoundError(f"Resume file not found: {normalized_path}")

        extension = normalized_path.suffix.lower()
        if extension not in _SUPPORTED_EXTENSIONS:
            allowed = ", ".join(sorted(_SUPPORTED_EXTENSIONS))
            raise ValueError(f"Unsupported resume type '{extension}'. Allowed: {allowed}")

        mime_type = _MIME_TYPES[extension]
        encoded_data = base64.b64encode(normalized_path.read_bytes()).decode("ascii")
        input_file = {
            "type": "input_file",
            "filename": normalized_path.name,
            "file_data": f"data:{mime_type};base64,{encoded_data}",
        }

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Parse this resume and return JSON that strictly matches the schema."
                            ),
                        },
                        input_file,
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "resume_parse_result",
                    "strict": True,
                    "schema": dict(schema),
                }
            },
        }

        response_payload = self._post_json("/responses", payload)
        text_output = _extract_output_text(response_payload)

        try:
            parsed = json.loads(text_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Responses API returned non-JSON content: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Responses API output must be a JSON object")
        return parsed

    def map_bullets_to_attributes(
        self,
        *,
        bullet_texts: List[str],
        attribute_catalog_text: str,
        schema: Mapping[str, Any],
        instructions: str,
    ) -> Dict[str, Any]:
        """Text-only call: map numbered bullets to user attributes."""
        numbered = "\n".join(
            f"{i}: {text}" for i, text in enumerate(bullet_texts)
        )

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Map the following resume bullets to attributes.\n\n"
                                f"## Attribute catalog\n{attribute_catalog_text}\n\n"
                                f"## Bullets\n{numbered}"
                            ),
                        },
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "bullet_attribute_mapping",
                    "strict": True,
                    "schema": dict(schema),
                }
            },
        }

        response_payload = self._post_json("/responses", payload)
        text_output = _extract_output_text(response_payload)

        try:
            parsed = json.loads(text_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Responses API returned non-JSON content: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Responses API output must be a JSON object")
        return parsed

    def refine_career_matches(
        self,
        *,
        matches: List[Mapping[str, Any]],
        answers: List[Mapping[str, str]],
        schema: Mapping[str, Any],
        instructions: str,
        feedback: str = "",
    ) -> Dict[str, Any]:
        """Text-only call: refine matched careers based on follow-up answers and feedback."""
        user_text = build_refine_career_user_text(matches=matches, answers=answers, feedback=feedback)

        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": instructions}],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_text,
                        },
                    ],
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "career_refinement",
                    "strict": True,
                    "schema": dict(schema),
                }
            },
        }

        response_payload = self._post_json("/responses", payload)
        text_output = _extract_output_text(response_payload)

        try:
            parsed = json.loads(text_output)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Responses API returned non-JSON content: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Responses API output must be a JSON object")
        return parsed

    def _post_json(self, path: str, payload: Mapping[str, Any]) -> Dict[str, Any]:
        """POST JSON payload to OpenAI API and return parsed JSON response."""
        url = f"{self.base_url}{path}"
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )

        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"OpenAI Responses API error ({exc.code}): {detail}"
            ) from exc
        except error.URLError as exc:
            raise RuntimeError(f"Failed to reach OpenAI Responses API: {exc}") from exc

        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenAI API returned invalid JSON: {exc}") from exc

        if not isinstance(decoded, dict):
            raise RuntimeError("OpenAI API returned unexpected payload type")
        return decoded
