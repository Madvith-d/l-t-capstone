# AI-Based College Academic Assistant — Project Scope

## 1. Document Purpose

This document defines the exact scope, boundaries, functional requirements, technical constraints, architecture expectations, and acceptance criteria for the **AI-Based College Academic Assistant**.

This document is intended to be used as a **hard scope contract for an AI coding agent**. The agent must implement only the functionality defined here unless the project owner explicitly approves a scope change.

The system must provide a single AI-based academic assistant capable of:

- Answering academic questions using college-provided documents.
- Searching and retrieving relevant information from college documents.
- Maintaining conversational context for follow-up questions.
- Creating personalized study plans.
- Modifying existing study plans through natural-language instructions.
- Executing at least one external tool/API operation.
- Handling questions for which the knowledge base has insufficient information.
- Demonstrating a LangChain + LangGraph based workflow.
- Comparing a basic LLM chatbot against the RAG-based assistant.

---

# 2. Project Objective

Build a production-structured MVP of a college academic assistant that combines:

- LLM-based natural-language understanding.
- Retrieval-Augmented Generation (RAG).
- LangChain components.
- LangGraph workflow orchestration.
- Vector search.
- Conversational memory.
- Deterministic tools.
- Personalized study planning.
- Structured plan modification.
- Source-grounded responses.

The system must prioritize **grounded answers over plausible answers**. College-specific facts must come from the configured knowledge base whenever the question requires college-specific information.

---

# 3. Primary Users

## 3.1 Student

The primary user can:

- Ask academic questions.
- Search college information.
- Ask follow-up questions.
- Create study plans.
- Modify study plans.
- View document sources.
- View previous conversations.

## 3.2 System Administrator

The administrator is responsible for:

- Adding/updating college documents.
- Running document ingestion.
- Monitoring ingestion failures.
- Maintaining configuration.

A full administrator dashboard is **not required for MVP**. Document ingestion may initially be handled through a CLI/script or protected backend operation.

---

# 4. Core Features

## 4.1 Academic Question Answering

The assistant must answer questions using the college knowledge base.

Examples:

- "What is the minimum attendance requirement?"
- "What are the examination guidelines?"
- "What subjects are included in semester 4?"
- "What are the rules for internal assessment?"

For college-specific questions:

1. Analyze the query.
2. Retrieve relevant document chunks.
3. Determine whether sufficient evidence exists.
4. Generate an answer from retrieved context.
5. Return source information.

---

## 4.2 College Document Search

The knowledge base must support documents such as:

- Syllabus.
- Academic regulations.
- Examination guidelines.
- Student FAQs.
- Course-related documents.
- Other approved college academic documents.

Each document must have metadata.

Minimum metadata:

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

The retrieval system must preserve metadata so that answers can identify their sources.

---

## 4.3 Retrieval-Augmented Generation

The system must implement a complete RAG pipeline:

```text
Document
    ↓
Text Extraction
    ↓
Cleaning
    ↓
Chunking
    ↓
Embedding
    ↓
Vector Database
    ↓
Query Embedding
    ↓
Similarity Search
    ↓
Relevant Chunks
    ↓
Context Construction
    ↓
LLM
    ↓
Grounded Answer
```

The vector database must support semantic similarity search.

PostgreSQL + pgvector is the default database implementation.

---

## 4.4 Source Attribution

RAG answers must expose their sources.

Example response:

```text
The minimum attendance requirement is 85%.

Sources:
- Academic Regulations 2026 — Page 14
```

The backend must return structured source metadata.

Example:

```json
{
  "answer": "The minimum attendance requirement is 85%.",
  "sources": [
    {
      "document_id": "academic-regulations-2026",
      "title": "Academic Regulations 2026",
      "page": 14,
      "section": "Attendance"
    }
  ]
}
```

The UI must display sources separately from the answer.

---

# 5. Conversational Context

The assistant must understand follow-up questions.

Example:

```text
Student:
What is the attendance requirement?

Assistant:
The minimum attendance requirement is 85%.

Student:
What happens if I don't meet it?
```

The second question must be interpreted using the previous conversation context.

The system must maintain:

- Conversation ID.
- Recent messages.
- Relevant conversation summary/context.
- Current user query.

The implementation must avoid sending unlimited historical messages to the LLM.

