# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run API server locally
python -m uvicorn apps.api.main:app --reload --port 8000

# Run with Docker
docker compose up --build

# Run all tests (unittest, no pytest)
python -m unittest discover tests -v

# Run a single test file
python -m unittest tests.test_user_service -v

# Run a single test class
python -m unittest tests.test_user_service.TestUserService -v

# Run a single test method
python -m unittest tests.test_user_service.TestUserService.test_add_job_experience -v

# Live test (calls real OpenAI API, requires OPENAI_API_KEY in .env)
python -m unittest tests.test_parse_resume_live -v
```

## Architecture

Hexagonal architecture (ports & adapters). The core has zero infrastructure dependencies.

```
apps/api/          → FastAPI gateway (sync, port 8000)
apps/worker/       → Worker module (future async tasks, currently called synchronously)
packages/core/
  domain/          → Domain models (Occupation, User, ParsedResume, etc.)
  use_cases/       → Business orchestration (resume parsing, profile init, career matching)
  ports/           → Protocol interfaces (LLMProvider)
packages/infra/    → Adapters (OpenAIResponsesClient; db/queue/storage/telemetry are stubs)
web/               → Vanilla HTML/CSS/JS frontend (no build step)
tests/             → unittest-based tests
```

### Request flow (POST /api/upload)

1. FastAPI receives multipart file upload
2. **LLM Call 1**: `parse_resume_file()` sends resume + full O*NET occupation list to OpenAI Responses API with strict JSON schema → returns `ParsedResume`
3. **Profile init** (`init_profile_from_resume()`) runs 3 phases:
   - **Phase 1**: For each job, look up O*NET occupation, update user attributes from element scales
   - **Phase 2**: **LLM Call 2** maps all bullet points to user attributes with relevance scores
   - **Phase 3**: Set education binary attributes based on highest education level
4. Response includes jobs, education, skills, attribute sections, and stats

### Key startup behavior

`apps/api/main.py` lifespan preloads two expensive resources into `app_state`:
- `occupations`: 1016-occupation dict from `occupations.pkl` (~22MB)
- `resume_instructions`: LLM prompt with all O*NET occupations + alternate titles baked in

### LLM integration

- Port: `LLMProvider` Protocol in `packages/core/ports/llm_provider.py` (two methods: `parse_resume`, `map_bullets_to_attributes`)
- Adapter: `OpenAIResponsesClient` in `packages/infra/llm/client.py` (uses stdlib `urllib`, no third-party HTTP lib)
- Model: `gpt-4.1` (configurable via `OPENAI_RESUME_PARSER_MODEL` env var)
- Both LLM calls use strict JSON schema mode

### Data

- O*NET source files in `packages/core/data/` (tab-delimited `.txt` files)
- Pickled occupations in `packages/core/data/initialized/occupations.pkl`
- ~307 user attribute templates loaded from `packages/core/data/user_attribute.csv`
- Attributes use dotted hierarchy (e.g., `1.A.1.a.1` = Oral Comprehension) with `mapping_element_id` linking to O*NET elements

## Dependencies

Runtime: `fastapi`, `uvicorn`, `python-multipart` only. Python 3.13+. OpenAI API key required in `.env` (see `.env.example`).
