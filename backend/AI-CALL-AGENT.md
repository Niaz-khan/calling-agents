# AI Call Agent

## Project Version

**Version:** 1.0.0  
**Status:** Active Development  
**Stage:** Backend Foundation → AI Agent → Voice Integration

---

# 1. Project Vision

The goal of this project is to build a production-ready **AI Call Agent platform**.

The platform will allow a business to create an AI-powered phone agent that can:

- Receive incoming phone calls
- Understand callers using speech-to-text
- Have natural conversations using an LLM
- Remember the current conversation
- Answer business-specific questions
- Use tools to perform real actions
- Check appointment availability
- Book appointments
- Cancel appointments
- Look up customers
- Create/update customer information
- Transfer calls to a human when necessary
- Store call history
- Store transcripts
- Track call status and outcomes
- Provide analytics to the business
- Eventually support multiple AI agents per business

The final system should behave like a real human receptionist or business representative rather than a simple chatbot.

---

# 2. Core Product Idea

A business owner should be able to:

1. Create an account
2. Create an AI agent
3. Configure the agent
4. Give the agent business information
5. Connect a phone number
6. Receive customer calls
7. Let the AI handle conversations
8. Allow the AI to perform business actions
9. Review calls and transcripts
10. Monitor performance

Example:

A customer calls a dental clinic.

The AI answers:

> "Hello, thank you for calling ABC Dental Clinic. How can I help you today?"

Customer:

> "I'd like to book an appointment tomorrow afternoon."

The AI determines that an appointment is required.

It checks availability using a backend tool.

If 3:00 PM is available:

> "We have an opening at 3 PM tomorrow. Would you like me to book that for you?"

Customer:

> "Yes."

The AI calls the booking tool.

The backend creates the appointment.

The AI confirms:

> "You're all set. Your appointment is booked for tomorrow at 3 PM."

---

# 3. Important Architectural Principle

The system must separate:

### Conversation

What the AI says and understands.

### Reasoning

What the LLM decides should happen.

### Tools

What the backend is allowed to execute.

### Database

Where business data is stored.

### Telephony

How audio enters and leaves the system.

The LLM must NOT have direct database access.

The architecture should be:

```text
Caller
   |
   v
Telephony Provider
   |
   v
Speech-to-Text
   |
   v
AI Agent
   |
   +---- LLM
   |
   +---- Conversation Memory
   |
   +---- Tools
           |
           +---- Appointments
           +---- Customers
           +---- Calendar
           +---- CRM
           +---- Human Transfer
   |
   v
Text-to-Speech
   |
   v
Telephony Provider
   |
   v
Caller
````

---

# 4. Current Technology Stack

## Backend

* Python
* FastAPI
* SQLAlchemy
* Alembic
* PostgreSQL
* Pydantic
* JWT authentication

## AI

The AI layer should be provider-independent.

Current direction:

* OpenAI-compatible API
* LLM abstraction layer
* Tool/function calling
* System prompts
* Conversation memory

The provider should be replaceable later.

Possible future providers:

* OpenAI
* Anthropic
* Google
* Groq
* OpenRouter
* Local models
* Other OpenAI-compatible providers

The rest of the application should not depend directly on a specific provider.

## Database

PostgreSQL.

## Infrastructure

Development:

```text
Ubuntu
Docker
Docker Compose
PostgreSQL
FastAPI
```

Production will eventually use:

```text
VPS / Cloud
Docker
PostgreSQL
Nginx
HTTPS
Domain
```

## Frontend

A web dashboard will eventually be added.

The dashboard will allow businesses to:

* Manage agents
* Configure agents
* Manage phone numbers
* View calls
* View transcripts
* Manage appointments
* Manage customers
* View analytics
* Configure business hours
* Configure AI behavior

Frontend technology can be finalized later.

---

# 5. Current Backend Architecture

Current approximate structure:

```text
app/
│
├── ai/
│   ├── __init__.py
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
│   ├── user.py
│   ├── agent.py
│   ├── call.py
│   ├── call_message.py
│   └── appointment.py
│
├── schemas/
│   ├── auth.py
│   ├── agent.py
│   ├── call.py
│   ├── chat.py
│   └── appointment.py
│
├── services/
│   └── appointments.py
│
├── config.py
├── database.py
└── main.py
```

This structure can evolve.

Do not reorganize the entire project unless there is a clear architectural reason.

---

# 6. What Has Already Been Completed

## Health checks

Implemented:

```http
GET /
GET /health
GET /db-health
```

Database health is confirmed.

---

# 7. Authentication

Implemented:

```http
POST /auth/register
POST /auth/login
```

JWT authentication is working.

The application uses the authenticated user's identity instead of trusting an `owner_id` supplied by the client.

This is important.

The client must NOT be allowed to create an agent like:

```json
{
    "owner_id": 1
}
```

Instead:

```text
JWT
 |
 v