---

# 6. Query Classification

The system must classify incoming requests into a controlled set of intents.

Minimum supported intents:

```text
ACADEMIC_QA
DOCUMENT_SEARCH
STUDY_PLAN
STUDY_PLAN_MODIFICATION
CALCULATION
GENERAL_CONVERSATION
UNKNOWN
```

The classifier must be implemented as a dedicated LangGraph node or service.

Routing must be explicit.

---

# 7. LangGraph Workflow

LangGraph must orchestrate the multi-step workflow.

The graph must contain at minimum:

```text
START
  ↓
analyze_query
  ↓
route_request
  ├── academic → retrieve_documents
  │                    ↓
  │              validate_context
  │                    ↓
  │              generate_answer
  │
  ├── planner → generate_study_plan
  │                    ↓
  │               validate_plan
  │
  └── tool → select_tool
                  ↓
             execute_tool
                  ↓
            generate_answer
  ↓
finalize_response
  ↓
END
```

The exact implementation can differ internally, but the responsibilities must remain.

---

# 8. LangGraph State

The graph must maintain structured state.

Minimum conceptual state:

```python
{
    "user_id": "...",
    "question": "...",
    "conversation_history": [],
    "intent": "...",
    "retrieved_documents": [],
    "context": "...",
    "tool_calls": [],
    "tool_results": [],
    "study_plan": None,
    "response": "...",
    "sources": [],
    "confidence": 0.0
}
```

Do not store arbitrary unstructured state when structured fields are sufficient.

---

# 9. Study Planner

The assistant must generate personalized study plans based on:

- Subjects.
- Topics.
- Topic difficulty.
- Available study hours.
- Exam date.
- Optional preferred study periods.

Example input:

```json
{
  "subjects": [
    {
      "name": "DBMS",
      "difficulty": 4,
      "topics": [
        "SQL",
        "Normalization",
        "Transactions"
      ]
    }
  ],
  "available_hours_per_day": 3,
  "exam_date": "2026-11-15"
}
```

The planner must return structured data.

Example:

```json
{
  "plan": [
    {
      "date": "2026-10-01",
      "sessions": [
        {
          "subject": "DBMS",
          "topic": "SQL",
          "duration_minutes": 60
        }
      ]
    }
  ]
}
```

The LLM may generate the initial allocation, but deterministic validation must verify the result.

---

# 10. Study Plan Validation

Every generated or modified plan must be validated.

Minimum constraints:

1. Daily study time must not exceed available study time.
2. Sessions must not be scheduled after the examination date.
3. Required subjects must be represented.
4. Session durations must be positive.
5. Dates and times must be valid.
6. The resulting plan must remain internally consistent.

Invalid plans must be rejected or repaired before being shown to the student.

---

# 11. Study Plan Modification

The user must be able to modify an existing plan using natural language.

Examples:

```text
I cannot study on Saturday.
```

```text
Move DBMS revision to Monday.
```

```text
I only have one hour tomorrow.
```

The system must:

1. Load the existing plan.
2. Interpret the requested change.
3. Identify affected sessions.
4. Preserve unaffected sessions where possible.
5. Redistribute displaced work when required.
6. Validate the modified plan.
7. Return the updated plan.

A small modification should not unnecessarily destroy unrelated parts of the plan.

---

# 12. External Tool/API

At least one external tool must be implemented.

The preferred MVP tools are:

## Calculator

Use a deterministic calculator for arithmetic.

Example:

```text
What is 18% of 750?
```

Workflow:

```text
Query
 ↓
Intent detection
 ↓
Calculator tool
 ↓
Result
 ↓
Response
```

## Calendar

A calendar abstraction should also be implemented if feasible.

Example:

```text
Schedule DBMS revision tomorrow at 7 PM.
```

The system should support a calendar tool interface.

A mock/local implementation is acceptable for the MVP if external credentials are unavailable, but the architecture must allow replacement with a real calendar API.

---

# 13. Unknown Knowledge Handling

The assistant must not fabricate college-specific information.

If retrieval does not provide sufficient evidence:

```text
I couldn't find information about this in the available college documents.
```

The system must distinguish:

```text
Relevant evidence found
```

from:

```text
No sufficient evidence found
```

A retrieval threshold must be configurable.

