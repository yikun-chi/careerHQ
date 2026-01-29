# Attribute Update Logic

This document describes the formulas and rationale for updating user attributes based on job experience.

## Overview

When a user adds a job experience, their attributes are updated based on:
1. The O*NET element data associated with the occupation
2. The duration of the job experience (in years)

## Attribute Fields

Each `UserAttribute` has three value fields:

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `capability` | float | 0-100 | User's experience/skill level in this attribute |
| `preference` | float | 0-100 | User's preference for work involving this attribute |
| `binary` | bool | True/False | Categorical flag (used for education/training levels) |

**Note:** Capability and preference are stored as floats to preserve precision during accumulation across multiple jobs. When displaying to users, consider rounding to 1-2 decimal places.

## Update Formulas

### Capability

**Formula:**
```
capability_delta = years * experience_score
new_capability = min(100, current_capability + capability_delta)
```

Where:
- `years` = duration of job experience in years
- `experience_score` = value between 0-1 derived from element scales (see below)

**Rationale:** Capability accumulates with experience. A job that heavily uses a skill (high experience_score) contributes more capability per year than a job that barely uses it.

### Preference

**Formula:**
```
preference_delta = years * 2
new_preference = min(100, current_preference + preference_delta)
```

**Rationale:** The more years a user spends doing something, the more likely they prefer it (self-selection effect). The constant factor of 2 means 50 years of total experience would max out preference, which is reasonable for a career span.

### Binary

Only applicable to category distribution elements (Education 2.D, Training 3.A):
- Set to `True` if the user's job experience indicates they meet the requirement
- Currently not implemented; reserved for future education/certification tracking

## Experience Score Calculation

The experience score (0-1) represents how much capability a user gains per year from a particular element. Different element types use different scale combinations:

### 1. Abilities, Skills, Knowledge (LV + IM scales)

**Elements:** 1.A.*, 2.A.*, 2.B.*, 2.C.*

**Formula:**
```
experience_score = (LV * IM) / 35
```

Where:
- `LV` (Level): 0-7 scale indicating complexity/difficulty
- `IM` (Importance): 1-5 scale indicating how critical the element is
- Max product: 7 * 5 = 35

**Rationale:** Both level and importance matter. A highly important skill at a high level contributes more than a marginally important skill at a low level.

**Example:**
- Oral Comprehension for Chief Executive: LV=4.88, IM=4.62
- experience_score = (4.88 * 4.62) / 35 = 0.644
- 3 years experience → capability_delta = 3 * 0.644 = 1.93 ≈ 1

### 2. Occupational Interests (OI scale)

**Elements:** 1.B.1.*

**Formula:**
```
experience_score = OI / 7
```

Where:
- `OI` (Occupational Interests): 1-7 scale

**Rationale:** Direct mapping of interest relevance to experience contribution.

### 3. Work Values (EX scale)

**Elements:** 1.B.2.*

**Formula:**
```
experience_score = EX / 7
```

Where:
- `EX` (Extent): 1-7 scale indicating how much the value is satisfied

**Rationale:** Direct mapping of value satisfaction to experience contribution.

### 4. Work Styles (WI scale)

**Elements:** 1.D.*

**Formula:**
```
experience_score = (WI + 3) / 6
```

Where:
- `WI` (Work Styles Impact): -3 to +3 scale
- Normalized to 0-1 range

**Rationale:** Work styles impact can be negative (detrimental) or positive (beneficial). The formula normalizes this to a positive experience contribution.

### 5. Category Distributions (RL, RW, PT, OJ scales)

**Elements:** 2.D.1 (Education), 3.A.* (Training)

**Formula:**
```
experience_score = max_percentage / 100
```

Where category scales include:
- `RL-1` to `RL-12`: Required Level of Education (% of workers at each level)
- `RW-1` to `RW-11`: Related Work Experience categories
- `PT-1` to `PT-9`: On-Site Training categories
- `OJ-1` to `OJ-9`: On-The-Job Training categories

**Rationale:** The highest percentage category indicates the most common requirement, which we use as a proxy for how much experience this job provides.

### 6. Default Fallback

If no recognized scale is found:
```
experience_score = 0.5
```

**Rationale:** Neutral contribution when scale data is missing.

## Scale Reference

| Scale ID | Name | Range | Type | Used By |
|----------|------|-------|------|---------|
| LV | Level | 0-7 | Interval | Abilities, Skills, Knowledge |
| IM | Importance | 1-5 | Ordinal | Abilities, Skills, Knowledge |
| OI | Occupational Interests | 1-7 | Interval | Interests (1.B.1) |
| EX | Extent | 1-7 | Interval | Work Values (1.B.2) |
| WI | Work Styles Impact | -3 to +3 | Interval | Work Styles (1.D) |
| RL-n | Education Level n | 0-100 | Interval | Education (2.D.1) |
| RW-n | Work Experience n | 0-100 | Interval | Work Experience (3.A.1) |
| PT-n | On-Site Training n | 0-100 | Interval | On-Site Training (3.A.2) |
| OJ-n | On-Job Training n | 0-100 | Interval | On-Job Training (3.A.3) |

## Example Calculation

**Scenario:** User adds 3 years as "Chief Executive" at "Acme Corp"

For attribute "1.A.1.a.1 Oral Comprehension":
- mapping_element_id = "1.A.1.a.1"
- Element has LV=4.88, IM=4.62
- experience_score = (4.88 * 4.62) / 35 = 0.644
- capability_delta = 3 * 0.644 = 1.93 → rounds to 1
- preference_delta = 3 * 2 = 6

If user had no prior Oral Comprehension:
- capability: 0 → 1
- preference: 0 → 6

If user had prior capability=50, preference=30:
- capability: 50 → 51
- preference: 30 → 36

## Future Considerations

1. **Diminishing returns:** Consider logarithmic scaling for capability to model mastery plateaus
2. **Recency weighting:** More recent jobs could have stronger influence
3. **Job level/seniority:** Entry-level vs senior roles could scale experience differently
4. **Skill decay:** Long gaps between jobs could reduce capability over time
