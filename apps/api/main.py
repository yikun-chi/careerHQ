"""CareerHQ FastAPI application."""

from contextlib import asynccontextmanager
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from packages.core.domain.attribute_info import load_scale_anchors
from packages.core.domain.occupation_populate import load_occupations
from packages.core.use_cases.process_resume import build_resume_parse_instructions

# Shared state populated at startup
app_state: dict = {}

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
QUESTIONS_CONFIG_PATH = Path(__file__).resolve().parents[2] / "packages" / "core" / "data" / "career_questions.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_state["occupations"] = load_occupations()
    app_state["resume_instructions"] = build_resume_parse_instructions()
    app_state["career_questions"] = json.loads(QUESTIONS_CONFIG_PATH.read_text())
    app_state["scale_anchors"] = load_scale_anchors()
    yield
    app_state.clear()


app = FastAPI(title="CareerHQ", lifespan=lifespan)

# Mount static files (CSS / JS)
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")

# Register API routes
from apps.api.routes.upload import router as upload_router  # noqa: E402
from apps.api.routes.career import router as career_router  # noqa: E402

app.include_router(upload_router, prefix="/api")
app.include_router(career_router, prefix="/api")


@app.get("/")
async def index():
    return FileResponse(str(WEB_DIR / "index.html"))
