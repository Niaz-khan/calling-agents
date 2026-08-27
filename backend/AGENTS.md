# AGENTS.md

## AI Call Agent — Development Instructions

This file contains the rules and instructions that AI coding assistants must follow when working on this repository.

Before making any changes, read:

```text
AI-CALL-AGENT.md
````

`AI-CALL-AGENT.md` describes the overall product vision, architecture, roadmap, current development phase, and long-term goals.

This file describes **how code should be written and changed**.

---

# 1. Project Overview

This repository contains a production-oriented AI Call Agent platform.

The platform will eventually allow businesses to create AI-powered phone agents capable of:

* Receiving phone calls
* Understanding speech
* Conversing naturally with customers
* Answering business questions
* Using backend tools
* Booking appointments
* Managing customers
* Transferring calls to humans
* Maintaining call history
* Storing transcripts
* Providing analytics

Current development is focused on the **backend and text-based AI agent**.

Do NOT jump directly to voice/telephony unless explicitly instructed.

---

# 2. Current Development Phase

Current phase:

```text
Phase 3 — AI Agent
```

Current priority:

```text
LLM Tool Calling
```

Immediate tools:

```text
check_appointment_availability
book_appointment
```

The immediate objective is to make the following workflow work:

```text
User Message
     |
     v
AI Agent
     |
     v
LLM
     |
     +---- normal response
     |
     +---- tool call
              |
              v
        Backend Tool
              |
              v
          Database
              |
              v
        Tool Result
              |
              v
             LLM
              |
              v
        Final Response
```

---

# 3. Golden Rule

## Do not break working functionality to implement future functionality.

Make small, incremental changes.

Do not rewrite the entire application unless explicitly requested.

Do not replace working architecture simply because another architecture is possible.

---

# 4. Before Changing Code

Before modifying anything:

1. Read `AI-CALL-AGENT.md`
2. Inspect the existing project structure
3. Identify the relevant route/service/model/schema
4. Read the existing implementation
5. Understand how the current feature works
6. Make the smallest change necessary

Do not assume files or functions exist.

Do not invent architecture without checking the repository first.

---

# 5. Technology Stack

Current backend stack:

```text
Python
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Pydantic
JWT
Docker
Docker Compose
```

AI layer:

```text
LLM provider abstraction
System prompts
Conversation history
Tool/function calling
```

Future:

```text
Telephony
Speech-to-Text
Text-to-Speech
Redis
RAG
Vector database
Frontend dashboard
```

Future technologies should not be introduced prematurely.

---

# 6. Project Architecture

Prefer this general architecture:

```text
app/
│
├── ai/
│   ├── provider.py
│   ├── prompts.py
│   ├── agent.py
│   └── tools.py
│
├── api/
│   └── routes/
│       ├── auth.py
│       ├── agents.py
│       ├── chat.py
│       └── calls.py
│
├── auth/
│   ├── dependencies.py
│   └── security.py
│
├── models/
│
├── schemas/
│
├── services/
│
├── database.py
├── config.py
└── main.py
```

The exact structure may differ from this.

Always inspect the actual repository before creating files.

---

# 7. Separation of Responsibilities

Keep responsibilities separated.

## API Routes

Routes should:

* Validate HTTP input
* Authenticate users
* Authorize resources
* Call services
* Return API responses

Routes should NOT contain large business logic.

Bad:

```python
@router.post("/appointments")
def create_appointment(...):
    # 100 lines of business logic
```

Prefer:

```python
@router.post("/appointments")
def create_appointment(...):
    return appointment_service.create(...)
```

---

# 8. Services

Services contain business logic.

Examples:

```text
services/
    appointments.py
    customers.py
    calls.py
```

Services should handle:

* Availability calculations
* Booking logic
* Customer lookup
* Call operations
* Business rules

---

# 9. Models

SQLAlchemy models represent database entities.

Models should contain:

* Database fields
* Relationships
* Constraints
* Indexes where appropriate

Avoid putting large application workflows inside models.

---

# 10. Schemas

Pydantic schemas represent API input/output.

Keep request and response schemas separate when appropriate.

Example:

```text
AgentCreate
AgentUpdate
AgentResponse
```

Do not expose database internals unnecessarily.

---

# 11. Authentication

Authentication uses JWT.

Protected endpoints must use the authenticated user.

Example:

```text
Authorization: Bearer <token>
```

Never trust:

```json
{
    "owner_id": 1
}
```

from the client for ownership.

Instead:

```text
JWT
 |
 v
