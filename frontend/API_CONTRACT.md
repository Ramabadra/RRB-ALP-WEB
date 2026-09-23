# RRB ALP Mock Test Platform API Contract

This document outlines the REST API contract between the Next.js frontend and the FastAPI backend.

## Base URL
The backend is expected to be reachable at the URL defined by the `NEXT_PUBLIC_API_URL` environment variable.

## Authentication
All protected routes must include a Bearer token in the Authorization header:
`Authorization: Bearer <token>`

---

### AUTHENTICATION

#### 1. Google Login / Signup
- **Method**: `POST`
- **Endpoint**: `/api/auth/google`
- **Auth Required**: No
- **Request**:
  ```json
  {
    "token": "string (Google OAuth JWT token)"
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "user": {
      "id": "string",
      "name": "string",
      "email": "string",
      "avatarUrl": "string?"
    },
    "token": "string (JWT)"
  }
  ```
- **Errors**: `400 Bad Request` (Invalid token), `401 Unauthorized`

#### 2. Get Current User
- **Method**: `GET`
- **Endpoint**: `/api/users/me`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "id": "string",
    "name": "string",
    "email": "string",
    "avatarUrl": "string?"
  }
  ```
- **Errors**: `401 Unauthorized`

---

### PDF PROCESSING

#### 1. Upload PDF
- **Method**: `POST`
- **Endpoint**: `/api/pdfs/upload`
- **Auth Required**: Yes
- **Request**: `multipart/form-data`
  - `file`: PDF File
- **Response**: `202 Accepted`
  ```json
  {
    "jobId": "string",
    "status": "QUEUED | PARSING | COMPLETED | FAILED"
  }
  ```
- **Errors**: `400 Bad Request` (Invalid file), `413 Payload Too Large`

#### 2. List PDFs
- **Method**: `GET`
- **Endpoint**: `/api/pdfs`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "filename": "string",
      "uploadedAt": "string (ISO Date)",
      "status": "COMPLETED",
      "questionCount": 100
    }
  ]
  ```

#### 3. Get PDF Details
- **Method**: `GET`
- **Endpoint**: `/api/pdfs/{id}`
- **Auth Required**: Yes
- **Response**: `200 OK` (Similar to List response)

#### 4. Get PDF Processing Status
- **Method**: `GET`
- **Endpoint**: `/api/pdfs/{id}/status`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "jobId": "string",
    "status": "QUEUED | PARSING | COMPLETED | FAILED",
    "progress": 50,
    "error": "string?"
  }
  ```

---

### QUESTIONS

#### 1. List Questions
- **Method**: `GET`
- **Endpoint**: `/api/questions`
- **Auth Required**: Yes
- **Query Params**: `subjectId?`, `topicId?`, `difficulty?`
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "text": "string",
      "options": [
        { "id": "string", "text": "string" }
      ],
      "correctOptionId": "string",
      "explanation": "string?",
      "subjectId": "string",
      "topicId": "string",
      "difficulty": "EASY | MEDIUM | HARD",
      "pdfSourceId": "string?"
    }
  ]
  ```

#### 2. Get Question
- **Method**: `GET`
- **Endpoint**: `/api/questions/{id}`
- **Auth Required**: Yes
- **Response**: `200 OK` (Single Question Object)
- **Errors**: `404 Not Found`

---

### SUBJECTS & TOPICS

#### 1. List Subjects
- **Method**: `GET`
- **Endpoint**: `/api/subjects`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "name": "string",
      "code": "string?"
    }
  ]
  ```

#### 2. List Topics
- **Method**: `GET`
- **Endpoint**: `/api/topics`
- **Auth Required**: Yes
- **Query Params**: `subjectId?`
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "subjectId": "string",
      "name": "string"
    }
  ]
  ```

---

### MOCK TESTS

#### 1. Generate Mock Test
- **Method**: `POST`
- **Endpoint**: `/api/mock-tests/generate`
- **Auth Required**: Yes
- **Request**:
  ```json
  {
    "subjectWeights": {
      "subjectId": 25,
      "subjectId2": 75
    },
    "totalQuestions": 75,
    "durationMinutes": 60,
    "difficulty": "MEDIUM"
  }
  ```
- **Response**: `201 Created`
  ```json
  {
    "id": "string",
    "title": "string",
    "durationMinutes": 60,
    "totalQuestions": 75,
    "createdAt": "string (ISO Date)"
  }
  ```

