# API Contract — RRB ALP Mock Test Platform

**Version:** 1.0.0  
**Base URL:** `https://your-backend.onrender.com` (production) | `http://localhost:8000` (local)  
**API Prefix:** All endpoints are prefixed with `/api` except `/health`

---

## Authentication

All protected endpoints require a `Bearer` token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

The token is a JWT obtained from the Google OAuth flow.  
Tokens expire after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 60 minutes).

---

## Common Response Formats

### Success (List with Pagination)
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### Error
```json
{
  "error": "Human-readable description",
  "details": [
    { "field": "question_count", "message": "must be one of [20, 30, 40, 50, 75]" }
  ],
  "status_code": 422
}
```

### Common HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 204 | No Content (DELETE success) |
| 400 | Bad Request |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (valid token, wrong user) |
| 404 | Not Found |
| 409 | Conflict (duplicate) |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Enum Reference

| Field | Allowed Values |
|-------|---------------|
| `correct_answer` | `"A"`, `"B"`, `"C"`, `"D"` |
| `source_type` (question) | `"PYQ"`, `"AI_GENERATED"`, `"REFERENCE"` |
| `source_type` (mock test) | `"PYQ"`, `"AI_GENERATED"`, `"MIXED"` |
| `verification_status` | `"VERIFIED"`, `"NEEDS_REVIEW"`, `"REJECTED"`, `"UNVERIFIED"` |
| `difficulty` (question) | `"EASY"`, `"MEDIUM"`, `"HARD"` |
| `difficulty` (mock test) | `"EASY"`, `"MEDIUM"`, `"HARD"`, `"MIXED"` |
| `language` | `"ENGLISH"`, `"HINDI"`, `"BILINGUAL"` |
| attempt `status` | `"NOT_STARTED"`, `"IN_PROGRESS"`, `"SUBMITTED"`, `"EXPIRED"` |
| PDF job `status` | `"QUEUED"`, `"PROCESSING"`, `"EXTRACTING"`, `"OCR"`, `"PARSING"`, `"VALIDATING"`, `"COMPLETED"`, `"FAILED"` |

---

## /health

### `GET /health`
**Auth:** None  
**Description:** Health check endpoint. Used by Render.

**Response 200:**
```json
{
  "status": "ok",
  "service": "rrb-alp-backend",
  "version": "1.0.0"
}
```

---

## /api/auth

### `GET /api/auth/google/login`
**Auth:** None  
**Description:** Returns the Google OAuth authorization URL. The frontend redirects the browser to this URL.