current_user
 |
 v
current_user.id
 |
 v
resource.owner_id
```

---

# 12. Authorization

Authentication answers:

> Who is this user?

Authorization answers:

> Is this user allowed to access this resource?

Every user-owned resource must verify ownership.

Example:

```python
agent = get_agent(agent_id)

if agent.owner_id != current_user.id:
    raise HTTPException(
        status_code=404,
        detail="Agent not found",
    )
```

Prefer returning `404` for inaccessible user-owned resources where appropriate so resource existence is not unnecessarily disclosed.

Never allow:

```text
User A
    |
    v
/agents/999
    |
    v
User B's agent
```

---

# 13. Database Rules

PostgreSQL is the source of truth for persistent application data.

Use SQLAlchemy for database access.

Use Alembic for schema migrations.

Never manually modify production database schemas without a migration.

Whenever models change:

```bash
alembic revision --autogenerate -m "describe change"
```

Review the generated migration.

Then:

```bash
alembic upgrade head
```

Do not blindly trust autogenerated migrations.

---

# 14. Migration Safety

Before creating a migration:

```bash
alembic current
```

Check the current database revision.

After creating a migration:

```bash
alembic upgrade head
```

Then verify:

```bash
alembic current
```

Never delete existing migrations simply to make migration problems disappear.

---

# 15. AI Provider Abstraction

The application should not be tightly coupled to one LLM provider.

Prefer:

```text
AI Agent
   |
   v
Provider Interface
   |
   +---- OpenAI
   +---- Anthropic
   +---- OpenRouter
   +---- Local Model
```

The rest of the application should not need to know provider-specific implementation details.

Keep provider-specific code inside the AI provider layer.

---

# 16. System Prompts

Agent system prompts are user/business configuration.

Do not hard-code one business's behavior into application logic.

An agent may contain:

```text
name
description
system_prompt
```

Future configuration may include:

```text
voice
language
timezone
business_hours
greeting
fallback_message
tools
knowledge_base
```

Keep dynamic agent configuration separate from application-level instructions.

---

# 17. Tool Calling

Tool calling is one of the most important architectural components.

The LLM does NOT directly execute tools.

Correct:

```text
LLM
 |
 | tool request
 v
Agent Orchestrator
 |
 v
Tool Registry
 |
 v
Validated Tool
 |
 v
Database / Service
 |
 v
Tool Result
 |
 v
LLM
```

Incorrect:

```text
LLM
 |
 v
Python eval()
 |
 v
Database
```

Never allow arbitrary code execution from LLM output.

---

# 18. Tool Registry

Tools should be explicitly registered.

Example concept:

```python
TOOLS = {
    "check_appointment_availability": check_appointment_availability,
    "book_appointment": book_appointment,
}
```

The exact implementation should follow the existing project architecture.

Unknown tools must be rejected.

Example:

```text
LLM requests:
delete_database

Result:
Tool not available
```

Never dynamically import or execute arbitrary functions based on LLM-generated strings.

---

# 19. Tool Validation

Every tool must validate its arguments.

For example:

```text
book_appointment
```

should validate:

```text
customer_name
customer_phone
start_time
end_time
```

Do not trust LLM-generated arguments.

The LLM can make mistakes.

Backend validation is authoritative.

---

# 20. Appointment Availability

The availability tool must check the database.

Example:

```text
Existing appointment:
14:00 - 15:00

Requested:
14:30 - 15:30

Result:
NOT AVAILABLE
```

Example:

```text
Existing:
14:00 - 15:00

Requested:
15:00 - 15:30

Result:
AVAILABLE
```

Appointments that overlap must be rejected.

---

# 21. Booking Safety

The AI should never claim an appointment was booked unless the backend successfully created it.

Correct:

```text
LLM
 |
 v
book_appointment
 |
 v
Database
 |
 +---- success
 |       |
 |       v
 |     LLM
 |
 +---- failure
         |
         v
        LLM
