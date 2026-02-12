# CareerHQ Quickstart

## Prerequisites
- Python 3.13+ (or Docker)
- An OpenAI API key

## Setup

1. Copy `.env.example` to `.env` and add your key:
   ```
   cp .env.example .env
   ```

2. Edit `.env` and set `OPENAI_API_KEY`.

## Run with Docker (recommended)

```
docker compose up --build
```

Open http://localhost:8000

## Run locally

```
pip install -r requirements.txt
python -m uvicorn apps.api.main:app --reload
```

Open http://localhost:8000

## Run tests

```
python -m unittest tests.test_resume_parser tests.test_init_profile -v
```
