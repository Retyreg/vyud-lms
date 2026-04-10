# CLAUDE.md — VYUD LMS

> Single source of truth for AI agents working on this project.
> Read by: Claude Code, GitHub Copilot, OpenClaw agents.
> Maintainer: @Retyreg | Updated: 2026-04-10

---

## Project Overview

**VYUD LMS** — AI-powered Learning Management System built on a knowledge-graph architecture.
Students navigate interconnected learning nodes (concepts, lessons, assessments) visualized as an interactive graph.
AI personalizes the learning path, generates content, and adapts difficulty in real time.

- **Repository**: `github.com/Retyreg/vyud-lms`
- **Stage**: Active development (pre-launch MVP)
- **License**: TBD

---

## Tech Stack

| Layer         | Technology                          | Notes                                    |
|---------------|-------------------------------------|------------------------------------------|
| Frontend      | Next.js 14+ (App Router)           | TypeScript, React Server Components      |
| Graph UI      | ReactFlow                          | Knowledge-graph visualization            |
| Styling       | Tailwind CSS                        | + shadcn/ui component library            |
| Backend API   | FastAPI (Python 3.11+)              | Async, Pydantic v2 models                |
| Database      | PostgreSQL via Supabase             | Row-Level Security enabled               |
| Auth          | Supabase Auth                       | JWT, OAuth providers                     |
| AI Gateway    | LiteLLM                             | Multi-provider: Anthropic, Google, etc.  |
| ORM           | SQLAlchemy 2.0 (async)              | Alembic for migrations                   |
| Testing       | pytest (backend), Vitest (frontend) |                                          |
| CI/CD         | GitHub Actions                      | Lint → Test → Build → Deploy             |
| Deployment    | TBD (Vercel frontend, VPS backend)  |                                          |

---

## Project Structure

```
vyud-lms/
├── frontend/                   # Next.js application
│   ├── app/                    # App Router pages & layouts
│   │   ├── (auth)/             # Auth-related routes (login, signup)
│   │   ├── (dashboard)/        # Protected dashboard routes
│   │   ├── graph/              # Knowledge graph view
│   │   └── api/                # Next.js API routes (BFF layer)
│   ├── components/             # React components
│   │   ├── ui/                 # shadcn/ui primitives
│   │   ├── graph/              # ReactFlow graph components
│   │   ├── lessons/            # Lesson viewer/editor
│   │   └── shared/             # Shared/layout components
│   ├── lib/                    # Utilities, hooks, API client
│   ├── types/                  # TypeScript type definitions
│   └── public/                 # Static assets
│
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── api/                # API route handlers
│   │   │   └── v1/             # Versioned endpoints
│   │   ├── core/               # Config, security, dependencies
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic layer
│   │   ├── ai/                 # LiteLLM integration, prompts
│   │   └── db/                 # Database session, migrations
│   ├── alembic/                # Migration scripts
│   ├── tests/                  # pytest test suite
│   └── requirements.txt
│
├── supabase/                   # Supabase config & migrations
│   ├── migrations/             # SQL migrations
│   └── seed.sql                # Dev seed data
│
├── .github/
│   └── workflows/              # CI/CD pipelines
│
├── CLAUDE.md                   # ← This file
├── docs/                       # Architecture Decision Records, specs
└── docker-compose.yml          # Local dev environment
```

---

## Architecture Principles

1. **Knowledge Graph First** — every learning entity (concept, lesson, quiz, resource) is a node with typed edges (prerequisite, related, deepens). ReactFlow renders the graph; backend stores it in PostgreSQL with adjacency tables.

2. **AI as a Service Layer** — AI capabilities (content generation, path recommendation, difficulty adaptation) live in `backend/app/ai/` and are called via LiteLLM. Never embed AI logic in route handlers directly.

3. **Strict API Boundary** — Frontend communicates with backend exclusively through REST API (`/api/v1/`). No direct Supabase client calls from frontend except for Auth and Realtime subscriptions.

4. **Type Safety End-to-End** — Pydantic schemas on backend, TypeScript types on frontend. Keep them in sync manually (future: auto-generate from OpenAPI spec).

5. **Feature-Based Organization** — group files by feature (graph, lessons, assessments), not by file type. Shared utilities go in `lib/` or `core/`.

---

## Data Flow

