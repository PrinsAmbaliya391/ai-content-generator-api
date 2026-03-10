# Quillify — AI Content Generation Platform
## Backend API Documentation

---

> **Quillify** is an intelligent, AI-powered content generation platform that enables users to produce high-quality written content from documents using Retrieval-Augmented Generation (RAG). It provides rich content lifecycle management — generate, refine, manually edit, and regenerate — all backed by a tone-aware ML model that continuously curates a training dataset for improved quality. Real-time AI chat support is available via WebSocket for both general and system-specific queries.

---

## Table of Contents
- [Tech Stack](#tech-stack)
- [Architecture Overview](#architecture-overview)
- [Authentication](#authentication)
- [Content Generation](#content-generation)
- [Real-Time Chat](#real-time-chat)
- [Database Schema](#database-schema)
- [Security Model](#security-model)
- [Error Reference](#error-reference)

---

## Tech Stack

| Layer          | Technology                              |
|----------------|-----------------------------------------|
| Framework      | FastAPI (Python)                        |
| Database       | Supabase (PostgreSQL)                   |
| AI Model       | Google Gemini (gemini-3.1-flash-lite-preview) |
| Auth           | JWT (access + refresh tokens) + OTP (Email) |
| Password Hash  | bcrypt via `passlib`                    |
| Vector Search  | ChromaDB + LangChain (for RAG)          |
| Embeddings     | Google Gemini Embedding (`gemini-embedding-001`) |
| Tone Detection | Scikit-learn (pickled ML pipeline)     |
| Logging        | Loguru with business-logic filtering   |

---

## Architecture Overview

```
Client
  │
  ├── REST API  ──►  FastAPI Router
  │                     ├── /auth        ─► AuthService    ─► Supabase (users)
  │                     ├── /content     ─► ContentService ─► Supabase (generations, generation_contents)
  │                     │                                  ─► Gemini AI
  │                     │                                  ─► ChromaDB (RAG)
  │                     │                                  ─► ML Tone Model
  │
  └── WebSocket ──►  /chat               ─► ChatService    ─► Supabase (chat)
                                                           ─► Gemini AI
```

All requests pass through `BusinessLogicLoggerMiddleware` which:
- Extracts the user identity (UUID from JWT or email from body)
- Logs structured request/response data to `logs/activity.log`
- Suppresses raw Uvicorn access logs

---

## Authentication

**Base URL:** `/auth`
**Auth Required:** ❌ (all auth endpoints are public)

---

### `POST /auth/signup`

Registers a new user. Validates password strength, sends an OTP email, and stores a bcrypt-hashed password.

**Request Body:**
```json
{
  "username": "john_doe",
  "email": "john@example.com",
  "password": "Secure@123"
}
```

**Success Response `200`:**
```json
{
  "message": "OTP sent to john@example.com"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `400`  | `"john@example.com already exists"` |
| `400`  | `"Password too weak"` (fails strength validation) |
| `500`  | `"Failed to send verification email"` |

---

### `POST /auth/verify-otp`

Verifies the email OTP sent after signup. Activates the user account upon success.

**Request Body:**
```json
{
  "email": "john@example.com",
  "otp": "483921"
}
```

**Success Response `200`:**
```json
{
  "message": "Verification successful"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"User not found"` |
| `400`  | `"Invalid OTP"` |

---

### `POST /auth/login`

Validates user credentials (bcrypt password check). If valid, sends a login OTP to the user's email for 2-factor verification.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "Secure@123"
}
```

**Success Response `200`:**
```json
{
  "message": "OTP sent to john@example.com"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `401`  | `"Invalid email or password"` |
| `403`  | `"Please verify your email first"` |

---

### `POST /auth/verify-login-otp`

Completes the 2-factor login by verifying the login OTP. Returns both an access token and a refresh token on success.

**Request Body:**
```json
{
  "email": "john@example.com",
  "otp": "739201"
}
```

**Success Response `200`:**
```json
{
  "access_token": "<JWT_ACCESS_TOKEN>",
  "refresh_token": "<JWT_REFRESH_TOKEN>",
  "token_type": "bearer"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"User not found"` |
| `400`  | `"Invalid OTP"` |

> **Token Usage:** Include the access token in all protected requests as:
> `Authorization: Bearer <access_token>`

---

### `PUT /auth/change-password`

Changes the password for a user. Verifies the old password before updating to a newly hashed version.

**Request Body:**
```json
{
  "email": "john@example.com",
  "old_password": "Secure@123",
  "new_password": "NewSecure@456"
}
```

**Success Response `200`:**
```json
{
  "message": "Password updated successfully"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"User not found"` |
| `401`  | `"Incorrect old password"` |

---

## Content Generation

**Base URL:** `/content`
**Auth Required:** ✅ Bearer JWT Token

---

### `POST /content/generate`

The primary endpoint of Quillify. Accepts a document file and a topic, then uses **RAG (Retrieval-Augmented Generation)** to produce AI-written content grounded in the document's information.

This endpoint:
1. Extracts text from the uploaded file (PDF, DOCX, TXT).
2. Builds a ChromaDB vector store and performs semantic similarity search.
3. Validates that the document context is sufficient to answer the topic.
4. Generates content using Gemini AI with strict tone control.
5. Runs a tone-detection ML model on the output.
6. If the tone doesn't match, queues a background dataset curation task for model improvement.
7. Saves metadata to `generations` table and content to `generation_contents` table.

**Request:** `multipart/form-data`

| Field        | Type    | Required | Description                           |
|--------------|---------|----------|---------------------------------------|
| `topic`      | string  | ✅       | The question or topic to write about  |
| `word_count` | integer | ✅       | Target word count for the output      |
| `tone`       | string  | ✅       | Desired tone (e.g. `"formal"`, `"persuasive"`, `"casual"`) |
| `language`   | string  | ✅       | Output language (e.g. `"english"`)    |
| `file`       | file    | ✅       | Source document (PDF / DOCX / TXT)    |

**Success Response `200`:**
```json
{
  "id": 42,
  "generations_uuid": "6768a44c-cf9e-49ea-a1ca-5445d3a189ad",
  "generated_text": "artificial intelligence is fundamentally transforming ...",
  "user_tone": "formal",
  "model_tone": "formal"
}
```

> **Important:** Save `generations_uuid` — it is the identifier for all subsequent update, refine, regenerate, and delete operations.

**Error Responses:**
| Status | Detail |
|--------|--------|
| `401`  | `"Verify email first"` |
| `400`  | `"Document required."` |
| `404`  | `"Document context insufficient."` |
| `500`  | `"AI Service Error"` |
| `500`  | `"Failed to save generation metadata"` |

---

### `GET /content/history`

Returns the complete generation history for the authenticated user, including all content versions (generate, update, refine, regenerate) for each generation.

**Headers:** `Authorization: Bearer <token>`

**Success Response `200`:**
```json
{
  "history": [
    {
      "id": 42,
      "generations_uuid": "6768a44c-cf9e-49ea-a1ca-5445d3a189ad",
      "user_uuid": "c128ba7a-e2d0-44c4-99c4-cf01a07e38a5",
      "topic": "Impact of AI on Healthcare",
      "word_count": 500,
      "tone": "formal",
      "language": "english",
      "created_at": "2026-03-10T11:08:00.000Z",
      "updated_at": "2026-03-10T11:12:00.000Z",
      "content": [
        "artificial intelligence is fundamentally...",
        "AI is fundamentally transforming healthcare...",
        "refined and improved version..."
      ],
      "status": [
        "generate",
        "update",
        "refine"
      ]
    }
  ]
}
```

---

### `POST /content/update`

Saves a manually edited version of the content. Appends the new text as a new versioned entry under the generation, preserving history.

**Request Body:**
```json
{
  "generations_uuid": "6768a44c-cf9e-49ea-a1ca-5445d3a189ad",
  "updated_text": "Artificial intelligence is fundamentally transforming healthcare..."
}
```

**Success Response `200`:**
```json
{
  "status": "update"
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"Generation not found"` |

---

### `POST /content/refine`

Uses AI to refine the latest version of the content based on user feedback. The refined output is saved as a new versioned entry.

**Request Body:**
```json
{
  "generations_uuid": "6768a44c-cf9e-49ea-a1ca-5445d3a189ad",
  "user_change": "Make the introduction more impactful",
  "disliked_part": "work faster"
}
```

**Success Response `200`:**
```json
{
  "updated_text": "the revolution in artificial intelligence is reshaping..."
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"Generation not found"` |

---

### `POST /content/regenerate`

Generates a completely new version of the content for the same topic, tone, and word count. Saves the new version as a new entry in history.

**Request Body:**
```json
{
  "generations_uuid": "6768a44c-cf9e-49ea-a1ca-5445d3a189ad"
}
```

**Success Response `200`:**
```json
{
  "updated_text": "a new, fully rewritten version of the content..."
}
```

**Error Responses:**
| Status | Detail |
|--------|--------|
| `404`  | `"Generation not found"` |

---

### `DELETE /content/delete/{generations_uuid}`

Permanently deletes a generation record. Due to the `ON DELETE CASCADE` constraint in the database, all associated content versions in `generation_contents` are also deleted automatically.

**URL Parameter:** `generations_uuid` (string, UUID)

**Example:** `DELETE /content/delete/6768a44c-cf9e-49ea-a1ca-5445d3a189ad`

**Success Response `200`:**
```json
{
  "message": "deleted"
}
```

---

## Real-Time Chat

**Base URL:** `/chat`
**Connection Type:** WebSocket
**Auth Required:** ✅ `Authorization: Bearer <token>` header on connection

> All chat endpoints use WebSocket. Connect using `ws://` or `wss://`. Send the JWT in the `Authorization` header when establishing the connection.

---

### `WS /chat/ws`

General-purpose AI chat. The AI maintains session history and can answer any question.

**Message Format:** Plain text string

**Send:**
```
"What are the benefits of machine learning in finance?"
```

**Receive:**
```
"Machine learning in finance provides several key benefits: fraud detection using anomaly detection models..."
```

> A new `session_id` (UUID) is created for each connection. The full conversation is stored in the `chat` table under this session.

---

### `WS /chat/system`

System-support chat. The AI is strictly constrained to answer only questions about Quillify's features (content generation, tone selection, language, word count, history management, etc.). Off-topic questions receive a standard refusal response.

**Send:**
```
"How do I change the tone of my generated content?"
```

**Receive:**
```
"Use the /content/refine endpoint with your desired tone change in the user_change field."
```

---

### `WS /chat/continue/{session_id}`

Resumes an existing chat session using its `session_id`. The full conversation history is reloaded as context for the AI.

**URL Path Parameter:** `session_id` (string, UUID)

**Send:** `"Continue from where we left off"`

**Receive:** AI response with full prior context.

**Error (if session not found):** Returns `"session not found"` and closes the socket.

---

### `WS /chat/delete/{session_id}`

Deletes a specific chat session record from the database.

**URL Path Parameter:** `session_id` (string, UUID)

**Receive (success):** `"chat deleted successfully"` and connection closes.
**Receive (not found):** `"session not found"` and connection closes.

---

## Database Schema

### `users`
| Column       | Type        | Notes                              |
|--------------|-------------|------------------------------------|
| `uuid`       | UUID (PK)   | Auto-generated primary key         |
| `email`      | text        | Unique, required                   |
| `username`   | text        | Display name                       |
| `password`   | text        | bcrypt hashed                      |
| `otp`        | text        | Temporary OTP value                |
| `is_verified`| boolean     | `false` until OTP verified         |
| `created_at` | timestamptz | Auto-set on insert                 |
| `updated_at` | timestamptz | Auto-updated via trigger           |

---

### `generations`
| Column            | Type        | Notes                              |
|-------------------|-------------|------------------------------------|
| `id`              | bigint (PK) | Auto-incrementing identity         |
| `generations_uuid`| UUID (UQ)   | Unique external identifier         |
| `user_uuid`       | UUID (FK)   | References `users.uuid` (CASCADE)  |
| `topic`           | text        | Content topic/question             |
| `word_count`      | integer     | Requested word count               |
| `tone`            | text        | Requested tone                     |
| `language`        | text        | Output language                    |
| `created_at`      | timestamptz | Auto-set on insert                 |
| `updated_at`      | timestamptz | Auto-updated via trigger           |

---

### `generation_contents`
| Column            | Type        | Notes                                        |
|-------------------|-------------|----------------------------------------------|
| `id`              | bigint (PK) | Auto-incrementing identity                   |
| `generations_uuid`| UUID (FK)   | References `generations.generations_uuid` (CASCADE) |
| `content`         | text        | The actual written content                   |
| `status`          | text        | `generate` / `update` / `refine` / `regenerate` |
| `created_at`      | timestamptz | Auto-set on insert                           |

---

### `chat`
| Column     | Type     | Notes                                 |
|------------|----------|---------------------------------------|
| `id`       | bigint   | Auto-incrementing                     |
| `user_uuid`| UUID     | References `users.uuid`               |
| `session`  | text     | UUID string for the chat session      |
| `chat`     | JSONB    | Array of `{role, content, time}` objects |
| `status`   | text     | `generate_content` or `system_content`|

---

## Security Model

| Feature | Implementation |
|---|---|
| Password Storage | bcrypt via `passlib[bcrypt]` |
| Authentication | JWT with `access` and `refresh` token types |
| Email Verification | OTP sent via SMTP on signup and login (2FA) |
| Route Protection | `Depends(get_current_user)` extracts UUID from JWT |
| Content Ownership | All queries check `user_uuid` before operating |
| Generation Isolation | All operations validate `generations_uuid` + `user_uuid` together |

---

## Error Reference

| HTTP Status | Meaning |
|---|---|
| `400` | Bad request / validation failure / email conflict |
| `401` | Unauthenticated or invalid credentials |
| `403` | Authenticated but not permitted (e.g. email not verified) |
| `404` | Resource not found |
| `422` | Pydantic schema validation failure (missing/wrong field) |
| `500` | Server-side or AI service error |

---

*Built with ❤️ using FastAPI, Supabase, and Google Gemini.*
