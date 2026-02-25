# Technical Design Doc: Auth, Chat Persistence & Portfolio

> **Status:** Draft
> **Date:** 2025-02-25
> **Authors:** Michael, Alex
> **Branch:** `frontend` (frontend changes), `backend` (API + DB changes)

---

## 1. Overview

This document covers three new features for StockRAG:

1. **User Authentication** — Sign up / login via [Clerk](https://clerk.com)
2. **Chat Persistence** — Store and retrieve per-user chat sessions
3. **Portfolio** — Users save stock recommendation cards to a personal portfolio

All three features require new database tables, backend API endpoints, and frontend integration.

---

## 2. High-Level Architecture

```mermaid
graph TB
    subgraph Frontend ["Frontend (React + Mantine)"]
        ClerkUI["Clerk Components<br/>&lt;SignIn/&gt; &lt;SignUp/&gt; &lt;UserButton/&gt;"]
        ChatUI["Chat UI"]
        PortfolioUI["Portfolio UI"]
    end

    subgraph Auth ["Auth Layer"]
        ClerkSDK["Clerk SDK<br/>(Frontend: @clerk/clerk-react)<br/>(Backend: clerk-backend-api)"]
    end

    subgraph Backend ["Backend (FastAPI)"]
        AuthMW["Auth Middleware<br/>(verify Clerk JWT)"]
        ChatAPI["Chat Endpoints"]
        PortfolioAPI["Portfolio Endpoints"]
        RAG["RAG Pipeline<br/>(existing)"]
    end

    subgraph DB ["Database (PostgreSQL)"]
        UsersRef["users (Clerk-managed, ID reference only)"]
        ChatsTable["chats"]
        MessagesTable["chat_messages"]
        PortfolioTable["portfolio_items"]
    end

    ClerkUI --> ClerkSDK
    ChatUI --> AuthMW
    PortfolioUI --> AuthMW
    AuthMW --> ChatAPI
    AuthMW --> PortfolioAPI
    ChatAPI --> RAG
    ChatAPI --> ChatsTable
    ChatAPI --> MessagesTable
    PortfolioAPI --> PortfolioTable
```

---

## 3. Authentication — Clerk

### 3.1 Why Clerk?

- Free tier covers dev usage
- Handles sign-up, login, OAuth, email verification, session management
- Provides React components (`<SignIn/>`, `<SignUp/>`, `<UserButton/>`) — drop-in UI
- Provides a JWT that the backend can verify without managing sessions ourselves

### 3.2 Frontend Integration

**Install:**
```bash
npm install @clerk/clerk-react
```

**Wrap the app:**
```tsx
// main.tsx
import { ClerkProvider } from '@clerk/clerk-react';

const CLERK_PUBLISHABLE_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;

<ClerkProvider publishableKey={CLERK_PUBLISHABLE_KEY}>
  <App />
</ClerkProvider>
```

**Protect routes / show auth UI:**
```tsx
import { SignedIn, SignedOut, SignIn, UserButton } from '@clerk/clerk-react';

// In App.tsx or a layout component:
<SignedOut>
  <SignIn />
</SignedOut>
<SignedIn>
  {/* existing app content */}
  <UserButton />  {/* avatar dropdown in AppHeader */}
</SignedIn>
```

**Attach JWT to API calls:**
```tsx
import { useAuth } from '@clerk/clerk-react';

const { getToken } = useAuth();
const token = await getToken();

// Add to axios instance
apiClient.interceptors.request.use(async (config) => {
  const token = await getToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
```

### 3.3 Backend Integration

**Verify the Clerk JWT in FastAPI middleware:**

```python
# middleware/auth.py
from fastapi import Request, HTTPException
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=os.getenv("CLERK_SECRET_KEY"))

async def get_current_user(request: Request) -> str:
    """Extract and verify Clerk user ID from JWT."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing auth token")

    token = auth_header.split(" ")[1]
    # Verify JWT with Clerk's JWKS
    # Returns the Clerk user_id (e.g., "user_2x...")
    payload = verify_clerk_jwt(token)
    return payload["sub"]
```

> **Note:** Clerk user IDs (e.g., `user_2xABC123`) are strings. We reference these directly in our DB — no local `users` table needed.

### 3.4 Auth Flow

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant C as Clerk
    participant F as Frontend
    participant B as Backend (FastAPI)

    U->>C: Sign up / Sign in
    C-->>F: Session + JWT
    F->>B: API request + Bearer JWT
    B->>C: Verify JWT (JWKS)
    C-->>B: Valid → user_id
    B-->>F: Response (scoped to user)
```

---

## 4. Chat Persistence

### 4.1 Data Model

A **chat** is a conversation session. Each chat contains multiple **messages** (user + assistant turns).

```mermaid
erDiagram
    CHATS {
        uuid id PK
        string clerk_user_id "Clerk user ID (e.g. user_2x...)"
        string title "Auto-generated from first message"
        timestamp created_at
        timestamp updated_at
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid chat_id FK
        string role "user | assistant"
        text user_text "User's message (if role=user)"
        text assistant_text "Assistant's text response (if role=assistant)"
        jsonb stocks "Array of StockProfile objects (if role=assistant)"
        string status "sending | sent | error"
        timestamp created_at
    }

    CHATS ||--o{ CHAT_MESSAGES : contains
```

**Key decisions:**
- `stocks` is stored as `JSONB` — matches the `StockProfile[]` from the frontend types. This avoids a complex relational join for what is essentially a blob of recommendation data per message.
- `clerk_user_id` is a string, not a FK to a local users table — Clerk owns user management.
- `title` is auto-set from the first user message (truncated to ~80 chars). Can be updated later.

### 4.2 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/chats` | List all chats for current user | Yes |
| `POST` | `/api/chats` | Create a new chat session | Yes |
| `GET` | `/api/chats/{chat_id}` | Get a chat with all its messages | Yes |
| `POST` | `/api/chats/{chat_id}/messages` | Add a message to a chat (triggers RAG if user msg) | Yes |
| `DELETE` | `/api/chats/{chat_id}` | Delete a chat and its messages | Yes |

#### Request/Response Schemas

**`GET /api/chats`** — List chats
```json
{
  "chats": [
    {
      "id": "uuid",
      "title": "EV car companies",
      "created_at": "2025-02-25T10:00:00Z",
      "updated_at": "2025-02-25T10:05:00Z",
      "message_count": 4
    }
  ]
}
```

**`POST /api/chats`** — Create chat
```json
// Request
{ "title": "optional title" }

// Response
{
  "id": "uuid",
  "title": "New Chat",
  "created_at": "2025-02-25T10:00:00Z"
}
```

**`GET /api/chats/{chat_id}`** — Get chat with messages
```json
{
  "id": "uuid",
  "title": "EV car companies",
  "messages": [
    {
      "id": "uuid",
      "role": "user",
      "user_text": "Show me EV companies",
      "created_at": "2025-02-25T10:00:00Z"
    },
    {
      "id": "uuid",
      "role": "assistant",
      "assistant_text": "Here are some top EV companies...",
      "stocks": [ { "ticker": "TSLA", "companyName": "Tesla", ... } ],
      "created_at": "2025-02-25T10:00:01Z"
    }
  ]
}
```

**`POST /api/chats/{chat_id}/messages`** — Send a message
```json
// Request
{ "text": "Show me EV companies" }

// Response — returns the assistant's reply
{
  "user_message": { "id": "uuid", "role": "user", "user_text": "...", ... },
  "assistant_message": { "id": "uuid", "role": "assistant", "assistant_text": "...", "stocks": [...], ... }
}
```

### 4.3 Frontend Changes

```mermaid
graph LR
    subgraph Sidebar
        ChatList["Chat List<br/>(GET /api/chats)"]
        NewChatBtn["+ New Chat"]
    end

    subgraph MainArea
        ChatView["Chat View<br/>(GET /api/chats/:id)"]
        Input["ChatInput<br/>(POST /api/chats/:id/messages)"]
    end

    ChatList -->|select| ChatView
    NewChatBtn -->|POST /api/chats| ChatView
    Input -->|send| ChatView
```

- Add a **sidebar** to `MainLayout` listing past chats
- Refactor `useChat` hook to:
  - Accept a `chatId` parameter
  - Load messages from API on mount (`GET /api/chats/{id}`)
  - Send messages via `POST /api/chats/{id}/messages` instead of direct RAG call
  - Auto-create a new chat on first message if no `chatId` is set
- The `ChatMessage` type on the frontend already has `id`, `role`, `text`, `content.stocks` — maps cleanly to the DB schema

---

## 5. Portfolio

### 5.1 Concept

Users can "save" a stock card from a chat recommendation to their **portfolio**. The portfolio item stores the exact same data as a `StockProfile` card, so it renders using the existing `StockCard` component.

### 5.2 Data Model

```mermaid
erDiagram
    PORTFOLIO_ITEMS {
        uuid id PK
        string clerk_user_id "Clerk user ID"
        string ticker "e.g. TSLA"
        string company_name
        string exchange "NASDAQ, NYSE, etc."
        int match_percent "0-100"
        string sector
        string industry
        string market_cap "formatted string"
        int employees
        int founded
        string pe_ratio
        string why_fits
        string details_url
        text notes "Optional user notes"
        uuid source_chat_id FK "Which chat it came from (nullable)"
        uuid source_message_id FK "Which message it came from (nullable)"
        timestamp added_at
    }
```

**Key decisions:**
- Schema mirrors `StockProfile` from `src/api/types.ts` exactly — the portfolio card IS a stock card
- `notes` lets users annotate why they saved it
- `source_chat_id` / `source_message_id` provide traceability back to the original recommendation
- We store a snapshot of the data at save-time (denormalized) so it doesn't change if the stock data updates

### 5.3 API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/api/portfolio` | Get all portfolio items for current user | Yes |
| `GET` | `/api/portfolio/{item_id}` | Get a specific portfolio item | Yes |
| `POST` | `/api/portfolio` | Add a stock to portfolio | Yes |
| `DELETE` | `/api/portfolio/{item_id}` | Remove a stock from portfolio | Yes |

#### Request/Response Schemas

**`GET /api/portfolio`**
```json
{
  "items": [
    {
      "id": "uuid",
      "ticker": "TSLA",
      "companyName": "Tesla, Inc.",
      "exchange": "NASDAQ",
      "matchPercent": 92,
      "sector": "Consumer Cyclical",
      "industry": "Auto Manufacturers",
      "marketCap": "$780B",
      "employees": 140000,
      "founded": 2003,
      "peRatio": "68.4",
      "whyFits": "Market leader in EV...",
      "detailsUrl": "https://finance.yahoo.com/quote/TSLA",
      "notes": "Love this one",
      "sourceChatId": "uuid-or-null",
      "addedAt": "2025-02-25T10:00:00Z"
    }
  ]
}
```

**`POST /api/portfolio`**
```json
// Request — essentially a StockProfile + optional notes
{
  "ticker": "TSLA",
  "companyName": "Tesla, Inc.",
  "exchange": "NASDAQ",
  "matchPercent": 92,
  "sector": "Consumer Cyclical",
  "industry": "Auto Manufacturers",
  "marketCap": "$780B",
  "employees": 140000,
  "founded": 2003,
  "peRatio": "68.4",
  "whyFits": "Market leader in EV...",
  "detailsUrl": "https://finance.yahoo.com/quote/TSLA",
  "notes": "Adding for long-term watch",
  "sourceChatId": "uuid-or-null",
  "sourceMessageId": "uuid-or-null"
}

// Response
{ "id": "uuid", "addedAt": "2025-02-25T10:00:00Z", ...rest of fields }
```

### 5.4 Frontend Changes

- Add a **"Save to Portfolio"** button on each `StockCard` in chat results
- Add a **Portfolio page/tab** accessible from the header or sidebar
- Portfolio page renders the same `StockCard` components (reuse existing component)
- New hook: `usePortfolio()` — fetches/manages portfolio state
- Add navigation (React Router or simple tab state) to switch between Chat and Portfolio views

---

## 6. Database Design (PostgreSQL)

### 6.1 SQL Schema

```sql
-- No local users table — we use Clerk's user_id (string) directly

-- Chat sessions
CREATE TABLE chats (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id TEXT NOT NULL,
    title         TEXT NOT NULL DEFAULT 'New Chat',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chats_user ON chats(clerk_user_id);

-- Chat messages
CREATE TABLE chat_messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    chat_id         UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    user_text       TEXT,
    assistant_text  TEXT,
    stocks          JSONB,
    status          TEXT DEFAULT 'sent' CHECK (status IN ('sending', 'sent', 'error')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_messages_chat ON chat_messages(chat_id);

-- Portfolio items
CREATE TABLE portfolio_items (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clerk_user_id     TEXT NOT NULL,
    ticker            TEXT NOT NULL,
    company_name      TEXT NOT NULL,
    exchange          TEXT,
    match_percent     INTEGER,
    sector            TEXT,
    industry          TEXT,
    market_cap        TEXT,
    employees         INTEGER,
    founded           INTEGER,
    pe_ratio          TEXT,
    why_fits          TEXT,
    details_url       TEXT,
    notes             TEXT,
    source_chat_id    UUID REFERENCES chats(id) ON DELETE SET NULL,
    source_message_id UUID REFERENCES chat_messages(id) ON DELETE SET NULL,
    added_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_portfolio_user ON portfolio_items(clerk_user_id);
-- Prevent duplicate saves of the same ticker per user
CREATE UNIQUE INDEX idx_portfolio_user_ticker ON portfolio_items(clerk_user_id, ticker);
```

### 6.2 PostgreSQL vs MongoDB?

| Factor | PostgreSQL | MongoDB |
|--------|-----------|---------|
| Schema stability | Chat schema is stable; portfolio mirrors `StockProfile` which may evolve | Better for highly dynamic schemas |
| JSONB support | `stocks` field uses JSONB — gives us flexibility where we need it | Native JSON, but we don't need it everywhere |
| Existing infra | Standard, easy to host (Supabase, Neon, Railway, etc.) | Would add a second DB technology |
| Relationships | Chats → Messages FK, Portfolio → Chat FK work naturally | References are manual |

**Recommendation: PostgreSQL** with JSONB for the `stocks` array. This gives us relational integrity where it matters (user → chats → messages) and schema flexibility where we need it (stock data blobs). If `StockProfile` schema changes frequently, we only update the JSONB — no migrations needed for that column.

---

## 7. Implementation Plan

### Phase 1: Auth (Clerk)
| Task | Owner | Branch |
|------|-------|--------|
| Create Clerk project, get API keys | Michael/Alex | — |
| Install `@clerk/clerk-react`, wrap app in `ClerkProvider` | Frontend | `frontend` |
| Add `<SignedIn>` / `<SignedOut>` gates + `<UserButton>` in header | Frontend | `frontend` |
| Add axios interceptor to attach JWT | Frontend | `frontend` |
| Add Clerk JWT verification middleware in FastAPI | Backend | `backend` |
| Add `CLERK_SECRET_KEY` to backend `.env` | Backend | `backend` |

### Phase 2: Chat Persistence
| Task | Owner | Branch |
|------|-------|--------|
| Create `chats` + `chat_messages` tables (SQL migration) | Backend | `backend` |
| Implement `GET/POST/DELETE /api/chats` endpoints | Backend | `backend` |
| Implement `GET /api/chats/{id}`, `POST /api/chats/{id}/messages` | Backend | `backend` |
| Add chat sidebar to `MainLayout` | Frontend | `frontend` |
| Refactor `useChat` to use API-backed persistence | Frontend | `frontend` |

### Phase 3: Portfolio
| Task | Owner | Branch |
|------|-------|--------|
| Create `portfolio_items` table (SQL migration) | Backend | `backend` |
| Implement `GET/POST/DELETE /api/portfolio` endpoints | Backend | `backend` |
| Add "Save to Portfolio" button on `StockCard` | Frontend | `frontend` |
| Build Portfolio page with `usePortfolio` hook | Frontend | `frontend` |
| Add navigation between Chat ↔ Portfolio | Frontend | `frontend` |

### Phase 4: Polish
- Loading states, error handling, optimistic UI
- Chat title auto-generation
- Portfolio duplicate detection (frontend toast if already saved)
- Mobile responsiveness for sidebar

---

## 8. Environment Variables

### Frontend (`.env.local`)
```
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_API_BASE_URL=http://localhost:8000
```

### Backend (`.env`)
```
CLERK_SECRET_KEY=sk_test_...
DATABASE_URL=postgresql://user:pass@localhost:5432/stockrag
GEMINI_API_KEY=...  # existing
```

---

## 9. Open Questions

1. **Chat history in RAG context** — Should previous messages in a chat be sent to the RAG pipeline as context for follow-up queries? (e.g., "show me more like the first one")
2. **Portfolio updates** — Should we allow editing portfolio items (e.g., updating notes), or keep it simple with add/remove only?
3. **Chat sharing** — Any future need to share chats between users?
4. **Rate limiting** — Should we add per-user rate limits on the RAG endpoint once auth is in place?
5. **Migration tool** — Alembic for Python DB migrations, or raw SQL scripts?

---

## 10. File Impact Summary

### Frontend (files to create/modify)
| File | Action | Notes |
|------|--------|-------|
| `src/main.tsx` | Modify | Wrap with `ClerkProvider` |
| `src/App.tsx` | Modify | Add `SignedIn`/`SignedOut` gates, routing |
| `src/components/header/AppHeader.tsx` | Modify | Add `UserButton`, portfolio nav |
| `src/components/layout/MainLayout.tsx` | Modify | Add chat sidebar |
| `src/components/chat/ChatSidebar.tsx` | **Create** | Chat list + new chat button |
| `src/components/stock/StockCard.tsx` | Modify | Add "Save to Portfolio" button |
| `src/components/portfolio/PortfolioPage.tsx` | **Create** | Portfolio view |
| `src/hooks/useChat.ts` | Modify | API-backed chat persistence |
| `src/hooks/usePortfolio.ts` | **Create** | Portfolio CRUD hook |
| `src/api/client.ts` | Modify | Add auth interceptor, chat/portfolio API functions |
| `src/api/types.ts` | Modify | Add Chat, PortfolioItem types |
| `src/constants/api.ts` | Modify | Add new endpoint constants |

### Backend (files to create/modify)
| File | Action | Notes |
|------|--------|-------|
| `middleware/auth.py` | **Create** | Clerk JWT verification |
| `api/models.py` | Modify | Add Chat, Message, Portfolio Pydantic models |
| `api/routes.py` | Modify | Add chat + portfolio route groups |
| `db/schema.sql` | **Create** | PostgreSQL table definitions |
| `db/connection.py` | **Create** | DB connection pool (asyncpg or SQLAlchemy) |
| `config.py` | Modify | Add `DATABASE_URL`, `CLERK_SECRET_KEY` |
| `requirements.txt` | Modify | Add `asyncpg`, `clerk-backend-api`, `sqlalchemy` (if used) |
