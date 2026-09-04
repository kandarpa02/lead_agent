# Sales Agent

An Ollama-backed, OpenAI Agents SDK sales workflow. A campaign is persisted, researched on the public web, converted into verified leads and Instagram/LinkedIn message drafts, and paused for human review. Social messages are copied and sent manually by the user.

## Workflow

```text
Complete workspace setup in the browser
	-> POST /api/workspace
	-> POST campaign
	-> POST /api/campaigns/{id}/run
	-> Agents SDK research agent calls public web tools
	-> leads, public social URLs, and evidence are saved
	-> Agents SDK channel-specific draft agents create drafts
	-> drafts are saved as Pending Approval
	-> POST /api/drafts/{id}/approval
	-> copy draft and open social profile
	-> POST /api/drafts/{id}/mark-contacted after manual sending
```

The model runtime is Ollama through its OpenAI-compatible `/v1` endpoint. The OpenAI Agents SDK supplies `Agent`, `Runner`, function tools, structured output, and orchestration. OpenAI-hosted models are not required for this configuration, and tracing is disabled so local Ollama runs do not upload traces.

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