# Business Logic

This document describes the business logic for initializing and updating a user's career profile from resume data. It supersedes `attribute_update_logic.md` by covering all three phases of profile initialization.

## 1. Elements & Scales Overview

An **element** is a measurable dimension of an occupation defined by the O*NET database — things like "Oral Comprehension" (an ability), "Python" (a knowledge area), or "Attention to Detail" (a work style).

- **159 unique elements** across all occupations
- Elements use **hierarchical dotted notation** (e.g., `1.A.1.a.1` = Oral Comprehension under Cognitive Abilities under Abilities)
- Each element has one or more **scales** that quantify its relevance to an occupation (e.g., Level, Importance)
- The same element appears across many occupations but with different scale values

## 2. Scale Dictionary

| Scale ID | Name | Range | Type | Meaning | Used By |
|:---|:---|:---|:---|:---|:---|
| LV | Level | 0–7 | Interval | Complexity/difficulty required | Abilities (1.A), Skills (2.A, 2.B), Knowledge (2.C) |
| IM | Importance | 1–5 | Ordinal | How critical the element is to the occupation | Abilities (1.A), Skills (2.A, 2.B), Knowledge (2.C) |
| OI | Occupational Interests | 1–7 | Interval | Relevance of a Holland interest code | Interests (1.B.1) |
| EX | Extent | 1–7 | Interval | How much a work value is satisfied | Work Values (1.B.2) |
| WI | Work Styles Impact | -3 to +3 | Interval | Behavioral trait impact (negative = detrimental) | Work Styles (1.D) |
| DR | Data Relevance | 0–100 | Interval | General relevance percentage | Various |
| RL-n | Required Education Level n | 0–100 | Interval | % of workers at education level n | Education (2.D.1) |
| RW-n | Related Work Experience n | 0–100 | Interval | % of workers needing experience level n | Work Experience (3.A.1) |
| PT-n | On-Site Training n | 0–100 | Interval | % of workers needing training level n | On-Site Training (3.A.2) |
| OJ-n | On-Job Training n | 0–100 | Interval | % of workers needing OJT level n | On-Job Training (3.A.3) |

## 3. User Attributes Overview

A **user attribute** represents a user's measured capability, preference, or binary qualification in a specific area. Attributes are the user-facing counterpart of O*NET elements.

### Attribute Fields

| Field | Type | Range | Description |
|:---|:---|:---|:---|
| `capability` | float | 0–100 | Accumulated experience/skill level |
| `preference` | float | 0–100 | Inferred preference for work involving this attribute |
| `binary` | bool | True/False | Categorical flag (used for education levels) |

### Attribute Templates

~307 leaf attribute templates are loaded from `packages/core/data/user_attribute.csv` at runtime via `get_attribute_template_registry()`. Each template defines:
- `attribute_id` — dotted hierarchical ID
- `attribute_name` — human-readable name
- `mapping_element_id` — O*NET element ID (if mapped), or `None` for custom attributes
- `description` — what the attribute measures

### Attribute Hierarchy

| Prefix | Category | Mapping |
|:---|:---|:---|
| `1.A` | Abilities | Maps to O*NET 1.A elements |
| `1.B` | Interests & Work Values | Maps to O*NET 1.B elements |
| `1.D` | Work Styles | Maps to O*NET 1.C elements |
| `2.D` | Education | Maps to O*NET 2.D elements |
| `3.A` | Basic Skills | Maps to O*NET 2.A elements |
| `3.B` | Cross-Functional Skills | Maps to O*NET 2.B elements |
| `3.C` | Knowledge | Maps to O*NET 2.C elements |
| `4.B` | Interests & Work Values (display group) | Maps to O*NET 1.B elements |
| `1.N`, `2.N`, `4.N` | Custom (no O*NET mapping) | Personality types, age, custom values |

### Element ID Remapping

User attribute IDs and O*NET element IDs use different prefixes. The `mapping_element_id` field bridges them. For example:
- User attribute `3.A.1.a.1` (Active Listening) → O*NET element `2.A.1.a.1`
- User attribute `3.C.1.a` (Administration and Management) → O*NET element `2.C.1.a`

