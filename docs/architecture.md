# Architecture

This document describes the actual implemented architecture of CareerHQ.

## 1. Core Design Principles

### 1.1 Hexagonal Architecture (Ports & Adapters)

- **Core** (`packages/core/`): Domain models, use cases, and business logic. Zero dependencies on specific vendors or infrastructure.
- **Ports** (`packages/core/ports/`): Python `Protocol` interfaces that define how the core communicates with external services (e.g., `LLMProvider`).
- **Adapters** (`packages/infra/`): Concrete implementations of ports (e.g., `OpenAIResponsesClient`).

### 1.2 Major Components

| Component | Purpose |
|:---|:---|
| `apps/api/` | FastAPI gateway — serves the web UI and the single API endpoint |
| `apps/worker/` | Worker module — wraps the profile-init use case (currently invoked synchronously from the API, no queue) |
| `packages/core/` | Domain models, use cases, ports |
| `packages/infra/` | Infrastructure adapters (LLM client, stub dirs for db/queue/storage/telemetry) |
| `web/` | Vanilla HTML/CSS/JS frontend |
| `tests/` | Unit and integration tests (`unittest`) |

## 2. The Apps Layer

### 2.1 The API Service (`apps/api/`)

The synchronous gateway. FastAPI application defined in `apps/api/main.py`.

**Lifespan preloading** — at startup the `lifespan` context manager loads two expensive resources into `app_state`:
- `occupations`: the full 1016-occupation dictionary from pickle (`load_occupations()`)
- `resume_instructions`: the LLM prompt with the complete O*NET occupation list and alternate titles (`build_resume_parse_instructions()`)

**Routes:**
- `GET /` — serves `web/index.html` via `FileResponse`
- `/static/*` — serves CSS/JS from `web/` via `StaticFiles`
- `POST /api/upload` — the single API endpoint (see `api_contract.md`)

**Request flow for `/api/upload`:**
1. Validate file extension (`.pdf`, `.doc`, `.docx`)
2. Write upload to a temp file
3. Run the synchronous pipeline in a thread executor:
   - `parse_resume_file()` → calls LLM to extract structured resume data
   - `init_profile_from_resume()` → seeds user attributes from the parsed resume (3 phases)
4. Build response JSON (jobs, education, skills, attribute sections, stats)
5. Clean up temp file

### 2.2 The Worker Module (`apps/worker/`)

`apps/worker/tasks/init_profile.py` exposes `run_init_profile(user, parsed_resume)`. It creates an `OpenAIResponsesClient` and delegates to `init_profile_from_resume()`.

Currently the API calls the use case directly (no task queue). The worker module exists as a future integration point for async processing.

## 3. The Packages Layer

### 3.1 Core Domain (`packages/core/domain/`)

| File | Contents |
|:---|:---|
| `occupation_class.py` | `Occupation`, `Element`, `ElementScale`, `OrganizationRegistry` — O*NET data model |
| `occupation_initialize.py` | Loads raw O*NET data files, builds element trees |
| `occupation_initialize_*.py` | Per-category loaders (1a, 1b, 1d, 2abc, 2d3a) |
| `occupation_populate.py` | `load_occupations()` → dict of 1016 `Occupation` objects from pickle; `load_occupations_list()` → lightweight (id, name, description) tuples |
| `user_class.py` | `User`, `UserAttribute`, `UserAttributeTemplate`, `AttributeTemplateRegistry`, `Job` |
| `user_initialize.py` | Loads `~307` attribute templates from `user_attribute.csv`; `get_attribute_template_registry()` |
| `user_service.py` | `add_job_experience()`, `update_user_attributes_from_job()`, `update_attributes_from_bullet_mappings()` — the Phase 1 and Phase 2 update logic |
| `resume.py` | `ParsedResume`, `ResumeJob`, `ResumeEducation`, `ResumeProject` — structured resume output |
| `bullet_mapping.py` | `BulletContext`, `AttributeMapping`, `BulletAttributeMapping` — data structures for Phase 2 |
| `profile.py` | (placeholder) |