#### 2. List Mock Tests
- **Method**: `GET`
- **Endpoint**: `/api/mock-tests`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "title": "string",
      "durationMinutes": 60,
      "totalQuestions": 75,
      "createdAt": "string (ISO Date)",
      "isCompleted": false
    }
  ]
  ```

#### 3. Get Mock Test
- **Method**: `GET`
- **Endpoint**: `/api/mock-tests/{id}`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "test": {
      "id": "string",
      "title": "string",
      "durationMinutes": 60,
      "totalQuestions": 75
    },
    "questions": [
      {
         // Question object without correctOptionId and explanation
         "id": "string",
         "text": "string",
         "options": [
           { "id": "string", "text": "string" }
         ]
      }
    ]
  }
  ```

---

### ATTEMPTS

#### 1. Start/Resume Attempt
- **Method**: `POST`
- **Endpoint**: `/api/attempts`
- **Auth Required**: Yes
- **Request**:
  ```json
  {
    "testId": "string"
  }
  ```
- **Response**: `200 OK` (or `201 Created` if new)
  ```json
  {
    "id": "string",
    "testId": "string",
    "startTime": "string (ISO Date)",
    "status": "IN_PROGRESS",
    "answers": {
      "questionId": "optionId"
    }
  }
  ```

#### 2. Get Attempt
- **Method**: `GET`
- **Endpoint**: `/api/attempts/{id}`
- **Auth Required**: Yes
- **Response**: `200 OK` (Same as Start Attempt response)

#### 3. Save Answers (Autosave)
- **Method**: `POST`
- **Endpoint**: `/api/attempts/{id}/answers`
- **Auth Required**: Yes
- **Request**:
  ```json
  {
    "answers": {
      "questionId": "optionId"
    }
  }
  ```
- **Response**: `200 OK`
  ```json
  {
    "success": true
  }
  ```

#### 4. Submit Attempt
- **Method**: `POST`
- **Endpoint**: `/api/attempts/{id}/submit`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "success": true,
    "resultId": "string"
  }
  ```

---

### RESULTS

#### 1. Get Result
- **Method**: `GET`
- **Endpoint**: `/api/results/{attemptId}`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "id": "string",
    "attemptId": "string",
    "score": 45.5,
    "totalQuestions": 75,
    "attempted": 60,
    "correct": 50,
    "incorrect": 10,
    "accuracy": 83.3,
    "subjectPerformance": [
      {
        "subjectId": "string",
        "subjectName": "string",
        "score": 15.0,
        "total": 25,
        "correct": 16,
        "incorrect": 3
      }
    ]
  }
  ```

---

### ANALYTICS

#### 1. Get User Analytics
- **Method**: `GET`
- **Endpoint**: `/api/analytics`
- **Auth Required**: Yes
- **Response**: `200 OK`
  ```json
  {
    "totalTestsTaken": 12,
    "averageScore": 65.4,
    "averageAccuracy": 78.2,
    "scoreHistory": [
      {
        "date": "2024-03-01",
        "score": 55,
        "testId": "string"
      }
    ],
    "subjectStrengths": [
      {
        "subjectName": "Mathematics",
        "accuracy": 85.0
      }
    ]
  }
  ```

---

### MISTAKES (Mistake Book)

#### 1. List Mistakes
- **Method**: `GET`
- **Endpoint**: `/api/mistakes`
- **Auth Required**: Yes
- **Query Params**: `subjectId?`
- **Response**: `200 OK`
  ```json
  [
    {
      "id": "string",
      "questionId": "string",
      "question": {
         "text": "string",
         "options": [],
         "correctOptionId": "string",
         "explanation": "string?"
      },
      "userAnswerId": "string?",
      "addedAt": "string (ISO Date)",
      "notes": "string?"
    }
  ]
  ```

#### 2. Add Mistake
- **Method**: `POST`
- **Endpoint**: `/api/mistakes`
- **Auth Required**: Yes
- **Request**:
  ```json
  {
    "questionId": "string",
    "userAnswerId": "string?",
    "notes": "string?"
  }
  ```
- **Response**: `201 Created`

#### 3. Remove Mistake
- **Method**: `DELETE`
- **Endpoint**: `/api/mistakes/{id}`
- **Auth Required**: Yes
- **Response**: `204 No Content`