## 4. Pipeline Orchestration

`init_profile_from_resume()` in `packages/core/use_cases/init_profile_from_resume.py` runs all three phases sequentially.

**Inputs:**
- `user: User` — the user to populate
- `parsed_resume: ParsedResume` — output from resume parsing (jobs, education, skills)
- `llm_provider: LLMProvider` — for the Phase 2 LLM call
- `occupations: Dict[str, Occupation]` — pre-loaded occupation dictionary (optional; loads from disk if omitted)

**Output:** `ProfileInitResult`
- `jobs_added: int` — number of jobs successfully matched to occupations
- `bullets_mapped: int` — number of bullets with at least one attribute mapping
- `attributes_updated: int` — total attributes with any non-null value
- `skipped_occupations: List[str]` — occupation IDs from resume that weren't found in the database

## 5. Phase 1 — Job Experience Updates

**Code:** `add_job_experience()` and `update_attributes_with_element_mapping()` in `packages/core/domain/user_service.py`

For each job in the parsed resume:
1. Look up the `Occupation` by `occupation_id`
2. Create a `Job` from the occupation (copies all element data)
3. Add the job to `user.jobs`
4. Update mapped attributes using the occupation's element scales

### Education Skip

Attributes under `2.D.1.*` (education levels) are **skipped** in Phase 1. These are set exclusively via the Phase 3 binary logic, since education level is better determined from explicit education entries than from job occupation data.

### Years Calculation

Years for a job are determined in priority order:
1. `duration_months / 12` if `duration_months` is set
2. Calculated from `start_date` and `end_date` (or now if current job)
3. Default: `1.0` year

When called from the pipeline, `duration_months` is set to `int(years_of_experience * 12)` from the parsed resume.

### Experience Score Formulas

The experience score (0–1) determines how much capability a user gains per year from a given element:

| Element Type | Scales | Formula | Max Score |
|:---|:---|:---|:---|
| Abilities, Skills, Knowledge | LV + IM | `(LV × IM) / 35` | 1.0 |
| Occupational Interests | OI | `OI / 7` | 1.0 |
| Work Values | EX | `EX / 7` | 1.0 |
| Work Styles | WI | `(WI + 3) / 6` | 1.0 |
| Category Distributions | RL-n, RW-n, PT-n, OJ-n | `max_percentage / 100` | 1.0 |
| Fallback (no scale found) | — | `0.5` | 0.5 |

### Update Formulas

**Capability:**
```
capability_delta = years × experience_score
new_capability = min(100, current_capability + capability_delta)
```

**Preference:**
```
preference_delta = years × 2
new_preference = min(100, current_preference + preference_delta)
```

Rationale: Capability accumulates proportionally to how much the job uses that skill. Preference accumulates at a flat rate (self-selection assumption — you tend to prefer what you do).

### Worked Example

**Scenario:** 3 years as "Chief Executive" at "Acme Corp"

For attribute `1.A.1.a.1` (Oral Comprehension):
- `mapping_element_id` = `1.A.1.a.1`
- Element scales: LV=4.88, IM=4.62
- `experience_score` = (4.88 × 4.62) / 35 = **0.644**
- `capability_delta` = 3 × 0.644 = **1.93**
- `preference_delta` = 3 × 2 = **6.0**

Starting from zero:
- capability: 0 → 1.93
- preference: 0 → 6.0

Starting from capability=50, preference=30:
- capability: 50 → 51.93
- preference: 30 → 36.0

## 6. Phase 2 — Bullet-to-Attribute Updates

**Code:** `_collect_bullets()`, `_build_catalog_text()`, `_parse_mapping_response()` in `init_profile_from_resume.py`; `update_attributes_from_bullet_mappings()` in `user_service.py`

### Bullet Collection

`_collect_bullets()` flattens all bullets from the parsed resume into a numbered `BulletContext` list:

| Source | `years` value |
|:---|:---|
| Job-level bullet points | `job.years_of_experience` |
| Project-level bullet points | `1.0` (fixed) |

