"""Live test: parse test_resume.pdf and print structured output.

Run from project root:
    python -m tests.test_parse_resume_live

Requires OPENAI_API_KEY in environment or .env file.
"""

import json
import sys
from pathlib import Path

# Add project root for imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.core.use_cases.process_resume import parse_resume_with_openai


def main() -> None:
    resume_path = Path(__file__).parent / "test_data" / "test_resume.pdf"
    if not resume_path.exists():
        print(f"ERROR: test resume not found at {resume_path}")
        sys.exit(1)

    print(f"Parsing resume: {resume_path}")
    print("Calling OpenAI Responses API (this may take a moment)...\n")

    parsed = parse_resume_with_openai(resume_path)

    # ---- Pretty-print full JSON ----
    print("=" * 70)
    print("FULL PARSED OUTPUT (JSON)")
    print("=" * 70)
    print(json.dumps(parsed.to_dict(), indent=2))

    # ---- Human-readable summary ----
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\nJobs ({len(parsed.jobs)}):")
    for i, job in enumerate(parsed.jobs, 1):
        print(f"\n  [{i}] {job.job_title}  @  {job.company_title}")
        print(f"      Occupation       : [{job.occupation_id}] {job.occupation_title}")
        print(f"      Years of exp     : {job.years_of_experience}")
        if job.bullet_points:
            print(f"      Bullet points ({len(job.bullet_points)}):")
            for bp in job.bullet_points:
                print(f"        - {bp}")
        if job.projects:
            print(f"      Projects ({len(job.projects)}):")
            for proj in job.projects:
                print(f"        * {proj.project_name or '(unnamed)'}")
                for bp in proj.bullet_points:
                    print(f"            - {bp}")

    print(f"\nEducation ({len(parsed.education)}):")
    for i, edu in enumerate(parsed.education, 1):
        degree_str = f"{edu.degree} in {edu.field_of_study}" if edu.degree else "(no degree)"
        year_str = f" ({edu.graduation_year})" if edu.graduation_year else ""
        print(f"  [{i}] {edu.institution} — {degree_str}{year_str}")
        if edu.bullet_points:
            for bp in edu.bullet_points:
                print(f"        - {bp}")

    print(f"\nSkills ({len(parsed.skills)}): {', '.join(parsed.skills)}")


if __name__ == "__main__":
    main()