Authenticated User
 |
 v
Backend determines owner_id
```

---

# 8. Agent Management

Implemented:

```http
GET    /agents
POST   /agents
GET    /agents/{agent_id}
PATCH  /agents/{agent_id}
DELETE /agents/{agent_id}
```

Agents belong to authenticated users.

Example agent:

```text
Name:
AI Receptionist

Description:
Main business receptionist

System Prompt:
You are a professional AI receptionist...
```

Agent ownership must always be enforced.

A user must never be able to access another user's agent by changing an `agent_id`.

---

# 9. Call Management

Implemented:

```http
POST /calls
```

A call currently contains:

```text
id
agent_id
customer_id
caller_number
direction
status
started_at
ended_at
```

Example:

```json
{
    "id": 1,
    "agent_id": 3,
    "customer_id": null,
    "caller_number": "string",
    "direction": "inbound",
    "status": "in_progress"
}
```

This is currently a simulated call.

Real phone integration comes later.

---

# 10. Conversation Management

Implemented:

```http
POST /calls/{call_id}/messages
```

Messages are stored in PostgreSQL.

A conversation looks like:

```text
Call #1

User:
Hello, my name is Ahmed.

Assistant:
Hello Ahmed! How can I help you?

User:
What is my name?

Assistant:
Your name is Ahmed.
```

This gives the AI conversation memory.

---

# 11. Current AI Architecture

The current AI flow is:

```text
API Request
    |
    v
Call
    |
    v
Agent
    |
    v
System Prompt
    |
    v
Conversation History
    |
    v
LLM
    |
    v
AI Response
    |
    v
PostgreSQL
```

The current AI layer contains:

```text
app/ai/provider.py
```

Responsible for communicating with the LLM.

```text
app/ai/prompts.py
```

Contains system prompts.

```text
app/ai/agent.py
```

Responsible for orchestrating the agent.

```text
app/ai/tools.py
```

Will contain tools that the LLM can request.

---

# 12. Current Development Stage

We are currently here:

```text
                    PROJECT
                       |
        +--------------+--------------+
        |              |              |
       Auth          Agents         Calls
        |              |              |
        +--------------+--------------+
                       |
                Conversation
                       |
                       v
                      LLM
                       |
                       v
                  Appointments
                       |
                       v
                 TOOL CALLING
                       |
                       v
                  TELEPHONY
                       |
                       v
                 PRODUCTION
```

The immediate task is:

# Build the Agent Tool System

---

# 13. Immediate Next Goal

The next major feature is LLM tool/function calling.

The AI should be able to decide when a backend action is required.

For example:

Customer:

> I want an appointment tomorrow at 3 PM.

The LLM should recognize:

```text
Intent:
Book appointment

Required information:
date
time
customer
```

Then request:

```text
check_appointment_availability
```

The backend executes the tool.

Example:

```json
{
    "available": true
}
```

The result goes back to the LLM.

Then the LLM can ask:

> 3 PM is available. Would you like me to book it?

After confirmation:

```text
book_appointment
```

is executed.

---

# 14. Tool Calling Architecture

The correct architecture is:

```text
                 LLM
                  |
                  | Tool Request
                  v
             FastAPI Agent
                  |
                  | Validate
                  v
              Tool Layer
                  |
                  v
              PostgreSQL
                  |
                  | Result
                  v
             Tool Layer
                  |
                  v
                 LLM
                  |
                  v
            Final Response