### 3.2 Core Use Cases (`packages/core/use_cases/`)

| File | Contents |
|:---|:---|
| `process_resume.py` | `parse_resume_file()` — sends resume + O*NET occupation list to LLM, validates output against `RESUME_PARSE_SCHEMA` |
| `init_profile_from_resume.py` | `init_profile_from_resume()` — orchestrates all 3 phases: occupation-based updates, bullet-to-attribute mapping, education binary attributes. Returns `ProfileInitResult` |

### 3.3 Core Ports (`packages/core/ports/`)

| File | Contents |
|:---|:---|
| `llm_provider.py` | `LLMProvider` Protocol with two methods: `parse_resume()` and `map_bullets_to_attributes()` |

### 3.4 Infrastructure (`packages/infra/`)

| Directory | Status |
|:---|:---|
| `llm/client.py` | **Implemented** — `OpenAIResponsesClient` (gpt-4.1, Responses API, strict JSON schema, base64 file encoding, stdlib `urllib`) |
| `db/` | Stub — `models.py` placeholder |
| `queue/` | Stub — `broker.py` placeholder |
| `storage/` | Stub — `files.py` placeholder |
| `telemetry/` | Stub — `logging.py` placeholder |

## 4. The Web Layer (`web/`)

Vanilla HTML/CSS/JS — no framework, no build step.

| File | Purpose |
|:---|:---|
| `index.html` | Single page: chat container with upload zone |
| `styles.css` | Chat bubbles, drag-and-drop zone, result cards, progress bars |
| `app.js` | Drag-and-drop + click-to-browse upload, `fetch("/api/upload")`, renders result cards |

**UI flow:**
1. Greeting message on page load
2. User drops or selects a resume file (`.pdf`, `.doc`, `.docx`)
3. Spinner while the backend processes (30-60 seconds)
4. Result cards rendered: Work Experience, Education, Skills from Resume, Profile Attributes (7 sections with top-5 bar charts)

## 5. Data Layer

### 5.1 O*NET Occupations
- **Source:** O*NET database text files in `packages/core/data/`
- **Initialized form:** `packages/core/data/initialized/occupations.pkl` (~22 MB pickle)
- **Count:** 1016 occupations, each with up to 159 elements
- **Alternate titles:** `Alternate Titles.txt` — used in resume parsing prompt for better occupation matching

### 5.2 User Attribute Templates
- **Source:** `packages/core/data/user_attribute.csv`
- **Count:** ~307 leaf attribute templates
- **Hierarchy:** Dotted notation (e.g., `1.A.1.a.1` = Oral Comprehension)
- **Mapping:** Each template has an optional `mapping_element_id` connecting it to an O*NET element

### 5.3 Element Scales
- 159 unique elements across categories (Abilities, Interests, Work Values, Work Styles, Skills, Knowledge, Education/Training)
- 10 scale types: DR, EX, IM, LV, OI, OJ, PT, RL, RW, WI
- See `business_logic.md` for scale details

## 6. Deployment

### Dockerfile
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml
Single `web` service — builds from Dockerfile, maps port 8000, reads `.env` for `OPENAI_API_KEY`.

### requirements.txt
```
fastapi==0.115.12
uvicorn[standard]==0.34.0
python-multipart==0.0.20
```

No other runtime dependencies. The LLM client uses stdlib `urllib`.

## 7. Not Yet Implemented

The following features are planned but have no working code:

- **Chat streaming** — SSE/WebSocket conversational interface
- **Profile retrieval** — `GET /api/profile` endpoint
- **Database** — PostgreSQL persistence (infra/db is a stub)
- **Task queue** — Celery/Redis async processing (infra/queue is a stub)
- **File storage** — S3/local file storage (infra/storage is a stub)
- **Telemetry** — Logging and monitoring (infra/telemetry is a stub)
- **Authentication** — User tokens, session management
- **Custom attributes** — N-prefixed attributes (personality, age) require user input, not job-derived