Each `BulletContext` includes: `bullet_index`, `text`, `occupation_title`, `source` ("job" or "project"), `project_name`, `years`.

### Attribute Catalog

`_build_catalog_text()` formats all ~307 leaf attribute templates as:
```
attribute_id | attribute_name | description
```

This text is injected into the LLM prompt so the model can pick valid attribute IDs.

### LLM Call

The `map_bullets_to_attributes()` call sends:
- **System prompt:** Instructions to map each bullet to up to 3 attributes with relevance scores (0–1)
- **User prompt:** The attribute catalog + numbered bullet texts
- **Schema:** `BULLET_MAPPING_SCHEMA` (strict JSON)

Output per bullet:
```json
{
  "bullet_index": 0,
  "attributes": [
    {"attribute_id": "3.A.1.a.1", "relevance_score": 0.8},
    {"attribute_id": "3.C.1.a", "relevance_score": 0.5}
  ]
}
```

Up to 3 attributes per bullet. `relevance_score`:
- `1.0` = direct demonstration
- `0.5` = moderately related
- `0.1` = tangentially related

### Update Formulas

The same formulas as Phase 1, but using `relevance_score` instead of `experience_score`:

**Capability:**
```
capability_delta = years × relevance_score
new_capability = min(100, current_capability + capability_delta)
```

**Preference:**
```
preference_delta = years × 2
new_preference = min(100, current_preference + preference_delta)
```

`relevance_score` is clamped to [0, 1]. Invalid `attribute_id` values (not in the template registry) are silently skipped.

## 7. Phase 3 — Education Binary Attributes

**Code:** `_apply_education_binary()` in `init_profile_from_resume.py`

### Education Levels

| Level | Attribute ID | Description |
|:---|:---|:---|
| 1 | `2.D.1.1` | Less than a High School Diploma |
| 2 | `2.D.1.2` | High School Diploma (or GED) |
| 3 | `2.D.1.3` | Post-Secondary Certificate |
| 4 | `2.D.1.4` | Some College Courses |
| 5 | `2.D.1.5` | Associate's Degree |
| 6 | `2.D.1.6` | Bachelor's Degree |
| 7 | `2.D.1.7` | Post-Baccalaureate Certificate |
| 8 | `2.D.1.8` | Master's Degree |
| 9 | `2.D.1.9` | Post-Master's Certificate |
| 10 | `2.D.1.10` | First Professional Degree (J.D., M.D.) |
| 11 | `2.D.1.11` | Doctoral Degree (Ph.D., Ed.D.) |
| 12 | `2.D.1.12` | Post-Doctoral Training |

### Cumulative Binary Logic

1. Find the highest `education_level` across all education entries in the parsed resume
2. For each level 1–12:
   - If `level <= max_level` → `binary = True`
   - If `level > max_level` → `binary = False`

**Example:** User has a Master's Degree (`education_level = 8`):
- `2.D.1.1` through `2.D.1.8` → `True`
- `2.D.1.9` through `2.D.1.12` → `False`

### Why Phase 1 Skips Education

Phase 1 (`update_attributes_with_element_mapping`) explicitly skips all `2.D.1.*` attributes. This is because:
- O*NET occupation data contains education distributions (% of workers at each level), which are useful for matching but poor proxies for an individual's education
- The actual education entries from the resume are far more accurate
- Phase 3 handles these attributes definitively using the parsed `education_level` field

## 8. Resume Parsing (Pre-Pipeline)

Before the 3-phase pipeline runs, `parse_resume_file()` in `process_resume.py` handles the LLM call to extract structured data from the resume.

**Key details:**
- System prompt includes all 1016 O*NET occupations with alternate titles for matching
- Schema enforces `education_level` as an integer enum (1–12)
- Each job must have `occupation_id` and `occupation_title` matched to a real O*NET entry
- Post-parse validation checks that all returned `occupation_id` values exist in the database
- Bullet points are preserved at both job level and project level for Phase 2

## 9. Career Analysis — Occupation Matching