```

The LLM must never directly execute Python functions.

The backend controls execution.

---

# 15. First Tools

The first tools should be:

```text
check_appointment_availability
book_appointment
```

Later:

```text
cancel_appointment
reschedule_appointment
get_customer
create_customer
update_customer
get_business_information
transfer_to_human
send_sms
send_email
```

Tools should be small, deterministic, validated backend functions.

---

# 16. Appointment System

Appointments currently contain:

```text
id
agent_id
call_id
customer_name
customer_phone
start_time
end_time
status
notes
created_at
```

Statuses:

```text
scheduled
cancelled
completed
```

Availability must check overlapping appointments.

Example:

```text
Existing appointment:

14:00 -------- 15:00

Requested:

14:30 -------- 15:30

Result:
NOT AVAILABLE
```

Example:

```text
Existing:

14:00 -------- 15:00

Requested:

15:00 -------- 15:30

Result:
AVAILABLE
```

---

# 17. Appointment Business Rules

Initial prototype:

```text
Appointment duration: 30 minutes

Business days:
Monday-Friday

Business hours:
09:00-17:00

Timezone:
Initially configurable / UTC for backend testing
```

These rules should eventually become agent/business configuration.

Do NOT permanently hard-code them into the LLM prompt.

Future configuration:

```text
Business
 |
 +-- timezone
 +-- business hours
 +-- working days
 +-- appointment duration
 +-- services
```

---

# 18. Future Customer System

Eventually:

```text
Customer
├── id
├── business_id
├── name
├── phone
├── email
├── notes
├── created_at
└── updated_at
```

A phone number should allow the system to recognize returning customers.

Example:

```text
Incoming caller:
+92XXXXXXXXXX

        |
        v

Find customer

        |
        +---- Existing customer
        |
        +---- New customer
```

---

# 19. Future Voice Architecture

After the text agent and tools are stable, add voice.

The final call pipeline should be:

```text
Customer Phone
      |
      v
Telephony Provider
      |
      v
Audio Stream
      |
      v
Speech-to-Text
      |
      v
AI Agent
      |
      +---- Conversation Memory
      |
      +---- LLM
      |
      +---- Tools
      |
      v
Text Response
      |
      v
Text-to-Speech
      |
      v
Audio
      |
      v
Telephony Provider
      |
      v
Customer
```

---

# 20. Telephony

The exact provider will be selected later.

Possible options include:

* Twilio
* Telnyx
* SIP
* Other telephony providers

The application should abstract telephony behind a service interface.

Avoid scattering provider-specific code throughout the application.

Prefer:

```text
app/telephony/
    provider.py
    webhook.py
```

rather than putting Twilio/Telnyx logic directly into business logic.

---

# 21. Real-Time Voice

Eventually the system should support:

```text
Caller speaks
    |
    v
Streaming STT
    |
    v
LLM
    |
    v
Streaming TTS
    |
    v
Caller hears response
```

The goal is low latency.

The AI should not wait for an entire long conversation before responding.

---

# 22. Call Lifecycle

The call lifecycle should eventually look like:

```text
initiated
    |
    v
ringing
    |
    v
in_progress
    |
    +---- completed
    |
    +---- failed
    |
    +---- transferred
    |
    +---- missed
```

Calls should record:

```text
started_at
answered_at
ended_at
duration
status
direction
caller_number
agent_id
customer_id
```

---

# 23. Call Transcript

Each call should eventually have a complete transcript.

Example:

```text
CALL #1023

00:00 Customer:
Hello.

00:01 AI:
Hello, thank you for calling ABC Clinic.

00:05 Customer:
I need an appointment.