```

If booking fails:

```text
Database:
booking failed
```

The AI must not say:

> Your appointment is confirmed.

Instead it should explain that the booking could not be completed and continue appropriately.

---

# 22. Conversation Memory

Conversation history should be stored in PostgreSQL.

A call may contain:

```text
user
assistant
tool
assistant
user
assistant
```

Example:

```text
User:
I need an appointment.

Assistant:
What day would you prefer?

User:
Tomorrow.

Assistant:
What time?

User:
3 PM.
```

The AI should receive the relevant conversation context when generating the next response.

---

# 23. Tool Messages

When tool calling is implemented, preserve the tool interaction in conversation history where appropriate.

Example:

```text
user:
I need an appointment tomorrow at 3 PM.

assistant:
tool_call: check_appointment_availability

tool:
available=true

assistant:
3 PM is available. Would you like me to book it?
```

This makes debugging and future transcript generation easier.

---

# 24. API Design

Follow REST conventions.

Examples:

```text
GET
POST
PATCH
DELETE
```

Use appropriate HTTP status codes.

Typical:

```text
200 OK
201 Created
204 No Content
400 Bad Request
401 Unauthorized
403 Forbidden
404 Not Found
422 Validation Error
500 Internal Server Error
```

Do not return `200` for every situation.

---

# 25. Error Handling

Errors should be predictable.

Bad:

```python
except Exception:
    return "Something went wrong"
```

without logging.

Prefer:

```text
Log internal error
Return safe API error
Do not expose secrets
```

Never expose:

* API keys
* Database credentials
* Stack traces
* Internal file paths
* JWT secrets

to API clients.

---

# 26. Logging

Use structured, useful logging.

Log important events such as:

```text
Agent created
Call created
Tool called
Tool failed
Appointment booked
LLM request failed
Database failure
```

Never log:

```text
passwords
JWT tokens
API keys
full sensitive customer information
```

unless explicitly required and appropriately protected.

---

# 27. Environment Variables

Secrets belong in environment variables.

Example:

```env
DATABASE_URL=
JWT_SECRET_KEY=
LLM_API_KEY=
LLM_MODEL=
LLM_BASE_URL=
```

Never commit:

```text
.env
```

with real secrets.

Use:

```text
.env.example
```

for documentation.

---

# 28. Docker

The application should remain Docker-compatible.

Typical development services:

```text
backend
postgres
```

Future:

```text
redis
frontend
nginx
```

Do not add infrastructure unless needed.

---

# 29. Testing

Every major feature should have tests.

Prioritize:

```text
Authentication
Authorization
Agents
Calls
Messages
Appointments
Tool execution
LLM orchestration
```

Especially test failure cases.

Example:

```text
valid booking
invalid booking
overlapping booking
unauthorized booking
unknown tool
invalid tool arguments
LLM failure
database failure
```

---

# 30. Manual API Testing

Swagger should be used during development.

Current API documentation:

```text
http://127.0.0.1:8000/docs
```

Test features through Swagger before connecting the frontend.

Preferred development sequence:

```text
Code
 |
 v
Database
 |
 v
API
 |
 v
Swagger test
 |
 v
Automated tests
 |
 v
Frontend
 |
 v
Telephony
```

---

# 31. Current API

Current important endpoints:

```text
POST   /auth/register
POST   /auth/login

GET    /agents
POST   /agents
GET    /agents/{agent_id}
PATCH  /agents/{agent_id}
DELETE /agents/{agent_id}

POST   /agents/{agent_id}/chat

POST   /calls
POST   /calls/{call_id}/messages

GET    /health
GET    /db-health
```

Do not remove or rename existing endpoints without a strong reason.

---

# 32. Current Call Flow

Current text-based call flow:

```text
Create Call
     |
     v
Call ID
     |
     v
Send Message
     |
     v
Load Call
     |
     v
Load Agent
     |
     v
Load Conversation
     |
     v
AI Agent
     |
     v
LLM
     |
     v
Response
     |
     v
Save Message
```

This should evolve into:

```text
Call
 |
 v
Conversation
 |
 v
AI Agent
 |
 v
LLM
 |
 +---- tool call
 |       |
 |       v
 |     Tool
 |       |
 |       v
 |     Database
 |       |
 |       v
 |     Result
 |       |
 |       v
 |      LLM
 |
 v
