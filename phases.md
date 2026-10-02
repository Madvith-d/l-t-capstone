# AI-Based College Academic Assistant — Implementation Phases

## 0. How to Use This File

This file is the implementation roadmap for the AI coding agent.

The agent must execute phases **sequentially**.

For every phase:

1. Read the phase objective.
2. Inspect the existing repository.
3. Implement only the listed work.
4. Run the phase-specific tests.
5. Fix failures.
6. Verify the acceptance criteria.
7. Update documentation if necessary.
8. Only then move to the next phase.

Do not skip directly to later phases.

Do not implement functionality listed in `scope.md` as out of scope.

---

# Phase 1 — Repository Initialization

## Objective

Create the base monorepo and establish the frontend/backend development environment.

## Tasks

### 1.1 Create repository structure

```text
academic-assistant/
├── frontend/
├── backend/
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
├── docs/
├── tests/
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── scope.md
└── phases.md
```

### 1.2 Initialize frontend

Use:

```text
Next.js
TypeScript
Tailwind CSS
```

Create a minimal page proving the frontend runs.

### 1.3 Initialize backend

Use:

```text
Python
FastAPI
Pydantic
```

Create:

```text
GET /health
```

Expected:

```json
{
  "status": "ok"
}
```

### 1.4 Add environment configuration

Create `.env.example`.

Never commit real secrets.

## Acceptance Criteria

- Frontend starts successfully.
- Backend starts successfully.
- `/health` returns 200.
- Environment variables load correctly.
- Repository structure matches the architecture.

## Required Test

```text
Frontend → HTTP 200
Backend → GET /health → HTTP 200
```

---

# Phase 2 — Docker and PostgreSQL

## Objective

Create the local infrastructure.

## Tasks

### 2.1 Add PostgreSQL

Use a PostgreSQL image with pgvector support.

### 2.2 Configure persistent storage

Database data must survive container restarts.

### 2.3 Create database connection

Backend must connect using:

```text
DATABASE_URL
```

### 2.4 Add migration system

Use a proper migration mechanism.

### 2.5 Create initial schema

Create tables/entities for:

```text
users
documents
document_chunks
conversations
messages
study_plans
study_sessions
```

## Acceptance Criteria

- `docker compose up` starts PostgreSQL.
- Backend connects successfully.
- Database migrations run successfully.
- pgvector extension is available.
- Database persists across restarts.

---

# Phase 3 — Document Ingestion

## Objective

Build the PDF ingestion pipeline.

## Tasks

### 3.1 Implement document loading

Support:

```text
PDF
TXT
```

PDF support is mandatory.

### 3.2 Extract text

Preserve page information where possible.

### 3.3 Clean extracted text

Handle:

- Excessive whitespace.
- Repeated headers/footers where detectable.
- Empty pages.
- Encoding problems.

Do not destroy meaningful document structure.

### 3.4 Attach metadata

Each chunk must eventually retain:

```text
document_id
title
category
department
academic_year
page_number
section
source
```

### 3.5 Implement chunking

Start with approximately:

```text
700–1000 tokens
100–150 token overlap
```

Make these configurable.

### 3.6 Prevent duplicate ingestion

Repeated ingestion of the same document must not blindly duplicate chunks.

Use a stable document identifier or content hash.

## Acceptance Criteria

Given:

```text
data/raw/academic-regulations.pdf
```

the pipeline produces clean document chunks with metadata.

---

# Phase 4 — Embeddings and Vector Storage

## Objective

Convert document chunks into embeddings and store them in PostgreSQL + pgvector.

## Tasks

### 4.1 Create embedding service

Define an interface such as:

```python
class EmbeddingService:
    def embed_documents(...)
    def embed_query(...)
```

### 4.2 Keep provider configuration separate

The embedding provider/model must come from environment configuration.

### 4.3 Generate embeddings

Each document chunk receives an embedding vector.

### 4.4 Store vectors

Store:

```text
chunk content
embedding
metadata
```

in PostgreSQL.

### 4.5 Implement vector similarity search

Create a retriever:

```python
retrieve(
    query,
    top_k,
    score_threshold
)
```

## Acceptance Criteria

- Documents have stored embeddings.
- Semantic search returns relevant chunks.
- Top-K is configurable.
- Similarity threshold is configurable.
- Metadata is returned with each result.

---

# Phase 5 — Basic RAG Pipeline

## Objective

Create the first working academic question-answering system.

Do not implement LangGraph yet.