**Response 200:**
```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

---

### `GET /api/auth/google/callback`
**Auth:** None  
**Description:** Google redirects to this URL after the user grants consent. The backend exchanges the code for tokens, creates/updates the user record, and returns a JWT.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `code` | string | Yes | Authorization code from Google |
| `state` | string | No | CSRF state token |

**Response 200:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Errors:**
- `400` — Missing or invalid code
- `500` — Google token exchange failed

---

### `POST /api/auth/logout`
**Auth:** Required  
**Description:** Stateless JWT logout — invalidates no server-side state (JWTs are stateless). Frontend should discard the token.

**Response 200:**
```json
{ "message": "Logged out successfully." }
```

---

## /api/users

### `GET /api/users/me`
**Auth:** Required  
**Description:** Returns the current authenticated user's profile.

**Response 200:**
```json
{
  "id": "uuid",
  "name": "Ramabadra",
  "email": "user@example.com",
  "profile_image": "https://lh3.googleusercontent.com/...",
  "created_at": "2025-01-01T00:00:00Z",
  "last_login": "2025-09-11T15:00:00Z"
}
```

**Errors:**
- `401` — Not authenticated

---

### `PATCH /api/users/me`
**Auth:** Required  
**Description:** Update the current user's editable profile fields.

**Request Body:**
```json
{
  "name": "New Display Name"
}
```

**Response 200:** Same as `GET /api/users/me`

---

## /api/subjects

### `GET /api/subjects`
**Auth:** None  
**Description:** Returns all subjects. Used to populate subject filters.

**Response 200:**
```json
[
  {
    "id": "uuid",
    "name": "MATHEMATICS",
    "short_code": "MATH",
    "description": null,
    "display_order": 1,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `GET /api/subjects/{subject_id}`
**Auth:** None  
**Description:** Returns a single subject by UUID.

**Response 200:** Single subject object  
**Errors:** `404` — Not found

---

## /api/topics

### `GET /api/topics`
**Auth:** None  
**Description:** Returns all topics, optionally filtered by subject.

**Query Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `subject_id` | UUID | No | Filter topics by subject |

**Response 200:**
```json
[
  {
    "id": "uuid",
    "subject_id": "uuid",
    "name": "Number System",
    "display_order": 1,
    "created_at": "...",
    "updated_at": "..."
  }
]
```

---

### `GET /api/topics/{topic_id}`
**Auth:** None  
**Response 200:** Single topic object  
**Errors:** `404` — Not found

---

## /api/questions

### `GET /api/questions`
**Auth:** Required  
**Description:** Paginated, filterable question bank.

**Query Parameters:**
| Param | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `subject_id` | UUID | No | — | Filter by subject |
| `topic_id` | UUID | No | — | Filter by topic |
| `source_type` | string | No | — | `PYQ`, `AI_GENERATED`, `REFERENCE` |
| `difficulty` | string | No | — | `EASY`, `MEDIUM`, `HARD` |
| `verification_status` | string | No | — | `VERIFIED`, `NEEDS_REVIEW`, etc. |
| `source_year` | int | No | — | Filter PYQs by year |
| `page` | int | No | 1 | Page number |
| `page_size` | int | No | 20 | Max 100 |

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "question_text": "What is the SI unit of force?",
      "option_a": "Joule",
      "option_b": "Newton",
      "option_c": "Watt",
      "option_d": "Pascal",
      "correct_answer": "B",
      "explanation": "Force is measured in Newtons (N).",
      "subject_id": "uuid",
      "topic_id": "uuid",
      "subtopic": null,
      "difficulty": "EASY",
      "language": "ENGLISH",
      "source_type": "PYQ",
      "source_exam": "RRB ALP",
      "source_year": 2018,
      "verification_status": "VERIFIED",
      "extraction_confidence": 0.97,
      "created_at": "...",
      "updated_at": "..."
    }
  ],
  "total": 500,
  "page": 1,
  "page_size": 20,
  "total_pages": 25
}
```

---

### `GET /api/questions/{question_id}`
**Auth:** Required  
**Response 200:** Single full `QuestionResponse`  
**Errors:** `404` — Not found

---

### `POST /api/questions`
**Auth:** Required  
**Description:** Manually create a question (admin use / manual entry).

**Request Body:**
```json
{
  "question_text": "What is 15% of 200?",
  "option_a": "25",
  "option_b": "30",
  "option_c": "35",
  "option_d": "40",
  "correct_answer": "B",
  "explanation": "15/100 × 200 = 30",
  "subject_id": "uuid",
  "topic_id": "uuid",
  "difficulty": "EASY",
  "source_type": "REFERENCE",
  "source_year": null
}
```

**Validation Rules:**
- `source_type = "AI_GENERATED"` → `source_year` must be `null`
- `correct_answer` must be `"A"`, `"B"`, `"C"`, or `"D"`

**Response 201:** Full `QuestionResponse`  
**Errors:** `422` — Validation error

---

### `PATCH /api/questions/{question_id}`
**Auth:** Required  
**Description:** Partial update of a question (for manual review/correction).

**Request Body:** Any subset of question fields (all optional)  
**Response 200:** Updated `QuestionResponse`  
**Errors:** `404`, `422`

---

### `DELETE /api/questions/{question_id}`
**Auth:** Required  
**Response 204:** No content  
**Errors:** `404`

---

## /api/mock-tests

### `POST /api/mock-tests/generate`
**Auth:** Required  
**Description:** Generates a new mock test by selecting questions from the bank.

**Request Body:**
```json
{
  "question_count": 30,
  "subjects": ["PHYSICS", "CHEMISTRY"],
  "topics": [],
  "difficulty": "MIXED",
  "source_type": "MIXED",
  "negative_marking": 0.3333,
  "marks_per_correct": 1.0,
  "duration_minutes": 30,
  "title": "Physics + Chemistry Practice Test"
}
```

**Field Rules:**
- `question_count` must be one of: `20`, `30`, `40`, `50`, `75`
- `negative_marking` must be between `0.0` and `1.0`
- `subjects` empty → all subjects eligible
- `topics` empty → all topics eligible
- `title` auto-generated if not provided

**Response 201:**
```json
{
  "id": "uuid",
  "title": "Physics + Chemistry Practice Test",
  "user_id": "uuid",
  "question_count": 30,
  "duration_minutes": 30,
  "negative_marking": 0.3333,
  "marks_per_correct": 1.0,
  "source_type": "MIXED",
  "difficulty": "MIXED",
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:**
- `422` — Invalid question count or parameters
- `400` — Not enough questions in the bank matching filters

---

### `GET /api/mock-tests`
**Auth:** Required  
**Description:** List all mock tests created by the current user.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | 1 | — |
| `page_size` | int | 20 | — |

**Response 200:** Paginated list of `MockTestSummary`

---

### `GET /api/mock-tests/{mock_test_id}`
**Auth:** Required  
**Description:** Get a specific mock test including ordered question IDs.

**Response 200:**
```json
{
  "id": "uuid",
  "title": "...",
  "question_count": 30,
  "duration_minutes": 30,
  "negative_marking": 0.3333,
  "marks_per_correct": 1.0,
  "source_type": "MIXED",
  "difficulty": "MIXED",
  "question_ids": ["uuid1", "uuid2", "..."],
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:** `403` — Mock test belongs to another user, `404`

---

## /api/attempts

### `POST /api/attempts`
**Auth:** Required  
**Description:** Create and start a new attempt for a mock test.  
Sets `started_at` and `expires_at` server-side. Returns the attempt with timer info.

**Request Body:**
```json
{
  "mock_test_id": "uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "mock_test_id": "uuid",
  "status": "IN_PROGRESS",
  "started_at": "2025-09-11T15:00:00Z",
  "expires_at": "2025-09-11T15:30:00Z",
  "submitted_at": null,
  "auto_submitted": false,
  "created_at": "...",
  "updated_at": "..."
}
```

**Errors:**
- `404` — Mock test not found
- `409` — User already has an IN_PROGRESS attempt for this mock test

---

### `GET /api/attempts/{attempt_id}`
**Auth:** Required  
**Description:** Get the current state of an attempt. Used to reconstruct the timer after a page refresh.

**Response 200:**
```json
{
  "id": "uuid",
  "status": "IN_PROGRESS",
  "started_at": "2025-09-11T15:00:00Z",
  "expires_at": "2025-09-11T15:30:00Z",
  "seconds_remaining": 847,
  "total_questions": 30,
  "answered_count": 12,
  "marked_count": 3
}
```

> `seconds_remaining` is computed by the **backend** from `expires_at - now()`.  
> The frontend must use this value to initialise its countdown timer.

**Errors:** `403`, `404`

---

### `POST /api/attempts/{attempt_id}/answers`
**Auth:** Required  
**Description:** Save (autosave) one or more answers. Safe to call repeatedly — uses UPSERT.

**Request Body:**
```json
{
  "answers": [
    {
      "question_id": "uuid",
      "selected_answer": "B",
      "is_marked": false
    },
    {
      "question_id": "uuid",
      "selected_answer": null,
      "is_marked": true
    }
  ]
}
```

> `selected_answer: null` clears a previously selected answer.  
> `is_marked: true` flags the question for review without changing the answer.

**Response 200:**
```json
{ "message": "Answers saved.", "saved_count": 2 }
```

**Errors:**
- `403` — Attempt belongs to another user
- `404` — Attempt or question not found
- `409` — Attempt is already SUBMITTED or EXPIRED

---

### `POST /api/attempts/{attempt_id}/submit`
**Auth:** Required  
**Description:** Submit the attempt. Scores all answers. Creates the `Result` record.  
Idempotent — submitting twice returns the same result.

**Request Body:** None (empty POST)

**Response 200:**
```json
{
  "attempt_id": "uuid",
  "result_id": "uuid",
  "message": "Attempt submitted successfully."
}
```

**Errors:**
- `403` — Wrong user
- `404` — Attempt not found
- `409` — Already submitted

---

## /api/results

### `GET /api/results/{attempt_id}`
**Auth:** Required  
**Description:** Retrieve the full result for a submitted attempt.

**Response 200:**
```json
{
  "id": "uuid",
  "attempt_id": "uuid",
  "user_id": "uuid",
  "mock_test_id": "uuid",
  "total_questions": 30,
  "attempted": 27,
  "correct": 20,
  "wrong": 7,
  "unanswered": 3,
  "score": 17.67,
  "max_score": 30.0,
  "accuracy": 74.07,
  "time_spent_seconds": 1543,
  "subject_performance": {
    "PHYSICS": {
      "attempted": 15,
      "correct": 12,
      "wrong": 3,
      "unanswered": 0,
      "score": 11.0,
      "accuracy": 80.0
    }
  },
  "topic_performance": {
    "Motion": {
      "attempted": 5,
      "correct": 4,
      "wrong": 1,
      "unanswered": 0,
      "score": 3.67,
      "accuracy": 80.0
    }
  },
  "answer_details": [
    {
      "question_id": "uuid",
      "selected_answer": "B",
      "correct_answer": "C",
      "is_correct": false
    }
  ],
  "created_at": "..."
}
```

**Errors:** `403`, `404` — Attempt not found or result not computed yet

---

## /api/analytics

### `GET /api/analytics`
**Auth:** Required  
**Description:** Aggregated performance statistics across all the user's attempts.

**Response 200:**
```json
{
  "total_attempts": 12,
  "total_questions_attempted": 340,
  "total_correct": 230,
  "total_wrong": 90,
  "total_unanswered": 20,
  "average_score": 18.4,
  "best_score": 27.0,
  "latest_score": 21.0,
  "average_accuracy": 71.8,
  "score_trend": [
    { "attempt_id": "uuid", "date": "2025-09-01", "score": 15.0, "max_score": 30.0, "accuracy": 60.0 }
  ],
  "accuracy_trend": [...],
  "subject_performance": {
    "MATHEMATICS": { "attempted": 120, "correct": 88, "wrong": 25, "unanswered": 7, "accuracy": 77.9 }
  },
  "topic_performance": {
    "Percentage": { "subject_name": "MATHEMATICS", "attempted": 30, "correct": 24, "wrong": 5, "unanswered": 1, "accuracy": 82.7 }
  },
  "weak_subjects": [
    { "name": "CHEMISTRY", "accuracy": 48.0, "attempted": 40, "correct": 19, "wrong": 21 }
  ],
  "weak_topics": [
    { "name": "Magnetism", "accuracy": 33.3, "attempted": 6, "correct": 2, "wrong": 4 }
  ]
}
```

---

## /api/mistakes

### `GET /api/mistakes`
**Auth:** Required  
**Description:** List all questions in the user's mistake book.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `subject_id` | UUID | — | Filter by subject |
| `page` | int | 1 | — |
| `page_size` | int | 20 | — |

**Response 200:** Paginated list of `MistakeResponse`

---

### `POST /api/mistakes`
**Auth:** Required  
**Description:** Manually add a question to the mistake book.  
Idempotent — adding the same question twice does nothing (returns existing entry).

**Request Body:**
```json
{
  "question_id": "uuid",
  "attempt_id": "uuid",
  "note": "I always confuse this formula"
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "question_id": "uuid",
  "attempt_id": "uuid",
  "added_at": "...",
  "note": "I always confuse this formula"
}
```

**Errors:** `404` — Question not found, `409` — Already in mistake book

---

### `DELETE /api/mistakes/{mistake_id}`
**Auth:** Required  
**Response 204:** No content  
**Errors:** `403`, `404`

---

### `POST /api/mistakes/practice`
**Auth:** Required  
**Description:** Generate a mini mock test from the user's mistake book questions.

**Request Body:**
```json
{
  "question_count": 20,
  "subject_filter": ["MATHEMATICS", "PHYSICS"],
  "negative_marking": 0.3333,
  "duration_minutes": 20
}
```

**Response 201:** Same as `POST /api/mock-tests/generate` response  
**Errors:** `400` — Not enough mistake questions matching the filter

---

## /api/pdfs

### `POST /api/pdfs/upload`
**Auth:** Required  
**Description:** Upload a previous-year question paper PDF.  
The file is validated, stored in Supabase Storage, and processed asynchronously in the background.  
**This endpoint returns immediately** — do not wait for processing to complete.

**Request:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | PDF file (max 50 MB) |
| `exam_name` | string | No | e.g. "RRB ALP" |
| `exam_year` | int | No | e.g. 2018 |
| `exam_shift` | string | No | e.g. "Shift 1" |

**Validation:**
- File extension must be `.pdf`
- MIME type must be `application/pdf`
- File size must be ≤ `MAX_PDF_SIZE_MB` (50 MB default)

**Response 202:**
```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "original_filename": "RRB_ALP_2018_Set_1.pdf",
  "file_size_bytes": 2457600,
  "status": "QUEUED",
  "message": "PDF uploaded. Processing queued."
}
```

**Errors:**
- `400` — Invalid file type or size
- `413` — File too large

---

### `GET /api/pdfs`
**Auth:** Required  
**Description:** List all PDFs uploaded by the current user.

**Response 200:** Paginated list of `PdfDocumentResponse`

---

### `GET /api/pdfs/{pdf_id}`
**Auth:** Required  
**Description:** Get metadata for a specific PDF document.

**Response 200:** `PdfDocumentResponse`  
**Errors:** `403`, `404`

---

### `GET /api/pdfs/{pdf_id}/status`
**Auth:** Required  
**Description:** Poll the processing status of a PDF. Frontend should poll this every 3–5 seconds after upload until `status == "COMPLETED"` or `"FAILED"`.

**Response 200:**
```json
{
  "document_id": "uuid",
  "job_id": "uuid",
  "status": "PARSING",
  "progress_pct": 65.0,
  "current_stage": "Detecting question boundaries",
  "error_message": null,
  "questions_extracted": 47,
  "questions_stored": 0,
  "started_at": "...",
  "completed_at": null
}
```

**Terminal states:** `COMPLETED`, `FAILED`  
**Errors:** `404`

---

### `GET /api/pdfs/{pdf_id}/questions`
**Auth:** Required  
**Description:** Get the questions extracted from a specific PDF (only available after `status == "COMPLETED"`).

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `verification_status` | string | — | Filter by status |
| `page` | int | 1 | — |
| `page_size` | int | 20 | — |

**Response 200:** Paginated list of `QuestionResponse`  
**Errors:** `404`, `400` — PDF not yet processed

---

## Timer Contract

> **CRITICAL for frontend implementation:**

1. When `POST /api/attempts` is called, the backend sets:
   - `started_at = UTC now()`
   - `expires_at = started_at + duration_minutes × 60`

2. `GET /api/attempts/{id}` returns `seconds_remaining = max(0, (expires_at - now()).seconds)`

3. The frontend **must** initialise its countdown timer from `seconds_remaining`, NOT from its own clock.

4. If the user refreshes the page, call `GET /api/attempts/{id}` again and re-sync the timer.

5. After `expires_at`, the backend auto-expires the attempt on the next request. The attempt status becomes `EXPIRED` and scoring runs.

6. The frontend should call `POST /api/attempts/{id}/submit` proactively before `seconds_remaining` reaches 0 for the cleanest UX.

---

## Scoring Contract

Score formula for a submitted attempt:

```
score = (correct × marks_per_correct) - (wrong × negative_marking × marks_per_correct)
accuracy = (correct / attempted) × 100   [if attempted > 0, else 0]
max_score = total_questions × marks_per_correct
```

Default values: `marks_per_correct = 1.0`, `negative_marking = 0.3333`

**The backend is the only authoritative scoring source. The frontend must never compute the final score locally.**

---

## AI-Generated Question Contract

> **These rules are enforced by the backend. The frontend should NOT display source information differently.**

| Field | Rule |
|-------|------|
| `source_type` | Always `"AI_GENERATED"` |
| `source_year` | Always `null` — never populated |
| `source_exam` | Always `null` |
| `verification_status` | `"NEEDS_REVIEW"` until manually verified |

AI-generated questions must **never** be presented to the user as official PYQs.

---

## Frontend Integration Checklist

- [ ] Store JWT in `httpOnly` cookie or secure memory (not `localStorage`)
- [ ] Send `Authorization: Bearer <token>` on all protected requests
- [ ] Reconstruct timer from `expires_at` / `seconds_remaining` (not client clock)
- [ ] Poll `GET /api/pdfs/{id}/status` every 3–5 seconds after upload
- [ ] Never trust client-side score calculation
- [ ] Handle `401` responses by redirecting to login
- [ ] Handle `403` responses by showing "Access Denied"
- [ ] Handle `409` (attempt already exists) gracefully by resuming the existing attempt

---

*Last updated: Phase 1 — Architecture, Database, API Contract*  
*This document is the single source of truth between the backend and frontend projects.*