Final Response
```

---

# 33. Do Not Implement Yet

Unless explicitly requested, DO NOT prematurely implement:

```text
Telephony
Twilio/Telnyx integration
Speech-to-text
Text-to-speech
Audio streaming
WebRTC
Redis
RAG
Vector database
Frontend dashboard
Analytics
Billing
Multi-tenancy redesign
Complex microservices
Kubernetes
```

The current priority is the text AI agent and tool calling.

---

# 34. Avoid Overengineering

Do not introduce:

```text
microservices
event buses
Kubernetes
multiple databases
complex queues
```

just because they might be useful later.

Start with:

```text
FastAPI
PostgreSQL
AI provider
```

and add components when the product actually requires them.

---

# 35. Code Quality

Prefer:

* Clear names
* Small functions
* Type hints
* Pydantic validation
* Explicit dependencies
* Reusable services
* Clear error handling

Avoid:

* Huge functions
* Global mutable state
* Duplicate business logic
* Magic values
* Hard-coded secrets
* Unnecessary abstractions

---

# 36. Python Style

Use modern Python typing.

Prefer:

```python
def get_agent(agent_id: int) -> Agent:
    ...
```

over untyped functions.

Keep functions focused.

Prefer:

```python
def check_availability(...):
    ...

def create_appointment(...):
    ...
```

instead of one function handling the entire workflow.

---

# 37. Database Access

Do not perform database queries directly inside the LLM provider.

Bad:

```text
LLM Provider
    |
    v
SQLAlchemy
```

Correct:

```text
Agent Orchestrator
    |
    v
Tool
    |
    v
Service
    |
    v
Database
```

---

# 38. AI Agent Responsibilities

The AI agent/orchestrator is responsible for:

* Loading agent configuration
* Loading conversation history
* Calling the LLM
* Detecting tool calls
* Executing approved tools
* Feeding tool results back to the LLM
* Producing final responses
* Persisting conversation events where appropriate

It should NOT directly contain every business rule.

Business rules belong in services/tools.

---

# 39. Tool Responsibilities

Tools are the controlled bridge between AI reasoning and real-world actions.

Example:

```text
LLM:
I need to check availability.

Tool:
check_appointment_availability
```

The tool:

```text
Validate arguments
        |
        v
Call service
        |
        v
Query database
        |
        v
Return structured result
```

---

# 40. Structured Tool Results

Prefer structured results.

Example:

```json
{
  "available": true,
  "requested_start": "2026-08-27T15:00:00",
  "requested_end": "2026-08-27T15:30:00"
}
```

Avoid returning vague strings such as:

```text
"Yeah probably available"
```

Structured results are easier for the LLM and application to handle.

---

# 41. Timezones

Do not silently mix local time and UTC.

Backend storage should have a consistent timezone strategy.

Appointment requests should eventually be interpreted using the business/agent timezone.

Example:

```text
Business timezone:
Asia/Karachi

Customer:
Tomorrow at 3 PM

Backend:
Convert/interpret according to business timezone
```

Do not let the LLM perform critical timezone calculations alone.

The backend should be authoritative.

---

# 42. Data Ownership

All business resources must eventually belong to the correct business/user.

Conceptually:

```text
User
 |
 +-- Agents
 |
 +-- Customers
 |
 +-- Calls
 |
 +-- Appointments
 |
 +-- Knowledge Base
```

Do not create cross-user data access.

---

# 43. Backward Compatibility

When modifying an existing API:

Prefer:

```text
Add
```

over:

```text
Break
```

unless the breaking change is explicitly requested.

If a breaking change is required:

1. Explain it
2. Update schemas
3. Update tests
4. Update documentation
5. Verify existing endpoints

---

# 44. Dependency Management

Do not install a package unless it is actually needed.

Before adding a dependency:

1. Check whether the functionality already exists
2. Check the existing dependency list
3. Determine whether a new package is justified

Avoid dependency bloat.

---

# 45. Git Practices

Make focused commits.

Good:

```text
feat: add appointment availability tool
```

```text
feat: add booking tool
```

```text
test: add appointment overlap tests
```

```text
fix: enforce agent ownership
```

Avoid:

```text
update everything
```

---

# 46. Before Finishing a Task

After implementing a feature:

1. Run tests
2. Check application startup
3. Check database migrations
4. Test the relevant API endpoint
5. Check logs for errors
6. Review changed files
7. Confirm no secrets were added
8. Explain what changed

---

# 47. Recommended Verification

Run:

```bash
pytest
```

If migrations changed:

```bash
alembic check
alembic current
```

If the application is running:

```bash
curl http://127.0.0.1:8000/health
```

Database:

```bash
curl http://127.0.0.1:8000/db-health
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