00:07 AI:
Sure. What day works best for you?

00:12 Customer:
Tomorrow afternoon.

...
```

The transcript should be linked to the call.

---

# 24. Human Handoff

The AI must know when it should stop handling the call.

Examples:

```text
Customer:
I want to speak to a human.

AI:
Certainly. I'll connect you with a member of our team.
```

Other triggers:

* Angry customer
* Complex request
* Sensitive request
* Repeated misunderstanding
* Business-defined escalation rules

Tool:

```text
transfer_to_human
```

---

# 25. Security Requirements

Security is a core requirement.

Never:

* Trust `owner_id` from the frontend
* Allow users to access another user's agent
* Allow the LLM direct database access
* Store API keys in frontend code
* Commit `.env` to Git
* Trust tool arguments without validation
* Allow arbitrary Python execution through LLM output

Always:

```text
JWT authentication
+
authorization checks
+
input validation
+
database constraints
+
tool validation
```

---

# 26. Environment Variables

Secrets must live in environment variables.

Example:

```env
DATABASE_URL=...

JWT_SECRET_KEY=...

LLM_API_KEY=...

LLM_MODEL=...

LLM_BASE_URL=...
```

Never commit real secrets.

`.env` must be in `.gitignore`.

---

# 27. Production Requirements

Before production deployment, the application needs:

### Backend

* Production ASGI server
* Docker
* Environment-based configuration
* Structured logging
* Error handling
* Health checks
* Database migrations

### Security

* HTTPS
* Secure JWT configuration
* Secret management
* CORS configuration
* Rate limiting
* Input validation
* Authorization

### Database

* PostgreSQL
* Automated backups
* Migration system
* Indexes
* Connection pooling

### Infrastructure

```text
Internet
   |
   v
Nginx
   |
   v
FastAPI
   |
   +---- PostgreSQL
   |
   +---- Redis (future)
   |
   +---- AI Provider
   |
   +---- Telephony Provider
```

---

# 28. Redis / Background Jobs

Redis may eventually be introduced for:

* Background tasks
* Call events
* Rate limiting
* Caching
* Real-time state
* Job queues

Do not introduce Redis prematurely unless a real requirement exists.

---

# 29. Frontend Dashboard

Eventually create a dashboard with:

```text
Dashboard
│
├── Overview
│
├── Agents
│   ├── Create Agent
│   ├── Edit Agent
│   └── Agent Settings
│
├── Calls
│   ├── Call History
│   ├── Call Details
│   └── Transcripts
│
├── Customers
│
├── Appointments
│
├── Phone Numbers
│
├── Knowledge Base
│
└── Settings
```

---

# 30. Agent Configuration

Eventually an agent should have more than just:

```text
name
description
system_prompt
```

Future configuration:

```text
Agent
├── name
├── description
├── system_prompt
├── voice
├── language
├── timezone
├── business_hours
├── appointment_duration
├── greeting
├── fallback_message
├── transfer_number
├── tools
└── knowledge_base
```

---

# 31. Knowledge Base

Eventually businesses should be able to provide:

* PDFs
* Documents
* FAQs
* Website content
* Policies
* Services
* Pricing information

The AI should use RAG when appropriate.

Architecture:

```text
Business Documents
       |
       v
Document Processing
       |
       v
Chunking
       |
       v
Embeddings
       |
       v
Vector Database
       |
       v
Retriever
       |
       v
