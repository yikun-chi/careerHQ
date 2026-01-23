# TODO (MVP Build Sequence)

Objective: Ordered feature checklist with implementation focus and file touchpoints.

## 1) Project Skeleton + Config
Goal: Establish runnable services and shared packages with minimal wiring.
Files to open/implement:
- apps/api/main.py
- apps/worker/worker.py
- packages/core/__init__.py
- packages/infra/__init__.py

## 2) Profile Data Model (MVP)
Goal: Define the profile attribute structure with metadata (source, extracted_at, optional confidence) and a storage strategy for evolving fields.
Files to open/implement:
- packages/core/domain/profile.py
- packages/core/schemas/profile_update.py
- packages/infra/db/models.py

## 3) Resume Upload API
Goal: Accept resume files and store them reliably; return upload_id.
Files to open/implement:
- apps/api/routes/upload.py
- packages/core/ports/file_storage.py
- packages/infra/storage/files.py
- packages/core/use_cases/process_resume.py

## 4) Resume Parsing + Profile Initialization (Worker)
Goal: Parse resume into structured data and initialize profile attributes.
Files to open/implement:
- apps/worker/tasks/parse_resume.py
- apps/worker/tasks/init_profile.py
- packages/core/use_cases/process_resume.py
- packages/core/domain/resume.py
- packages/core/ports/profile_repository.py
- packages/infra/db/models.py

## 5) Chat Streaming API
Goal: Stream assistant responses to the frontend with minimal latency.
Files to open/implement:
- apps/api/routes/chat.py
- packages/core/use_cases/chat_turn.py
- packages/core/ports/llm_provider.py
- packages/infra/llm/client.py

## 6) Profile Retrieval API
Goal: Return full profile attributes and visualization-ready data.
Files to open/implement:
- apps/api/routes/profile.py
- packages/core/use_cases/get_profile.py
- packages/core/ports/profile_repository.py
- packages/infra/db/models.py

## 7) Background Queue Wiring
Goal: Dispatch resume parsing jobs from API and execute in worker with retries.
Files to open/implement:
- packages/core/ports/queue.py
- packages/infra/queue/broker.py
- apps/api/routes/upload.py
- apps/worker/worker.py

## 8) Frontend MVP Shell
Goal: Basic chat UI + resume upload + visualization container.
Files to open/implement:
- web/index.html
- web/app.js
- web/styles.css

## 9) Visualization Rendering
Goal: Render profile attributes into charts/tables using returned `visualization` payload.
Files to open/implement:
- web/app.js
- web/styles.css

## 10) Logging + Basic Observability
Goal: Structured logs for API + Worker to trace user flows.
Files to open/implement:
- packages/infra/telemetry/logging.py
- apps/api/main.py
- apps/worker/worker.py

## 11) Basic Tests (Smoke)
Goal: Validate core flows: upload -> parse -> profile -> visualize.
Files to open/implement:
- tests/README.md