---

# 48. Definition of Done

A feature is not considered complete merely because the code compiles.

A feature should be:

```text
Implemented
   +
Validated
   +
Tested
   +
Integrated
   +
Documented
```

---

# 49. Current Task Instructions

## DO THIS NOW

Implement the AI tool-calling architecture.

Start with:

```text
check_appointment_availability
```

Then:

```text
book_appointment
```

The implementation should support:

```text
User
 |
 v
LLM
 |
 v
Tool Call
 |
 v
Backend Validation
 |
 v
Database
 |
 v
Tool Result
 |
 v
LLM
 |
 v
Final Response
```

Do not start telephony.

Do not start frontend work.

Do not start RAG.

Do not introduce unnecessary infrastructure.

---

# 50. Expected First Successful Scenario

The following must eventually work:

### Step 1

User sends:

```text
I want an appointment tomorrow at 3 PM.
```

### Step 2

LLM determines that availability must be checked.

### Step 3

LLM requests:

```text
check_appointment_availability
```

### Step 4

Backend validates the request.

### Step 5

Database is checked.

### Step 6

Tool returns:

```json
{
  "available": true
}
```

### Step 7

LLM responds:

```text
3 PM is available tomorrow. Would you like me to book it?
```

### Step 8

User says:

```text
Yes.
```

### Step 9

LLM requests:

```text
book_appointment
```

### Step 10

Backend validates and creates the appointment.

### Step 11

Tool returns success.

### Step 12

LLM responds:

```text
Your appointment has been booked successfully.
```

---

# 51. Important Rule About AI Behavior

The LLM is responsible for:

```text
Understanding
Reasoning
Choosing a tool
Generating natural language
```

The backend is responsible for:

```text
Authentication
Authorization
Validation
Business rules
Database operations
Security
```

Never reverse these responsibilities.

---

# 52. Final Architecture Principle

The project should evolve toward:

```text
                    AI CALL AGENT
                         |
          +--------------+--------------+
          |              |              |
        LLM           Memory          Tools
          |              |              |
          |              |        +-----+-----+
          |              |        |     |     |
          |              |    Booking Customer CRM
          |              |        |
          +--------------+--------+
                         |
                    PostgreSQL
                         |
              +----------+----------+
              |                     |
          Telephony              Dashboard
              |
         STT / TTS
              |
           Customer
```

The AI should be powerful, but the backend must remain in control.

---

# 53. Priority Order

Always prioritize work in this order unless explicitly instructed otherwise:

```text
1. Security
2. Correctness
3. Database integrity
4. AI/tool reliability
5. API stability
6. Tests
7. Performance
8. Developer experience
9. UI/UX
10. Future features
```

---

# 54. Final Instruction

When asked to implement a feature:

```text
READ
  ↓
UNDERSTAND
  ↓
INSPECT EXISTING CODE
  ↓
PLAN
  ↓
MAKE SMALL CHANGE
  ↓
TEST
  ↓
VERIFY
  ↓
REPORT
```

Do not blindly generate large amounts of code.

Do not assume missing requirements.

Do not skip testing.

Do not move to a later roadmap phase while the current phase is incomplete.

The goal is not simply to make the demo work.

The goal is to build a reliable foundation that can eventually become a production AI phone-agent platform.

````

### Your project should now have

```text
ai-call-agent/
│
├── AGENTS.md              ← instructions for coding AI
├── AI-CALL-AGENT.md       ← project vision + roadmap
├── README.md
├── docker-compose.yml
├── alembic.ini
├── .env
├── .env.example
│
└── app/
    ├── ai/
    ├── api/
    ├── auth/
    ├── models/
    ├── schemas/
    ├── services/
    ├── database.py
    ├── config.py
    └── main.py
````