## Tasks

### 5.1 Create query embedding

Convert the user query into an embedding.

### 5.2 Retrieve relevant chunks

Use pgvector.

### 5.3 Build context

Combine retrieved chunks with source metadata.

### 5.4 Create RAG prompt

The prompt must instruct the LLM:

- Use supplied context.
- Do not invent college-specific information.
- Say when information is unavailable.
- Answer clearly.
- Preserve source references.

### 5.5 Generate answer

Call the configured LLM.

### 5.6 Return sources

Response must contain:

```json
{
  "answer": "...",
  "sources": []
}
```

## Acceptance Criteria

The following must work:

```text
Question
 ↓
Retriever
 ↓
Context
 ↓
LLM
 ↓
Answer + Sources
```

---

# Phase 6 — RAG Quality and Source Grounding

## Objective

Make retrieval and grounding reliable enough for the MVP.

## Tasks

### 6.1 Add configurable retrieval parameters

```text
TOP_K
SCORE_THRESHOLD
```

### 6.2 Add metadata filtering

Support filters such as:

```text
department
category
academic_year
```

when available.

### 6.3 Add source normalization

Ensure every returned source has consistent fields.

### 6.4 Implement insufficient-context detection

If retrieved evidence is below the configured threshold:

```text
No sufficient evidence
```

must be returned to the application layer.

### 6.5 Improve chunk metadata

Ensure page and document references survive the complete RAG pipeline.

## Acceptance Criteria

- Relevant documents are retrieved for known questions.
- Irrelevant questions can result in no-answer state.
- Sources are displayed accurately.
- Retrieval parameters are configurable.

---

# Phase 7 — Conversation Management

## Objective

Add persistent conversations and follow-up understanding.

## Tasks

### 7.1 Create conversation API

Implement:

```text
POST /api/conversations
GET /api/conversations
GET /api/conversations/{id}
```

### 7.2 Persist messages

Store:

```text
role
content
timestamp
conversation_id
```

### 7.3 Build conversation context

Provide recent messages to the application workflow.

### 7.4 Add conversation summarization if necessary

Do not send unlimited history to the LLM.

### 7.5 Test follow-up questions

Example:

```text
What is the attendance requirement?

What happens if I don't meet it?
```

## Acceptance Criteria

- Conversations persist.
- Messages persist.
- Follow-up questions use previous context.
- Context size is controlled.

---

# Phase 8 — LangGraph Foundation

## Objective

Move orchestration into LangGraph.

## Tasks

### 8.1 Define state

Implement structured graph state containing:

```text
question
conversation_history
intent
retrieved_documents
context
tool_calls
tool_results
study_plan
response
sources
```

### 8.2 Create query-analysis node

Determine intent.

### 8.3 Create routing node

Route to:

```text
academic
planner
tool
general
```

### 8.4 Connect academic path

Implement:

```text
analyze
→ retrieve
→ validate
→ answer
```

### 8.5 Add finalization node

Normalize final response.

## Acceptance Criteria

The same RAG functionality now runs through LangGraph.

The graph can be visualized or otherwise inspected during development.

---

# Phase 9 — Query Classification

## Objective

Make request routing explicit and predictable.

## Tasks

Support:

```text
ACADEMIC_QA
DOCUMENT_SEARCH
STUDY_PLAN
STUDY_PLAN_MODIFICATION
CALCULATION
GENERAL_CONVERSATION
UNKNOWN
```

### 9.1 Create classification schema

Use structured output.

### 9.2 Add classification node

### 9.3 Add routing logic

### 9.4 Add tests for each intent

Example:

```text
"What is the attendance rule?"
→ ACADEMIC_QA

"Create a study plan."
→ STUDY_PLAN

"What is 20% of 500?"
→ CALCULATION
```

## Acceptance Criteria

All defined intents route to the correct workflow under the evaluation test set.

---

# Phase 10 — External Tools

## Objective

Add deterministic external capabilities.

## Tasks

### 10.1 Implement calculator tool

The tool must accept a safe mathematical expression or structured operation.

Do not use unrestricted code execution.

### 10.2 Register calculator with LangGraph/LangChain

### 10.3 Implement calendar abstraction

Create an interface such as:

```python
create_event(...)
list_events(...)
```

### 10.4 Implement mock calendar if required

The mock must use the same interface expected from a real provider.

### 10.5 Add tool execution node

Workflow:

```text
Analyze
→ Select Tool
→ Execute
→ Store Result
→ Respond
```

