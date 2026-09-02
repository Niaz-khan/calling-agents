# Onboarding & Optional-Phone Architecture

This document captures how the platform should onboard a new business and why the
**phone number is an optional, upgradeable channel** — never a hard requirement for
signing up. It describes the current state, the intended onboarding flow, and the
work needed to ship the guided setup experience.

---

## 1. Design principle

```
Organization
     │
     ├── Agents
     │
     ├── Deployments
     │      └── Website (widget)
     │
     ├── Phone Numbers
     │      └── Voice
     │
     ├── Knowledge
     ├── Services
     ├── Customers
     ├── Appointments
     └── Conversations
```

Channels are **capabilities of the organization**, not requirements of an agent.

- Phone is optional.
- Agent is the core.
- Widget and phone are independent channels.
- Organization is the isolation boundary.
- Infrastructure (backend, Twilio account, LLM key) is shared centrally.

This makes the SaaS easier to sell: a customer starts with a cheap/free website
agent and upgrades to voice later.

---

## 2. Current state (verified)

The backend already supports the optional-phone model with **no forced telephony**:

- `Agent` (apps/agents/models.py) has no phone dependency — an agent can exist with
  only a `system_prompt` and be used for website chat.
- `AgentDeployment` (channel `website`/`api`/`phone`/...) is created independently of
  any `PhoneNumber`.
- `PhoneNumber` (apps/telephony/models.py) links `organization → agent` and is created
  only when a business actually wants voice.
- Every resource is scoped by `organization`, so an org that never configures a phone
  is fully functional, and no org can see another's data.

Audit result: **a business can operate website‑only with zero telephony today.** No code
path forces a phone number during registration, agent creation, or deployment creation.

---

## 3. Intended onboarding flow

```text
Create Account
      ↓
Create Business / Organization
      ↓
Choose channels
 ┌───────────────┬───────────────┐
 │ Website Agent │ Phone Agent   │
 │      ✅       │     ⬜        │
 └───────────────┴───────────────┘
      ↓
Configure AI Agent
      ↓
Add Knowledge / Services
      ↓
Deploy
```

Example outcomes:

**Business A — Website only**

```text
Organization
 ├── Agent
 ├── Knowledge Base
 ├── Services
 ├── Customers
 └── Website Deployment
```

**Business B — Phone + Website**

```text
Organization
 ├── Agent
 ├── Knowledge Base
 ├── Services
 ├── Customers
 ├── Website Deployment
 └── Phone Number
       └── Twilio/Telnyx
```

Key messaging that drives the flow:

> Start with your website AI agent. Add a business phone number whenever you're ready.

---

## 4. Onboarding wizard (the build)

A multi-step wizard that runs right after signup (i.e. when a user has an org but no
agent yet). Steps:

1. **Welcome / choose channels**
   - Website (always offered)
   - Phone (optional; "Add phone number anytime" note)
2. **Create your agent**
   - Name, description, system prompt
   - Template presets per industry (real estate, dental, etc.)
3. **Add services** (optional)
   - Services used for appointment availability/booking
4. **Add knowledge** (optional)
   - Upload docs/PDFs for RAG
5. **Deploy**
   - If website chosen → create `AgentDeployment(channel=website)` → show install snippet
   - If phone chosen → guide to Phone Numbers provisioning (Twilio/Telnyx)
6. **Done → Dashboard**
   - On completion the wizard marks the org as onboarded, shows a brief success plus the
     install snippet, then **automatically redirects to the dashboard** (after ~5s, or
     immediately via the "Go to dashboard" button). The redirect guard will not re-trigger.

The wizard should only appear when the org has **no agents** (first-time onboarding),
and should be skippable/dismissible.

---

## 5. Backend work needed

The backend largely supports the flow already. Minimal additions:

- **Agent template presets** — optional seed endpoint or static list in frontend for
  industry-specific system prompts.
- **Onboarding progress** (optional) — a flag on `Organization` to track whether the
  initial setup wizard has been completed, so the dashboard can redirect to it once.
- Confirm the wizard's create-calls map cleanly to existing endpoints:
  - `POST /agents`
  - `POST /services`
  - `POST /knowledge` (upload)
  - `POST /deployments` (channel `website`)
  - `POST /phone-numbers` (only if phone chosen)

No schema migration is strictly required unless we add the onboarding-complete flag.

---

## 6. Frontend work needed

- New **Onboarding wizard** page/flow (`/app/onboarding`) invoked after registration.
- Route guard: redirect to onboarding when org has zero agents and onboarding not
  completed; allow "Skip for now".
- Stepper UI: choose channels → agent → services → knowledge → deploy.
- Install-snippet step for website deployments (already generated on the
  deployment detail page; reuse it).
- Industry template presets.

---

## 7. Landing page messaging

Update the public landing copy to emphasize optional phone:

- Hero sub-line already reads "Answer calls, chat with website visitors…" — keep.
- Add an explicit "Start with the website agent, add a phone when ready" message.
- Pricing should separate a website-only tier from a phone tier (see next section).
- FAQ already covers "Can it answer phone calls?" ("Once a phone number is connected…")
  and "Can it work on my website?" — keep, and consider an added FAQ:
  "Do I need a phone number to use the website agent?" → "No. Website is the fastest
  way to start; add a phone number anytime."

---

## 8. Pricing / plans

Separate website-only from phone-enabled tiers. Example:

| Tier | Website | Phone | Notes |
| ---- | ------- | ----- | ----- |
| Starter | ✅ | ❌ (add‑on) | 1 agent, booking, knowledge |
| Growth | ✅ | ✅ | phone add-on / bundled minutes |
| Business | ✅ | ✅ | multiple agents, advanced knowledge |
| Enterprise | ✅ | ✅ | custom |

Billing is not implemented yet (marked low priority). Recommended sequencing: ship
the onboarding wizard and messaging first, then add subscription plans.

---

## 9. Recommended build order

1. ✅ Verify phone is optional (done — audit clean)
2.  Onboarding wizard (highest value)
3.  Landing page messaging
4.  Billing / plans (lowest priority, needs infra decision)

---

## 10. Out of scope / not yet

- Billing/payment processor integration
- Phone provisioning inside the wizard (just a guided link to Phone Numbers for now)
- Real-time presence / analytics on the widget