The threshold must not be hard-coded throughout the codebase.

---

# 14. Basic LLM vs RAG Comparison

The project must include an evaluation mode or evaluation script that compares:

```text
Basic LLM
vs
RAG Assistant
```

The same question set must be used for both systems.

Minimum evaluation categories:

- Direct academic questions.
- Document-based questions.
- Follow-up questions.
- Unknown questions.
- Multi-step questions.

Metrics should include:

- Factual correctness.
- Grounding/source availability.
- Hallucination or unsupported-answer rate.
- Relevance.
- Follow-up handling.

The system must store or export evaluation results.

---

# 15. Frontend Scope

The frontend must be implemented using:

```text
Next.js
TypeScript
Tailwind CSS
```

The MVP must contain:

## Chat Screen

Must support:

- Sending messages.
- Streaming or incremental responses if practical.
- Displaying assistant responses.
- Displaying sources.
- Conversation history.
- Loading/error states.

## Study Planner Screen

Must support:

- Subject entry.
- Topic entry.
- Difficulty.
- Exam date.
- Available daily study hours.
- Plan generation.

## Study Plan View

Must display:

- Date.
- Subject.
- Topic.
- Duration.
- Status.

Must support modification through natural language.

## Documents/Sources View

Must display available document metadata and source information.

---

# 16. Backend Scope

Backend must use:

```text
Python
FastAPI
LangChain
LangGraph
PostgreSQL
pgvector
```

Minimum API groups:

```text
/api/chat
/api/conversations
/api/plans
/api/documents
```

Example:

```http
POST /api/chat
GET  /api/conversations
GET  /api/conversations/{id}

POST /api/plans
GET  /api/plans/{id}
PATCH /api/plans/{id}

GET /api/documents
```

The API must return structured JSON.

---

# 17. Database Scope

Required tables/entities:

```text
users
documents
document_chunks
conversations
messages
study_plans
study_sessions
```

The exact schema may be adjusted during implementation, but the relationships must support:

```text
User
 ├── Conversations
 │      └── Messages
 │
 └── Study Plans
        └── Study Sessions

Document
 └── Document Chunks
       └── Embeddings
```

---

# 18. Document Ingestion Scope

The ingestion pipeline must support:

```text
PDF
TXT
```

PDF is mandatory.

Pipeline:

```text
Load
 ↓
Extract text
 ↓
Clean
 ↓
Chunk
 ↓
Attach metadata
 ↓
Embed
 ↓
Store in pgvector
```

The ingestion process must be repeatable.

It must not create uncontrolled duplicate chunks when the same document is ingested repeatedly.

---

# 19. Security Scope

Minimum security requirements:

- API keys must be stored in environment variables.
- Secrets must never be committed to Git.
- User input must be validated.
- Database queries must use parameterized/ORM operations.
- Tool execution must be restricted to explicitly registered tools.
- Arbitrary code execution is prohibited.
- File uploads must be validated.
- Logs must avoid unnecessary sensitive user data.

Authentication may be implemented if required by deployment, but a complete enterprise identity system is outside MVP scope.

---

# 20. Error Handling

The system must handle:

- Invalid requests.
- Empty questions.
- LLM failures.
- Embedding failures.
- Vector database failures.
- Document parsing failures.
- Tool failures.
- Invalid study plans.
- Missing sources.
- Timeout conditions.

Errors must produce useful user-facing messages without exposing stack traces.

---

# 21. Observability

The backend must log enough information to debug workflows.

Minimum fields:

```text
request_id
intent
graph path
retrieved document IDs
retrieval scores
tools used
LLM latency
total request latency
error state
```

Do not log API keys or unnecessary personal data.

---

# 22. Deployment Scope

The project must run locally using Docker Compose.

Required services:

```text
frontend
backend
postgres
```

PostgreSQL must include pgvector support.

The system should be deployable later to:

```text
Frontend → Vercel or equivalent
Backend → Render/Railway/Fly.io or equivalent
Database → managed PostgreSQL
```

Deployment to a specific cloud provider is not mandatory unless explicitly requested.

---

# 23. Explicitly Out of Scope

The AI coding agent must **not** implement these unless explicitly requested:

1. Voice assistant.
2. Native Android/iOS application.
3. Autonomous unrestricted web browsing.
4. Multi-agent architecture beyond the required LangGraph workflow.
5. Face recognition.
6. Attendance tracking hardware.
7. College ERP replacement.
8. Payment systems.
9. Full LMS functionality.
10. Automatic submission of assignments/exams.
11. Automatic academic decision-making.
12. Social/community features.
13. Real-time classroom monitoring.
14. Complex recommendation engines unrelated to study planning.
15. Blockchain.
16. Cryptocurrency.
17. Fine-tuning an LLM.
18. Training a custom foundation model.
19. Autonomous email sending unless explicitly added as a tool requirement.
20. Features that are not directly related to the defined academic-assistant workflow.

---

# 24. Non-Goals

The assistant is not intended to:

- Replace teachers.
- Make official academic decisions.
- Invent college regulations.
- Guarantee academic outcomes.
- Act as an unrestricted general-purpose agent.
- Modify college records.
- Perform actions outside explicitly registered tools.

---

# 25. Definition of Done

The MVP is complete only when all of the following work:

- [ ] College PDFs can be ingested.
- [ ] Document chunks are stored in pgvector.
- [ ] Semantic retrieval works.
- [ ] RAG answers are grounded in retrieved documents.
- [ ] Answers display sources.
- [ ] Follow-up questions preserve context.
- [ ] LangGraph routes requests.
- [ ] Calculator tool works.
- [ ] Study plans can be generated.
- [ ] Study plans are validated.
- [ ] Existing plans can be modified.
- [ ] Unknown knowledge-base questions are handled safely.
- [ ] Basic LLM vs RAG evaluation can be run.
- [ ] Chat UI works.
- [ ] Study planner UI works.
- [ ] Docker Compose starts the application.
- [ ] Errors are handled cleanly.
- [ ] Secrets are environment-based.
- [ ] Tests cover the main workflows.

---

# 26. Architecture Principle

Use the following separation:

```text
Frontend
    ↓
API layer
    ↓
Application services
    ↓
LangGraph orchestration
    ↓
LangChain components
    ↓
RAG / Tools / Planner
    ↓
Database / External APIs
```

Do not place business logic directly inside frontend components.

Do not place all logic inside one agent prompt.

Do not implement the entire system as a single `agent.py` file.

---

# 27. AI Coding Agent Rules

The coding agent must:

1. Read `scope.md` before implementing features.
2. Read `phases.md` before starting implementation.
3. Implement phases sequentially.
4. Finish and test the current phase before moving to the next.
5. Avoid implementing out-of-scope features.
6. Prefer small, composable services.
7. Keep provider-specific code isolated.
8. Use environment variables for configuration.
9. Write tests for important deterministic logic.
10. Update documentation when architecture changes.
11. Never silently expand the project scope.
12. Never replace deterministic validation with an LLM when deterministic validation is practical.
13. Never fabricate missing college information.
14. Never hard-code API keys, credentials, or secrets.
15. Preserve existing working functionality when adding features.

---

# 28. Configuration Requirements

Configuration should be centralized.

Example environment variables:

```text
LLM_PROVIDER=
LLM_MODEL=
LLM_API_KEY=

EMBEDDING_PROVIDER=
EMBEDDING_MODEL=
EMBEDDING_API_KEY=

DATABASE_URL=

VECTOR_COLLECTION=
RETRIEVAL_TOP_K=
RETRIEVAL_SCORE_THRESHOLD=

CALENDAR_PROVIDER=
CALENDAR_API_KEY=
```

Do not scatter configuration constants across the codebase.

---

# 29. Final User Workflow

The complete intended workflow is:

```text
Student opens application
        ↓
Starts conversation
        ↓
Asks academic question
        ↓
LangGraph analyzes intent
        ↓
RAG retrieves college documents
        ↓
Context is validated
        ↓
LLM generates grounded answer
        ↓
Sources displayed
        ↓
Student asks follow-up
        ↓
Conversation context is used
        ↓
Student requests study plan
        ↓
Planner generates structured plan
        ↓
Plan validator checks constraints
        ↓
Plan displayed
        ↓
Student modifies plan
        ↓
LangGraph updates existing plan
        ↓
Plan validator checks it again
        ↓
Updated plan displayed
```

This workflow represents the core product. Features outside this workflow should not be added without explicit scope approval.