```
User Action (React)
    ↓
Next.js App Router / API Route (BFF)
    ↓
FastAPI endpoint (/api/v1/...)
    ↓
Service layer (business logic)
    ├──→ SQLAlchemy → PostgreSQL/Supabase (data)
    └──→ LiteLLM → Claude/Gemini (AI tasks)
    ↓
Pydantic response schema
    ↓
React component renders result
```

---

## Code Conventions

### Python (Backend)

- **Formatter**: `black` (line-length 88)
- **Linter**: `ruff`
- **Type hints**: Required on all function signatures
- **Async**: All DB and AI calls must be async (`async def`, `await`)
- **Naming**: `snake_case` for functions/variables, `PascalCase` for classes
- **Imports**: stdlib → third-party → local, separated by blank lines
- **Docstrings**: Google style on public functions and classes
- **Error handling**: Raise `HTTPException` in route handlers only; services raise domain exceptions defined in `core/exceptions.py`

```python
# Example: service function
async def get_learning_path(
    user_id: UUID,
    graph_id: UUID,
    db: AsyncSession,
) -> LearningPath:
    """Calculate personalized learning path for a user.

    Args:
        user_id: The learner's ID.
        graph_id: Target knowledge graph.
        db: Async database session.

    Returns:
        Ordered list of nodes forming the recommended path.

    Raises:
        GraphNotFoundError: If graph_id doesn't exist.
    """
    ...
```

### TypeScript (Frontend)

- **Formatter**: `prettier`
- **Linter**: `eslint` (Next.js config)
- **Components**: Functional components with hooks, no class components
- **Naming**: `camelCase` for variables/functions, `PascalCase` for components/types
- **Files**: Component files use `PascalCase.tsx`, utility files use `camelCase.ts`
- **State**: React hooks for local state; consider Zustand if global state grows
- **Fetching**: Server Components for read-only data; `useSWR` or `useQuery` for client-side
- **Props**: Define explicit interfaces, no `any` types

```tsx
// Example: component pattern
interface GraphNodeProps {
  nodeId: string;
  label: string;
  status: 'locked' | 'available' | 'completed';
  onSelect: (id: string) => void;
}

export function GraphNode({ nodeId, label, status, onSelect }: GraphNodeProps) {
  // ...
}
```

### Git Conventions

- **Branches**: `feature/<name>`, `fix/<name>`, `refactor/<name>`
- **Commits**: Conventional Commits — `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`
- **PRs**: Descriptive title, link to issue, checklist of changes
- **Merging**: Squash merge to `main`

---

## Agent Roles & Responsibilities

### Claude Code — Architect & Builder

**Scope**: Strategic decisions, new features, architecture changes.

| Task                              | Example                                                      |
|-----------------------------------|--------------------------------------------------------------|
| Design new modules                | "Create the assessment engine with adaptive difficulty"       |
| Scaffold features                 | Generate route + service + schema + model for a new entity    |
| Architecture decisions            | Choose patterns, define data models, plan API contracts       |
| Roadmap & planning                | Break epics into tasks, define milestones                     |
| Complex refactors                 | Restructure module boundaries, change data flow patterns      |
| AI integration                    | Design prompts, implement LiteLLM service functions           |
| Database schema design            | Create Alembic migrations, design indexes                     |
| Write this file (CLAUDE.md)       | Keep project context updated after major changes              |

**How to invoke**: Terminal → `claude` (Claude Code CLI)

**Protocol**:
- Before creating a new module, update the "Project Structure" section in this file.
- After architectural decisions, add an ADR to `docs/adr/`.
- Generate scaffolding with all layers (route → service → schema → model → test stub).

---

### GitHub Copilot — Maintainer & Quality Guard

**Scope**: Code quality, debugging, testing, CI/CD, documentation.

| Task                              | Example                                                      |
|-----------------------------------|--------------------------------------------------------------|
| Debug & fix                       | Analyze stack trace, find root cause, propose fix             |
| Trace data flow                   | "How does a quiz submission flow from UI to DB?"              |
| Refactor safely                   | Extract function, reduce duplication, improve naming          |
| Add/fix tests                     | Write unit tests for a service, integration tests for API     |
| Improve types                     | Add missing TypeScript types, tighten Pydantic schemas        |
| CI/CD maintenance                 | Fix GitHub Actions, add caching, configure matrix builds      |
| Code review assistance            | Review PR changes for consistency with conventions            |
| Documentation                     | README, CONTRIBUTING, issue templates, changelogs             |
| Performance                       | Profile slow queries, optimize React re-renders               |
| Search codebase                   | Find where a function is used, locate a pattern               |

