# API Contract (MVP)

Objective: Define minimal HTTP contracts for chat, resume upload, and profile visualization without implementation details.

## Base
- Base path: /api
- Content type: application/json (unless uploading files)
- Auth: bearer token in `Authorization: Bearer <token>` (placeholder)

## 1) Chat
### POST /api/chat/stream
Streams an assistant response for a single user message.

Request (JSON):
```
{
  "user_id": "string",
  "message": "string",
  "conversation_id": "string",
  "client_context": {
    "timezone": "string",
    "locale": "string"
  }
}
```

Response:
- `text/event-stream` or WebSocket stream (implementation TBD)
- Events: `message_delta`, `message_done`, `error`

Example SSE payload (conceptual):
```
event: message_delta
data: {"text": "Hello"}

event: message_done
data: {"message_id": "string"}
```

## 2) Resume Upload
### POST /api/uploads/resume
Uploads a resume and starts parsing / profile initialization.

Request (multipart/form-data):
- `file`: resume PDF/DOCX
- `user_id`: string

Response (JSON):
```
{
  "upload_id": "string",
  "status": "queued"
}
```

## 3) Profile Retrieval
### GET /api/profile
Fetches the full profile and visualization-ready data.

Query params:
- `user_id` (required)
- `fields` (optional, comma-separated)

Response (JSON):
```
{
  "user_id": "string",
  "attributes": {
    "technical_skills": {
      "value": ["Python", "SQL"],
      "source": "resume",
      "extracted_at": "2026-01-22T15:04:12Z",
      "confidence": 0.82
    }
  },
  "visualization": {
    "skill_radar": {"series": [/* ... */]}
  }
}
```

## 4) Profile Update Status (optional)
### GET /api/profile/status
Returns background processing state.

Query params:
- `user_id` (required)

Response (JSON):
```
{
  "user_id": "string",
  "profile_status": "initializing | ready | error",
  "last_updated": "2026-01-22T15:04:12Z"
}
```
## Sample End-to-End Flow
1) User opens the app
- Frontend shows chat UI + �Upload resume� prompt.
- No backend call yet.

2) User uploads resume
- Frontend sends `POST /api/uploads/resume` with `file` and `user_id`.
- Backend responds: `{ "upload_id": "upl_123", "status": "queued" }`.
- UI shows �Parsing your resume�� spinner.

3) Background parsing kicks off
- Worker reads the file, extracts fields, and initializes profile attributes.
- UI can optionally poll `GET /api/profile/status?user_id=...` until `profile_status: ready`.

4) User starts chatting
- Frontend sends `POST /api/chat/stream` with message + `conversation_id`.
- API streams deltas so the assistant �types� the response in real time.

5) Profile view loads
- Once status is `ready` (or on a timer), frontend calls `GET /api/profile?user_id=...`.
- Response includes `attributes` plus a `visualization` object.
- UI renders charts from `visualization` while also showing raw attributes if needed.

6) Continued usage
- As the user chats, new info gets extracted by the worker.
- UI refreshes periodically to reflect updated attributes and charts.

