"""Career analysis endpoint."""

import asyncio
from dataclasses import asdict

from fastapi import APIRouter, HTTPException

from apps.api.main import app_state
from packages.core.use_cases.career_analysis import find_matching_occupations

router = APIRouter()


@router.get("/career-analysis")
async def career_analysis():
    user = app_state.get("current_user")
    if user is None:
        raise HTTPException(status_code=404, detail="No user profile yet. Upload a resume first.")

    occupations = app_state["occupations"]

    loop = asyncio.get_running_loop()
    matches = await loop.run_in_executor(
        None, find_matching_occupations, user, occupations
    )

    return {
        "matches": [asdict(m) for m in matches],
    }