**How to invoke**: VS Code (inline suggestions + Chat) or GitHub.com (Copilot Chat)

**Protocol**:
- Before refactoring, check this file for architecture principles — don't break boundaries.
- Reference code conventions above for style decisions.
- When fixing CI, check `.github/workflows/` and match existing patterns.
- For PR descriptions, follow the Git Conventions section.

---

## Handoff Protocol

The key to effective collaboration is clear handoffs between agents:

```
┌─────────────────────────────────────────────────────┐
│                    TASK LIFECYCLE                     │
│                                                      │
│  1. PLAN        → Claude Code                        │
│     Design, decide architecture, create scaffolding  │
│     Output: new files, updated CLAUDE.md, ADR        │
│                                                      │
│  2. IMPLEMENT   → Claude Code (new) / Copilot (edit) │
│     New feature = Claude Code                        │
│     Edit existing = Copilot                          │
│                                                      │
│  3. POLISH      → GitHub Copilot                     │
│     Tests, types, error handling, edge cases          │
│                                                      │
│  4. REVIEW      → GitHub Copilot (code quality)      │
│                 → Claude Code (architecture check)   │
│                                                      │
│  5. SHIP        → GitHub Copilot                     │
│     PR, changelog, CI green, merge                   │
└─────────────────────────────────────────────────────┘
```

### Context Transfer Rules

1. **CLAUDE.md is the shared memory** — both agents read this file. Update it after any architectural change.
2. **ADRs for decisions** — if Claude Code makes a non-obvious choice (e.g., "we use adjacency list, not nested sets"), document it in `docs/adr/NNN-title.md`.
3. **TODO comments for handoffs** — if Claude Code scaffolds a function but skips edge cases, leave `# TODO(copilot): add validation for empty graph` so Copilot knows what to pick up.
4. **Commit messages as signals** — a `feat:` commit from Claude Code tells Copilot "new code to test and polish". A `fix:` commit from Copilot tells Claude Code "the architecture held, just needed a bug fix".

---

## Decision Log (Recent)

| Date       | Decision                                      | Agent       | Status   |
|------------|-----------------------------------------------|-------------|----------|
| 2026-04-10 | Created CLAUDE.md as shared context file       | Claude Code | Active   |
| 2026-04-02 | Set up OpenClaw multi-agent config (4 agents)  | Claude Code | Active   |
| TBD        | (add decisions as they're made)                |             |          |

---

## Quick Reference: "Who Do I Ask?"

| I need to...                          | Ask            |
|---------------------------------------|----------------|
| Build a new feature from scratch      | Claude Code    |
| Fix a bug in existing code            | Copilot        |
| Decide on a database schema           | Claude Code    |
| Write tests for an endpoint           | Copilot        |
| Restructure a module                  | Claude Code    |
| Refactor a function without changing behavior | Copilot |
| Set up a new CI pipeline              | Copilot        |
| Design AI prompts for LiteLLM         | Claude Code    |
| Improve TypeScript types              | Copilot        |
| Add a new API endpoint                | Claude Code    |
| Debug a failing test                  | Copilot        |
| Update CLAUDE.md                      | Claude Code    |
| Write PR description                  | Copilot        |
| Review architecture consistency       | Claude Code    |
| Optimize a slow query                 | Copilot        |

---

## Environment Setup

```bash
# Clone
git clone git@github.com:Retyreg/vyud-lms.git
cd vyud-lms

# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in Supabase URL, keys, LiteLLM config
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
cp .env.example .env.local  # fill in API URL, Supabase keys
npm run dev

# Full stack (Docker)
docker-compose up -d
```

---

## Important Paths

| What                    | Path                                |
|-------------------------|-------------------------------------|
| API routes              | `backend/app/api/v1/`               |
| Business logic          | `backend/app/services/`             |
| Database models         | `backend/app/models/`               |
| Pydantic schemas        | `backend/app/schemas/`              |
| AI/LLM integration      | `backend/app/ai/`                   |
| Alembic migrations      | `backend/alembic/versions/`         |
| React pages             | `frontend/app/`                     |
| React components        | `frontend/components/`              |
| Graph components        | `frontend/components/graph/`        |
| TypeScript types        | `frontend/types/`                   |
| CI/CD workflows         | `.github/workflows/`                |
| Architecture decisions  | `docs/adr/`                         |
| This file               | `CLAUDE.md`                         |