## Acceptance Criteria

Calculator requests execute through the calculator tool.

Calendar requests can execute through the calendar abstraction.

---

# Phase 11 — Study Planner Engine

## Objective

Build personalized study-plan generation.

## Tasks

### 11.1 Define planner input schema

Include:

```text
subjects
topics
difficulty
exam_date
available_hours
optional preferred times
```

### 11.2 Define planner output schema

Use structured JSON.

### 11.3 Implement planning algorithm/prompt

The planner must consider:

- Time available.
- Number of days.
- Subject workload.
- Difficulty.
- Topic coverage.
- Exam deadline.

### 11.4 Persist generated plans

Store:

```text
study_plans
study_sessions
```

### 11.5 Connect planner to LangGraph

Workflow:

```text
STUDY_PLAN
 ↓
generate_plan
 ↓
validate_plan
 ↓
persist_plan
 ↓
respond
```

## Acceptance Criteria

A student can submit subjects, available time, and exam date and receive a valid structured plan.

---

# Phase 12 — Study Plan Validator

## Objective

Prevent invalid plans.

## Tasks

Implement deterministic validation for:

```text
Daily time limit
Exam date
Session duration
Date validity
Subject coverage
```

### 12.1 Reject invalid plans

### 12.2 Attempt controlled repair when appropriate

If repair fails, return a structured validation error.

### 12.3 Add unit tests

Test:

```text
valid plan
overloaded day
session after exam
invalid duration
missing subject
```

## Acceptance Criteria

Invalid plans cannot silently reach the user as valid plans.

---

# Phase 13 — Study Plan Modification

## Objective

Allow natural-language modifications to an existing plan.

## Tasks

### 13.1 Retrieve existing plan

### 13.2 Classify modification intent

Examples:

```text
Remove Saturday.
Move DBMS to Monday.
I only have one hour tomorrow.
```

### 13.3 Determine affected sessions

### 13.4 Modify only required sections

### 13.5 Redistribute displaced workload

### 13.6 Validate the modified plan

### 13.7 Persist updated plan

## Acceptance Criteria

A user can modify an existing plan conversationally.

Unaffected plan entries remain unchanged whenever possible.

---

# Phase 14 — Unknown Question Handling

## Objective

Prevent unsupported college-specific answers.

## Tasks

### 14.1 Implement retrieval confidence evaluation

### 14.2 Add no-evidence state

### 14.3 Add safe response

Example:

```text
I couldn't find information about this in the
available college documents.
```

### 14.4 Test unrelated questions

Examples:

```text
What will the cafeteria serve next Tuesday?

What is the college's policy on a rule that does not
exist in the uploaded documents?
```

## Acceptance Criteria

The system does not fabricate missing college information.

---

# Phase 15 — Frontend Chat

## Objective

Build the student-facing chat interface.

## Tasks

### 15.1 Create chat layout

Include:

```text
Sidebar
Conversation list
Chat messages
Input
Send button
```

### 15.2 Connect chat API

### 15.3 Render sources

Sources must appear separately from answer content.

### 15.4 Add loading states

### 15.5 Add error states

### 15.6 Add conversation selection

## Acceptance Criteria

A student can complete:

```text
Open chat
→ ask question
→ receive answer
→ inspect sources
→ ask follow-up
```

without using API tools manually.

---

# Phase 16 — Frontend Study Planner

## Objective

Build planner and plan-management UI.

## Tasks

### 16.1 Create planner form

Fields:

```text
Subject
Topics
Difficulty
Exam date
Available hours
```

### 16.2 Submit planner request

### 16.3 Display generated plan

Use:

```text
Day
Subject
Topic
Duration
```

### 16.4 Add natural-language modification

Example input:

```text
I cannot study on Saturday.
```

### 16.5 Refresh displayed plan

## Acceptance Criteria

A student can generate and modify a study plan entirely through the UI.

---

# Phase 17 — Documents and Sources UI

## Objective

Make the knowledge base visible and traceable.

## Tasks

### 17.1 Create documents page

Display:

```text
Title
Category
Department
Academic year
```

### 17.2 Display source details

For every RAG answer show:

```text
Document
Page
Section
```

### 17.3 Handle missing source data gracefully

## Acceptance Criteria

Users can understand where academic answers came from.

---

# Phase 18 — Backend API Hardening

## Objective

Make the backend suitable for integrated use.

## Tasks

Implement and verify:

```text
POST /api/chat

GET /api/conversations
GET /api/conversations/{id}

POST /api/plans
GET /api/plans/{id}
PATCH /api/plans/{id}

GET /api/documents

GET /health
```

Add:

- Request validation.
- Response schemas.
- Error handling.
- Request IDs.
- Timeouts.
- Structured logging.

## Acceptance Criteria

Invalid API requests produce predictable 4xx responses.

Internal failures produce controlled 5xx responses without exposing stack traces.

---

# Phase 19 — Testing

## Objective

Verify the complete system.

## 19.1 Unit tests

Test:

```text
Chunking
Metadata
Retrieval
Plan validation
Plan modification
Tool functions
Intent classification
```

## 19.2 Integration tests

Test:

```text
API
→ LangGraph
→ RAG
→ Database
```

## 19.3 End-to-end tests

Test:

```text
Student
→ UI
→ API
→ Graph
→ Response
```

## 19.4 Required scenario tests

### Scenario A — Direct question

```text
What is the minimum attendance requirement?
```

### Scenario B — Follow-up

```text
What is the attendance requirement?
What happens if I don't meet it?
```

### Scenario C — RAG question

```text
What subjects are present in semester 4?
```

### Scenario D — Unknown

```text
What will the cafeteria serve next Tuesday?
```

### Scenario E — Study plan

```text
Create a 14-day plan for DBMS and OS.
I have 3 hours per day.
```

### Scenario F — Modification

```text
I cannot study Saturday.
```

### Scenario G — Tool

```text
What is 18% of 750?
```

## Acceptance Criteria

All critical scenarios pass.

---

# Phase 20 — Basic LLM vs RAG Evaluation

## Objective

Demonstrate the value of retrieval grounding.

## Tasks

### 20.1 Create evaluation dataset

Include at least:

```text
5 direct questions
5 RAG questions
3 follow-up sequences
3 unknown questions
3 multi-step requests
```

### 20.2 Implement basic LLM baseline

The baseline must receive the question without college-document retrieval.

### 20.3 Run RAG system

Use exactly the same questions.

### 20.4 Record outputs

Store:

```text
question
baseline_answer
rag_answer
sources
evaluation notes
```

### 20.5 Calculate evaluation metrics

Include:

```text
Correctness
Grounding
Unsupported answer rate
Relevance
Follow-up handling
```

## Acceptance Criteria

A reproducible evaluation report exists.

Do not hard-code claims about which system performs better; use the measured results.

---

# Phase 21 — Observability

## Objective

Make the agent workflow debuggable.

## Tasks

Log:

```text
request_id
user/conversation identifier where appropriate
intent
graph route
retrieved chunk IDs
retrieval scores
tool calls
LLM latency
total latency
errors
```

Do not log:

```text
API keys
passwords
raw secrets
unnecessary sensitive information
```

## Acceptance Criteria

A failed request can be traced through the workflow without exposing secrets.

---

# Phase 22 — Security Review

## Objective

Remove common implementation risks.

## Tasks

Verify:

- Secrets use environment variables.
- `.env` is ignored.
- SQL/ORM operations are parameterized.
- Uploaded files are validated.
- Tool execution is restricted.
- No arbitrary Python/JavaScript execution exists.
- User input is validated.
- Error messages do not expose internal stack traces.

## Acceptance Criteria

A security checklist is completed before deployment.

---

# Phase 23 — Docker Integration

## Objective

Run the entire application consistently.

## Tasks

### 23.1 Create frontend Dockerfile

### 23.2 Create backend Dockerfile

### 23.3 Configure PostgreSQL/pgvector

### 23.4 Connect services

### 23.5 Add health checks

### 23.6 Test clean startup

Run:

```bash
docker compose up --build
```

## Acceptance Criteria

A clean environment can start the complete application using Docker Compose.

---

# Phase 24 — Documentation

## Objective

Document the system for developers and evaluators.

Create/update:

```text
README.md
scope.md
phases.md
docs/architecture.md
docs/setup.md
docs/rag.md
docs/langgraph.md
docs/api.md
docs/evaluation.md
```

README must contain:

```text
Project overview
Architecture
Tech stack
Prerequisites
Environment variables
Local setup
Database setup
Document ingestion
Running the application
Running tests
Evaluation
```

---

# Phase 25 — Final Integration

## Objective

Verify the complete workflow from end to end.

Run:

