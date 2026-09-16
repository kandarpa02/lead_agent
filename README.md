# Lead Search Agent — Autonomous Prospecting & Sales Outreach

An Ollama-backed, OpenAI Agents SDK sales workflow engineered for high-precision B2B lead discovery and personalized outreach. A campaign is initialized with structured targeting and an optional chat brief assistant, researched on the public web across multiple sources, qualified using an 8-factor scoring matrix, audited for growth opportunities, and converted into channel-specific outreach drafts (Instagram, LinkedIn, Facebook, Email) paused for human review.

## Workflow

```text
Complete workspace setup in the browser
	-> POST /api/workspace
	-> Create campaign (optionally refine brief with AI Chat Assistant)
	-> POST /api/campaigns/{id}/run
	-> Agents SDK research agent executes PDF discovery patterns
	-> Public web evidence, social profiles (Instagram, LinkedIn, Facebook, Maps) are stored in ResearchEvidence
	-> Lead qualification matrix calculates 8-factor score & priority (HOT / WARM / COLD / SKIP)
	-> Lead audit profile records observations, missing social elements, and personalized offer angles
	-> Draft agents create channel-specific outreach DMs / Email drafts (Pending Approval)
	-> Human reviews, revises, and approves drafts
	-> Social DMs are copied & sent manually; approved Email drafts can be sent via Gmail API
	-> Mark contacted / record lead activities and manage follow-ups in Lead Tracker
```

The model runtime is Ollama through its OpenAI-compatible `/v1` endpoint. The OpenAI Agents SDK supplies `Agent`, `Runner`, function tools, structured output, and orchestration.

## Features & PDF Methodology Realization

- **AI Campaign Brief Assistant**: Chat interface during campaign initialization to define Ideal Customer Profile, buying signals, excluded types, and custom operator instructions.
- **PDF Discovery Query Builder**: Automated search patterns covering industry tiers, growth signals, city priorities (e.g. Kolkata & major hubs), and multi-channel profile detection.
- **Deterministic 8-Factor Qualification**: Evaluates established history, customer proof, offer quality, active operations, social presence, social opportunity gap, budget/ability to pay, and growth potential.
- **HOT / WARM / COLD / SKIP Prioritization**: Automatically prioritizes high-opportunity leads while skipping non-fits.
- **Full Lead Audit Profile**: Stores what is working, what is missing, social opportunity gaps, recommended offer, and personalization notes.
- **4-Channel Outreach**: Supports Instagram, LinkedIn, Facebook DMs, and Email outreach.
- **Lead Tracker & Operator Dashboard**: Responsive UI with priority chips, search filters, lead detail modal, source evidence links, activity timeline, and follow-up management.

## Boundaries

- Ollama is the model provider; there is no cloud-model fallback.
- Web research is restricted to public HTTP(S) data. Direct social profile inspection and messaging are kept manual to avoid unauthorized platform automation.
- Human approval is mandatory before any message can be marked contacted or sent.
- Alembic migrations run automatically in Compose (`0003_pdf_prospecting_workflow`).

## Run locally

1. Optionally copy `.env.example` to `.env` and choose `OLLAMA_MODEL`.
2. Pull the model in the Ollama volume: `docker compose run --rm ollama ollama pull gpt-oss:20b-cloud`.
3. Start the stack: `docker compose up --build`.
4. Open `http://localhost:8000` and complete the workspace setup wizard.

Compose runs the API, worker, Postgres database, and Ollama. Postgres and the Ollama model cache use named persistent volumes. The API runs Alembic migrations before becoming healthy; the worker starts after the API is ready.

## Campaign API

The browser creates a campaign with Instagram and/or LinkedIn selected, then runs it through `POST /api/campaigns/{campaign_id}/run`. The run searches public web results and fetches public business websites. It records public social profile URLs as lead destinations and creates separate drafts for each selected channel with an available destination.

Review drafts with `GET /api/campaigns/{campaign_id}/drafts`. Approve an unchanged or edited draft:

```json
{
	"action": "approve",
	"subject": "A thought for your social content",
	"body": "Approved email body"
}
```

Edit directly or request a revision through the draft studio. Approve the draft, copy it, open the profile, send it manually, and then call `POST /api/drafts/{draft_id}/mark-contacted`. No Instagram or LinkedIn API is used.

## Boundaries

- Ollama is the only model provider; there is no cloud-model fallback.
- Web access is implemented as explicit Agents SDK function tools and is restricted to public HTTP(S) research.
- Web content is evidence, never instructions to the agent.
- Human approval is mandatory before a social draft can be marked contacted.
- Instagram and LinkedIn sending is manual; there is no social API or browser automation.
- The setup wizard stores one local workspace profile and sends its business context to the drafting agents, never provider credentials.
- Alembic migrations run automatically in Compose. The worker consumes durable queued campaign runs and the browser dashboard provides campaign creation and draft approval.