**Code:** `find_matching_occupations()` in `packages/core/use_cases/career_analysis.py`

After a user's profile is initialized from their resume, the career analysis feature finds O\*NET occupations that match the user's attribute profile. This is pure data comparison — no LLM call required.

### Category Configuration

The algorithm compares across 6 attribute categories. Education (`2.D`) is excluded because it uses binary attributes, not capability scores.

| Category | User Prefix | O\*NET Prefix | Scale | # Elements |
|:---|:---|:---|:---|:---|
| Abilities | `1.A` | `1.A` | IM | 52 |
| Work Styles | `1.D` | `1.D` | WI | 25 |
| Basic Skills | `3.A` | `2.A` | IM | 10 |
| Cross-Functional Skills | `3.B` | `2.B` | IM | 25 |
| Knowledge | `3.C` | `2.C` | IM | 33 |
| Interests & Work Values | `4.B` | `1.B` | OI / EX | 12 |

For Interests & Work Values, interests (`1.B.1.*`) use OI (1–7) and work values (`1.B.2.*`) use EX (1–7). Since both scales share the same numeric range, they are combined and ranked together.

### Algorithm

1. **Build user top-3 sets** — For each of the 6 categories:
   - Get the user's leaf attributes where `attribute_id.startswith(prefix + ".")` and `capability > 0`
   - Sort by capability descending, take top 3
   - Collect their `mapping_element_id` values into a set
   - Skip the category if fewer than 2 scored attributes exist

2. **Score each occupation** — For each of the 1016 occupations:
   - For each eligible category:
     - Get the occupation's elements where `element_id.startswith(onet_prefix + ".")`
     - Rank by the category's scale value, take top 3 element IDs
     - Count overlap with the user's top-3 set
     - If overlap >= 2, the category matches
   - Sum matched categories → `match_count`

3. **Filter and rank** — Keep occupations with `match_count >= 1`, sort descending by `match_count`, return top 15

### Thresholds

| Parameter | Value | Rationale |
|:---|:---|:---|
| Top N per category | 3 | Balances specificity and coverage |
| Min scored attributes | 2 | Prevents matching on sparse data |
| Min overlap for category match | 2 | Requires meaningful alignment, not just a lucky single match |
| Max results returned | 15 | Keeps the UI focused |

### Return Type

```python
@dataclass
class CareerMatch:
    occupation_id: str
    occupation_name: str
    match_count: int          # categories matched (out of total_categories)
    total_categories: int     # categories the user had enough data for
    matched_categories: list  # e.g. ["Abilities", "Knowledge", "Work Styles"]
```

### Worked Example

**Scenario:** User has top abilities `{1.A.1.a, 1.A.1.b, 1.A.1.c}` and top knowledge `{2.C.1.a, 2.C.1.b, 2.C.1.c}` (via mapping from `3.C.*`).

For occupation "Management Analysts" (13-1111.00):
- Top 3 abilities by IM: `{1.A.1.a, 1.A.1.b, 1.A.1.d}` → overlap with user = 2 → **match**
- Top 3 knowledge by IM: `{2.C.1.a, 2.C.4.a, 2.C.1.b}` → overlap with user = 2 → **match**
- Result: `match_count = 2`, `total_categories = 2`, `matched_categories = ["Abilities", "Knowledge"]`

## 10. Future Considerations

1. **Diminishing returns** — Logarithmic scaling for capability to model mastery plateaus
2. **Recency weighting** — More recent jobs could have stronger influence
3. **Job level/seniority** — Entry-level vs senior roles could scale experience differently
4. **Skill decay** — Long gaps between jobs could reduce capability over time
5. **Custom attribute logic** — N-prefixed attributes (personality types, age, custom work values) currently have no update logic; they require direct user input
6. **Bullet confidence weighting** — Combining LLM relevance scores with confidence estimates
7. **Career analysis refinement** — Weighting category matches by relevance (e.g., Knowledge matches worth more than Work Styles), user-adjustable thresholds, or incorporating capability magnitude (not just top-3 membership)