LLM
```

Do not build the knowledge base before the core agent/tool architecture works.

---

# 32. Analytics

Eventually the dashboard should show:

```text
Total Calls
Answered Calls
Missed Calls
Average Call Duration
AI Resolution Rate
Human Transfer Rate
Appointments Booked
Appointments Cancelled
Customer Satisfaction
```

Potential future metrics:

```text
Average response latency
Tool success rate
Call abandonment rate
Conversion rate
```

---

# 33. Development Roadmap

## Phase 1 — Foundation

* [x] FastAPI
* [x] PostgreSQL
* [x] Docker
* [x] Alembic
* [x] Health endpoints
* [x] Authentication
* [x] JWT
* [x] Agent CRUD
* [x] Agent authorization

## Phase 2 — Conversation

* [x] Calls
* [x] Call messages
* [x] Conversation persistence
* [x] LLM provider abstraction
* [x] Agent prompts
* [x] Basic AI response

## Phase 3 — AI Agent

* [x] Tool framework
* [x] Tool schemas
* [x] Tool execution loop
* [x] Availability tool
* [x] Booking tool
* [x] Appointment validation
* [x] Customer lookup
* [x] Human transfer tool
* [x] Better agent memory

## Phase 4 — Voice

* [x] Telephony provider (Twilio client + TwiML + signature verification)
* [x] Incoming call webhook (`/telephony/webhook/inbound`)
* [x] Call lifecycle (status callback, provider status normalization)
* [x] Speech-to-text (OpenAI-compatible; Groq whisper in staging)
* [x] Text-to-speech (Edge neural voices free provider; OpenAI-compatible also supported)
* [ ] Audio streaming (Twilio Media Streams websocket; Gather-based loop is live)
* [x] Real-time conversation (TwiML speech-gather loop over the text agent)
* [ ] Call recording/transcription (transcript is persisted; provider recording not yet saved)

Staging uses a TwiML `<Gather input="speech">` conversational loop — Twilio
collects each caller utterance and posts it to `/telephony/webhook/gather`,
which runs the agent and answers with TwiML that speaks the reply. No
websocket infrastructure is required. Audio streaming (Media Streams) remains
incremental.

## Phase 5 — Dashboard

* [x] Frontend
* [x] Login
* [x] Agent management
* [x] Call history
* [x] Transcript viewer
* [x] Appointment management
* [x] Customer management
* [x] Analytics

## Phase 6 — Knowledge

* [x] File uploads
* [x] Document processing
* [x] Embeddings
* [ ] Vector database (embedded chunk search is used; no dedicated vector store yet)
* [x] RAG
* [x] Agent knowledge base

## Phase 7 — Production

* [ ] Docker production build
* [ ] Nginx
* [ ] HTTPS
* [ ] Domain
* [ ] Production PostgreSQL
* [ ] Backups
* [ ] Monitoring
* [ ] Logging
* [ ] Rate limiting
* [ ] Security review
* [ ] Load testing

---

# 34. Current Task

## CURRENT PHASE

**Phase 3 — AI Agent**

## CURRENT OBJECTIVE

Build a reliable tool-calling system.

The immediate implementation order is:

```text
1. Tool schema
2. Tool registry
3. LLM tool definitions
4. LLM tool-call detection
5. Backend tool execution
6. Tool result injection
7. Second LLM pass
8. Final response
9. Save all messages
10. Test end-to-end
```

The first tools are:

```text
check_appointment_availability
book_appointment
```

---

# 35. Definition of Done for the Current Phase

The current phase is complete when this works:

Customer:

> I want an appointment tomorrow at 3 PM.

System:

```text
LLM
 |
 +--> check_appointment_availability
 |
 v
Database
 |
 v
available = true
 |
 v
LLM
 |
 v
"3 PM is available. Would you like me to book it?"
```

Customer:

> Yes.

System:

```text
LLM
 |
 +--> book_appointment
 |
 v
Database
 |
 v
appointment created
 |
 v
LLM
 |
 v
"Your appointment has been booked."
```

And PostgreSQL contains the appointment.

---

# 36. Rules for AI Coding Assistants

When working on this project, follow these rules.

### Rule 1

Do not rewrite working code unnecessarily.

### Rule 2

Do not change the database schema without a migration.

### Rule 3

Do not bypass authentication.

### Rule 4

Never trust frontend-provided ownership information.

### Rule 5

Do not give the LLM direct database access.

### Rule 6

All business actions must happen through validated backend tools.

### Rule 7

Do not add telephony until the text-based agent works reliably.

### Rule 8

Do not add RAG until the core agent/tool architecture works.

### Rule 9

Keep AI provider code isolated behind an abstraction.

### Rule 10

Every major feature must be tested through the API before moving to the next layer.

### Rule 11

Prefer small, incremental changes.

### Rule 12

After modifying code:

```bash
pytest
```

and:

```bash
alembic check
```

should eventually be part of the development workflow.

---

# 37. Testing Philosophy

Every feature should first work through Swagger/API.

Example:

```text
Swagger
   |
   v
