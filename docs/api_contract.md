# API Contract

This document describes the HTTP endpoints that are actually implemented.

## Base

- **Base path:** `/api`
- **Auth:** None (not yet implemented)
- **Server:** FastAPI + Uvicorn on port 8000

## Endpoints

### `GET /`

Serves the static frontend (`web/index.html`).

### `GET /static/*`

Serves static assets (CSS, JS) from the `web/` directory.

### `POST /api/upload`

Accepts a resume file, runs the full parse-and-profile pipeline synchronously, and returns the complete result.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|:---|:---|:---|:---|
| `file` | file | yes | Resume file (`.pdf`, `.doc`, or `.docx`) |

**Success Response:** `200 OK`

```json
{
  "jobs": [
    {
      "job_title": "Analytics Associate",
      "company": "Acme Corp",
      "occupation": "Management Analysts",
      "years": 3.0
    }
  ],
  "education": [
    {
      "institution": "State University",
      "degree": "Bachelor of Science",
      "field": "Computer Science",
      "year": 2020
    }
  ],
  "resume_skills": ["Python", "SQL", "Tableau"],
  "attribute_sections": [
    {
      "label": "Abilities",
      "prefix": "1.A",
      "attributes": [
        {
          "attribute_id": "1.A.1.a.1",
          "name": "Oral Comprehension",
          "capability": 12.3,
          "preference": 10.0
        }
      ]
    }
  ],
  "stats": {
    "jobs_added": 2,
    "bullets_mapped": 15,
    "attributes_updated": 142
  }
}
```

**Response fields:**

| Field | Description |
|:---|:---|
| `jobs[]` | Parsed job entries with matched O*NET occupation title and years |
| `education[]` | Parsed education entries |
| `resume_skills[]` | Flat list of skills extracted from the resume |
| `attribute_sections[]` | 7 sections, each with up to 5 top attributes sorted by capability |
| `stats` | Summary counts from the profile initialization pipeline |

**Attribute sections** (7 total):

| Label | Prefix | Category |
|:---|:---|:---|
| Abilities | `1.A` | Cognitive and physical abilities |
| Work Styles | `1.D` | Behavioral traits (e.g., attention to detail) |
| Education | `2.D` | Education level requirements |
| Basic Skills | `3.A` | Foundational skills (reading, writing, math) |
| Cross-Functional Skills | `3.B` | Complex skills (critical thinking, problem solving) |
| Knowledge | `3.C` | Domain knowledge areas |
| Interests & Work Values | `4.B` | Holland interest codes and work values |

**Error Responses:**

| Status | Condition | Body |
|:---|:---|:---|
| `400` | Unsupported file extension | `{"detail": "Unsupported file type '.txt'. Allowed: .pdf, .doc, .docx"}` |
| `500` | Pipeline failure (LLM error, parse error, etc.) | `{"detail": "<error message>"}` |

## LLM Integration

### Port

`LLMProvider` protocol in `packages/core/ports/llm_provider.py` defines two methods:
- `parse_resume()` — file-based structured extraction
- `map_bullets_to_attributes()` — text-based bullet-to-attribute mapping

### Adapter

`OpenAIResponsesClient` in `packages/infra/llm/client.py`:
- **Model:** `gpt-4.1` (configurable via `OPENAI_RESUME_PARSER_MODEL` env var)
- **API:** OpenAI Responses API (`POST /v1/responses`)
- **Schema enforcement:** `strict: true` JSON schema mode
- **File handling:** Base64-encoded file content with MIME type
- **HTTP client:** stdlib `urllib` (no `requests` or `httpx` dependency)
- **Timeout:** 120 seconds

Two LLM calls are made per upload:
1. **Resume parse** — file + system prompt with 1016 O*NET occupations and alternate titles → structured JSON (jobs, skills, education)
2. **Bullet mapping** — numbered bullet texts + attribute catalog → attribute mappings with relevance scores

## Environment Variables

| Variable | Required | Default | Description |
|:---|:---|:---|:---|
| `OPENAI_API_KEY` | yes | — | OpenAI API key (read from env or `.env` at project root) |
| `OPENAI_RESUME_PARSER_MODEL` | no | `gpt-4.1` | Override the LLM model |

## End-to-End Flow

```
Browser                  API Service              LLM (OpenAI)
  │                          │                        │
  │  POST /api/upload        │                        │
  │  (multipart file)        │                        │
  │─────────────────────────>│                        │
  │                          │  parse_resume()        │
  │                          │  (file + occupation    │
  │                          │   list + schema)       │
  │                          │───────────────────────>│
  │                          │  structured JSON       │
  │                          │<───────────────────────│
  │                          │                        │
  │                          │  Phase 1: add_job_     │
  │                          │  experience() ×N jobs  │
  │                          │  (local, no LLM)       │
  │                          │                        │
  │                          │  map_bullets_to_       │
  │                          │  attributes()          │
  │                          │  (bullets + catalog    │
  │                          │   + schema)            │
  │                          │───────────────────────>│
  │                          │  mapping JSON          │
  │                          │<───────────────────────│
  │                          │                        │
  │                          │  Phase 2: update       │
  │                          │  attrs from bullets    │
  │                          │  (local, no LLM)       │
  │                          │                        │
  │                          │  Phase 3: education    │
  │                          │  binary attrs          │
  │                          │  (local, no LLM)       │
  │                          │                        │
  │  200 JSON response       │                        │
  │  (jobs, education,       │                        │
  │   skills, attributes,    │                        │
  │   stats)                 │                        │
  │<─────────────────────────│                        │
```

## Planned Endpoints (Not Yet Implemented)

These endpoints appear in earlier design docs but have no working code:

- `POST /api/chat/stream` — Conversational chat with SSE streaming
- `GET /api/profile` — Full profile retrieval with field filtering
- `GET /api/profile/status` — Background processing status polling
