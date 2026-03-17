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

`LLMProvider` protocol in `packages/core/ports/llm_provider.py` defines four methods:
- `parse_resume()` — file-based structured extraction
- `map_bullets_to_attributes()` — text-based bullet-to-attribute mapping
- `refine_career_matches()` — text-based refinement of career matches from user Q&A answers
- `generate_career_roadmap()` — text-based structured roadmap generation
- `validate_and_fix_roadmap_links()` — text-based URL plausibility check and replacement

### Adapter

`OpenAIResponsesClient` in `packages/infra/llm/client.py`:
- **Model:** `gpt-4.1` (configurable via `OPENAI_RESUME_PARSER_MODEL` env var)
- **API:** OpenAI Responses API (`POST /v1/responses`)
- **Schema enforcement:** `strict: true` JSON schema mode
- **File handling:** Base64-encoded file content with MIME type
- **HTTP client:** stdlib `urllib` (no `requests` or `httpx` dependency)
- **Timeout:** 120 seconds

LLM calls per user journey:
1. **Resume parse** — file + system prompt with 1016 O*NET occupations and alternate titles → structured JSON (jobs, skills, education)
2. **Bullet mapping** — numbered bullet texts + attribute catalog → attribute mappings with relevance scores
3. **Career refinement** *(optional)* — initial matches + follow-up Q&A answers → reranked top careers with reasons
4. **Roadmap generation** — gap analysis + user context → structured 4–6 milestone roadmap
5. **Link validation** — resource URLs from the roadmap → plausibility assessment + replacement suggestions for any invalid URLs

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

---

### `GET /api/career-analysis`

Runs the occupational matching algorithm against the current user's attribute profile and returns ranked matches with follow-up questions.

**Success Response:** `200 OK`

```json
{
  "matches": [
    {
      "occupation_id": "13-1111.00",
      "occupation_name": "Management Analysts",
      "match_count": 4,
      "total_categories": 5,
      "matched_categories": ["Abilities", "Knowledge", "Work Styles", "Basic Skills"]
    }
  ],
  "follow_up_questions": [
    "What kind of work environment do you prefer?",
    "..."
  ]
}
```

**Error Responses:**

| Status | Condition |
|:---|:---|
| `404` | No user profile in session (upload first) |

---

### `POST /api/career-analysis/refine`

Refines the career matches using the user's answers to follow-up questions and/or free-text feedback.

**Request Body:** `application/json`

```json
{
  "answers": [
    { "question": "What environment do you prefer?", "answer": "Remote" }
  ],
  "feedback": "I'm interested in data science roles"
}
```

**Success Response:** `200 OK`

```json
{
  "top_careers": [
    {
      "occupation_id": "15-2051.00",
      "occupation_name": "Data Scientists",
      "reason": "Strong alignment with your analytical skills and remote work preference"
    }
  ]
}
```

**Error Responses:**

| Status | Condition |
|:---|:---|
| `400` | No answers or feedback provided |
| `400` | Fewer than 3 career matches to refine |
| `404` | No user profile in session |
| `500` | LLM call failure |

---

### `PUT /api/user/attributes/{attribute_id}`

Manually overrides the capability score for a single user attribute.

**Path parameter:** `attribute_id` — dotted attribute ID (e.g., `1.A.1.a.1`)

**Request Body:** `application/json`

```json
{ "capability": 75.0 }
```

**Success Response:** `200 OK`

```json
{ "attribute_id": "1.A.1.a.1", "capability": 75.0 }
```

**Error Responses:**

| Status | Condition |
|:---|:---|
| `400` | Capability not in [0, 100] |
| `404` | No user profile, or attribute ID not found |

---

### `POST /api/career-roadmap`

Generates a personalized career roadmap from the user's current role to a target occupation. Runs two sequential LLM calls: roadmap generation, then URL validation and patching.

**Request Body:** `application/json`

```json
{
  "occupation_id": "15-2051.00",
  "occupation_name": "Data Scientists"
}
```

**Success Response:** `200 OK`

```json
{
  "roadmap_title": "From Management Analyst to Data Scientist",
  "estimated_timeline_months": 18,
  "summary": "A focused 18-month plan bridging your analytical foundation into data science...",
  "milestones": [
    {
      "milestone_number": 1,
      "title": "Build Python & Statistics Foundation",
      "description": "...",
      "timeline_months": "1-3",
      "milestone_type": "skill_building",
      "actions": [
        {
          "action_title": "Complete Python for Data Science",
          "action_description": "...",
          "action_type": "learn",
          "resources": [
            {
              "resource_name": "Python for Everybody",
              "resource_type": "course",
              "url": "https://www.coursera.org/specializations/python",
              "description": "Beginner Python specialization on Coursera"
            }
          ]
        }
      ]
    }
  ]
}
```

**Response fields:**

| Field | Description |
|:---|:---|
| `roadmap_title` | Concise title for the transition |
| `estimated_timeline_months` | Total realistic months for the full transition |
| `summary` | 2–3 sentence overview of the strategy |
| `milestones[]` | 4–6 ordered milestone objects |
| `milestones[].milestone_type` | One of: `skill_building`, `certification`, `experience`, `networking`, `transition`, `advancement` |
| `milestones[].actions[]` | 2–4 concrete actions per milestone |
| `milestones[].actions[].action_type` | One of: `learn`, `certify`, `build`, `network`, `apply`, `practice` |
| `milestones[].actions[].resources[]` | 2–3 resources per action with validated URLs |
| `milestones[].actions[].resources[].resource_type` | One of: `course`, `book`, `community`, `tool`, `certification_program`, `website` |

**URL validation:** After the roadmap is generated, a second LLM call validates every resource URL for plausibility (HTTPS, known domain, path matching resource name/type). Invalid URLs are replaced in-place before the response is returned. If URL validation fails, the original roadmap is returned unchanged.

**Error Responses:**

| Status | Condition |
|:---|:---|
| `404` | No user profile in session |
| `404` | `occupation_id` not found in the O*NET database |
| `500` | Roadmap generation LLM failure |

---

## Planned Endpoints (Not Yet Implemented)

These endpoints appear in earlier design docs but have no working code:

- `POST /api/chat/stream` — Conversational chat with SSE streaming
- `GET /api/profile` — Full profile retrieval with field filtering
- `GET /api/profile/status` — Background processing status polling