```text
1. Start Docker environment.
2. Run database migrations.
3. Ingest college documents.
4. Verify vectors.
5. Start backend.
6. Start frontend.
7. Ask a RAG question.
8. Ask a follow-up.
9. Ask an unknown question.
10. Generate a study plan.
11. Modify the study plan.
12. Execute calculator tool.
13. Run automated tests.
14. Run baseline-vs-RAG evaluation.
```

## Final Acceptance Criteria

The system must demonstrate:

```text
College Documents
        ↓
Document Ingestion
        ↓
Embeddings
        ↓
pgvector
        ↓
RAG
        ↓
LangGraph
        ↓
Intent Routing
        ↓
 ┌──────┼────────┐
 │      │        │
RAG   Planner   Tools
 │      │        │
 └──────┼────────┘
        ↓
Grounded Response
        ↓
Next.js UI
```

---

# Phase Completion Checklist

## Phase 1–4: Foundation

- [ ] Repository initialized.
- [ ] Frontend working.
- [ ] Backend working.
- [ ] PostgreSQL working.
- [ ] pgvector enabled.
- [ ] Database migrations working.
- [ ] Document ingestion working.
- [ ] Embeddings stored.

## Phase 5–8: AI/RAG

- [ ] RAG pipeline working.
- [ ] Sources returned.
- [ ] Unknown handling implemented.
- [ ] Conversations persisted.
- [ ] Follow-ups work.
- [ ] LangGraph workflow operational.

## Phase 9–13: Agent Features

- [ ] Intent routing working.
- [ ] Calculator tool working.
- [ ] Calendar abstraction working.
- [ ] Study planner working.
- [ ] Plan validation working.
- [ ] Plan modification working.

## Phase 14–18: Product

- [ ] Unknown handling tested.
- [ ] Chat UI working.
- [ ] Planner UI working.
- [ ] Documents UI working.
- [ ] APIs hardened.

## Phase 19–25: Quality and Delivery

- [ ] Unit tests pass.
- [ ] Integration tests pass.
- [ ] E2E tests pass.
- [ ] Baseline-vs-RAG evaluation completed.
- [ ] Observability implemented.
- [ ] Security review completed.
- [ ] Docker Compose works.
- [ ] Documentation completed.
- [ ] Final end-to-end workflow verified.

---

# AI Agent Operating Rules

The following rules apply throughout implementation.

## Rule 1 — Follow the scope

`scope.md` is the authority for what the application should contain.

## Rule 2 — Follow the phases

Do not implement Phase N+1 while Phase N is incomplete.

## Rule 3 — Inspect before changing

Before modifying an existing file:

1. Read it.
2. Understand its current responsibility.
3. Preserve working functionality.
4. Make the smallest appropriate change.

## Rule 4 — Avoid monolithic files

Keep separate modules for:

```text
RAG
LLM
Embeddings
Retrieval
LangGraph
Tools
Planner
Database
API
```

## Rule 5 — Prefer deterministic logic

Use deterministic code for:

```text
Validation
Arithmetic
Date calculations
Database operations
Constraint checks
```

Use LLMs for:

```text
Natural-language understanding
Intent classification
Contextual answer generation
Natural-language plan interpretation
```

## Rule 6 — Structured outputs

Whenever an LLM produces data consumed by application logic, use structured output/schema validation.

Do not parse arbitrary natural-language responses when a structured schema can be used.

## Rule 7 — No hallucinated college facts

College-specific information must be grounded in retrieved documents.

## Rule 8 — No hidden scope expansion

If implementation reveals a feature that is useful but not in scope:

```text
Do not implement it automatically.
Document it as a future enhancement.
Continue with the defined phase.
```

## Rule 9 — Test before progressing

A phase is not complete merely because code was written.

The phase is complete when:

```text
Implementation
+
Tests
+
Acceptance criteria
```

all pass.

## Rule 10 — Keep the MVP understandable

Prefer:

```text
simple architecture
clear interfaces
small services
structured state
deterministic validation
```

over unnecessary abstraction or premature optimization.

---

# Future Enhancements — Do Not Implement During MVP

Potential future features may include:

```text
Authentication and role-based administration
Real Google Calendar integration
Notifications
Email reminders
Advanced reranking
Hybrid keyword + semantic search
Document upload UI
OCR for scanned PDFs
Analytics dashboard
Feedback-based retrieval evaluation
Multiple LLM providers
Redis caching
Background ingestion workers
Streaming token responses
Advanced user personalization
```

These must remain outside the MVP unless explicitly approved.
