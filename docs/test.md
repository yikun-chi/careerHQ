# Test Reference

## How to run

| Runner | Command |
|--------|---------|
| All unit tests (unittest) | `python -m unittest discover tests -v` |
| All unit tests (pytest) | `pytest tests/ -v -s` |
| Single module | `python -m unittest tests.test_resume_parser -v` |
| Live resume parse | `python -m tests.test_parse_resume_live` |

> **Note:** `test_occupation_initialize`, `test_user_class`, and `test_user_service` use pytest.
> `test_resume_parser` uses unittest.
> `test_parse_resume_live` is a standalone script (not a test framework).

---

## Test files

### `tests/test_resume_parser.py`

Unit tests for the resume parsing use case. Uses a `FakeResumeLLMProvider` to return canned payloads — no network calls.

| Test | What it verifies |
|------|-----------------|
| `test_parse_resume_file_returns_normalized_resume` | A well-formed LLM payload is correctly deserialized into `ParsedResume` with all fields: `job_title`, `company_title`, `occupation_id`, `occupation_title`, `years_of_experience`, `projects`, `skills`, `education`. |
| `test_parse_resume_file_raises_for_missing_file` | `FileNotFoundError` is raised when the resume path does not exist. |

---

### `tests/test_parse_resume_live.py`

Standalone script that calls the OpenAI Responses API against `tests/test_data/test_resume.pdf`.
Prints full JSON output and a human-readable summary. Validates that every returned `occupation_id` exists in the O\*NET database.

Run: `python -m tests.test_parse_resume_live`

Requires `OPENAI_API_KEY` in environment or `.env` at project root.

---

### `tests/test_init_profile.py`

Unit tests for the profile initialization pipeline. Uses unittest with a `FakeLLMProvider` — no network calls.

| Class | What it covers |
|-------|---------------|
| `TestCollectBullets` | Job-level bullets use `job.years_of_experience`; project-level bullets use fixed 1.0 year; correct `bullet_index` sequencing. |
| `TestBuildCatalogText` | Catalog output is sorted by attribute ID; contains expected attribute names. |
| `TestParseMappingResponse` | Valid LLM JSON → `BulletAttributeMapping` objects; malformed entries (non-dict, non-int index, int attribute ID) are skipped. |
| `TestUpdateAttributesFromBulletMappings` | Basic capability/preference update; invalid attribute IDs skipped; relevance clamped to [0,1]; values capped at 100. |
| `TestInitProfileFromResume` | Occupation-only (no bullets); combined occupation + bullet updates accumulate; unknown occupation IDs tracked in `skipped_occupations`; project bullets use 1.0 year. |
| `TestEducationBinaryAttributes` | Bachelor's sets cumulative binary flags (1–6 True, 7–12 False); highest level wins across multiple entries; no education → no binary attributes. |

---

### `tests/test_career_analysis.py`

Unit tests for the career analysis matching logic. Uses unittest with mock `User` and `Occupation` objects — no network calls, no pickle loading.

| Class | What it covers |
|-------|---------------|
| `TestGetUserTop3` | Returns top 3 attributes by capability; skips zero-capability; filters by prefix (only matching category). |
| `TestGetOccTop3` | Returns top 3 occupation elements ranked by scale value. |
| `TestGetOccTop3Interests` | Combines OI (interests) and EX (work values) scales into a single ranked list. |
| `TestFindMatchingOccupations` | Perfect match (3/3 overlap); partial match (2/3 overlap meets threshold); insufficient overlap (1/3 → no match); category skipped when user has < 2 scored attributes; multiple categories (abilities + work styles); results sorted descending by match count; capped at 15 results; empty user → no matches; cross-prefix matching (user `3.A` → O\*NET `2.A`). |
| `TestCareerMatchDataclass` | `CareerMatch` fields are correctly set and accessible. |

---

### `tests/test_occupation_initialize.py`

Tests for the O\*NET occupation data loading pipeline. Uses pytest.

| Class | What it covers |
|-------|---------------|
| `TestOrganizationRegistry` | Organization hierarchy loads, node count, sample lookups, parent-child structure. |
| `TestScaleDefinitions` | Scale definitions load, have required fields, grouped by ordinal/interval type. |
| `TestElements` | Leaf elements load, are truly leaves (no children), have correct taxonomy prefixes, span all categories. |
| `TestIntegration` | All registries load together; element organization refs exist in registry. |
| `TestElementScales1A` | 1.A Abilities: IM/LV scale schemas, anchor loading, mapping, population of 52 ability elements. |
| `TestElementScales1B` | 1.B Interests & Values: OI/EX scale schemas, mapping, population of 12 elements; 1.B.3 intentionally unpopulated. |
| `TestElementScales1D` | 1.D Work Styles: WI/DR scale schemas, mapping, population of 21 elements, subcategory counts. |
| `TestElementScales2ABC` | 2.A/B/C Skills & Knowledge: LV anchors, mapping, population of 68 elements (10 + 25 + 33). |
| `TestElementScales2D3A` | 2.D/3.A Education & Training: RL/RW/PT/OJ category distribution scales, population of 6 elements. |
| `TestOccupationPopulate` | Schema creation (159 elements), occupation list loading (1016 occupations), empty occupation creation, rating file parsing, spot-check of populated values against raw data files. |

---

### `tests/test_user_class.py`

Tests for user domain models. Uses pytest.

| Class | What it covers |
|-------|---------------|
| `TestUserAttribute` | Creation, value setting, capability/preference range validation (0-100). |
| `TestUserAttributeTemplate` | Immutability (frozen dataclass), instantiation to mutable `UserAttribute`. |
| `TestJob` | Job creation with all fields, current job detection (no end date). |
| `TestJobFromOccupation` | `Job.from_occupation()` factory copies elements from a loaded `Occupation`. |
| `TestUser` | User creation, add/get attributes, add/get jobs, most-recent-first ordering, current job lookup. |
| `TestUserAttributeTemplateLoading` | CSV template loading, expected count (~308), category coverage, single-template lookup, instantiation. |
| `TestIntegration` | End-to-end: create user, load templates, instantiate attributes, set values. |

---

### `tests/test_user_service.py`

Tests for the user service layer (job experience flow and attribute updates). Uses pytest.

| Class | What it covers |
|-------|---------------|
| `TestGetJobYears` | Duration calculation from `duration_months`, start/end dates, default 1-year fallback. |
| `TestCalculateExperienceScore` | Score computation for LV+IM, OI, WI, and category distribution scales. |
| `TestAddJobExperience` | Adding a job to a user, element copying, attribute updates. |
| `TestUpdateAttributesWithElementMapping` | Capability increases with years, preference at 2 pts/year, cumulative across jobs, capped at 100. |
| `TestFullWorkflow` | Complete end-to-end: create user, add job, verify attributes populated with correct values. |

---

### `tests/presentation/sprint1.py`

Demo/presentation script for sprint 1. Not a test suite.