API
   |
   v
Database
```

Only after that should it be connected to:

```text
Frontend
```

and finally:

```text
Phone
```

This makes debugging much easier.

---

# 38. Final Target Architecture

The final platform should look approximately like:

```text
                         ┌─────────────────┐
                         │     Customer    │
                         │     Phone       │
                         └────────┬────────┘
                                  │
                                  v
                         ┌─────────────────┐
                         │    Telephony    │
                         └────────┬────────┘
                                  │
                              Audio
                                  │
                                  v
                         ┌─────────────────┐
                         │       STT       │
                         └────────┬────────┘
                                  │
                                  v
                    ┌──────────────────────────┐
                    │        AI AGENT          │
                    │                          │
                    │  Prompt                  │
                    │  Memory                  │
                    │  LLM                     │
                    │  Tool Calling            │
                    │  Knowledge/RAG           │
                    └────────────┬─────────────┘
                                 │
                   ┌─────────────┼──────────────┐
                   │             │              │
                   v             v              v
              PostgreSQL      Tools          Vector DB
                   │             │              │
                   │       ┌─────┼─────┐        │
                   │       │     │     │        │
                   │       v     v     v        │
                   │    Booking Customer CRM     │
                   │                            │
                   └────────────┬───────────────┘
                                │
                                v
                              TTS
                                │
                                v
                           Telephony
                                │
                                v
                            Customer


                    ┌─────────────────────┐
                    │   Business Dashboard│
                    ├─────────────────────┤
                    │ Agents              │
                    │ Calls               │
                    │ Customers           │
                    │ Appointments        │
                    │ Transcripts         │
                    │ Analytics           │
                    │ Settings            │
                    └─────────────────────┘
```

---

# 39. Current Status Summary

```text
Backend foundation (Django + DRF)  ████████████████████ 100%
Authentication                      ████████████████████ 100%
Agent management                    ████████████████████ 100%
Call management                     ████████████████████ 100%
Conversation memory                 ████████████████████ 100%
Customer memory                     ████████████████████ 100%
Basic LLM                           ██████████████████░░  90%  (live call pending a real API key)
Tool calling (5 tools)              ████████████████████ 100%
Call intelligence (summary/outcome) ████████████████████ 100%
Appointments                        ████████████████████ 100%
Dashboard (React)                   ████████████████████ 100%
RAG (knowledge base)                ████████████████████ 100%
Vector database                     ░░░░░░░░░░░░░░░░░░░░   0%
Voice / telephony                   ░░░░░░░░░░░░░░░░░░░░   0%
Production                          ░░░░░░░░░░░░░░░░░░░░   0%
```

---

# 40. Immediate Next Action

LLM tool calling is implemented and tested (eligibility check, booking, customer
lookup, knowledge search, human transfer plus call summary/outcome and customer
memory). Three things remain:

1. Validate the live end-to-end flow with a real LLM API key
   (the current ``LLM_API_KEY`` is a placeholder).
2. Optionally import existing FastAPI data:
   ``manage.py import_legacy_users`` then ``manage.py import_legacy_data``.
3. Only then begin Phase 4 — the voice/telephony layer. Per AGENTS.md, it is
   out of scope until explicitly requested.

````

### Save it

From your project root:

```bash
nano AI-CALL-AGENT.md
````

Paste the content, save with:

```text
CTRL + O
ENTER
CTRL + X
```

Then:

```bash
git add AI-CALL-AGENT.md
git commit -m "docs: add AI call agent project roadmap"
```
