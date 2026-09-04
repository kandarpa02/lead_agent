# Sales Agent

An Ollama-backed, OpenAI Agents SDK sales workflow. A campaign is persisted, researched on the public web, converted into verified lead records and email drafts, paused for human review, and sent through Gmail only after approval.

## Workflow

```text
POST campaign
	-> POST /api/campaigns/{id}/run
	-> Agents SDK research agent calls public web tools
	-> leads and evidence are saved
	-> Agents SDK email agent creates drafts
	-> drafts are saved as Pending Approval
	-> POST /api/drafts/{id}/approval
	-> POST /api/drafts/{id}/send
	-> Gmail API sends and records the provider message ID
```

The model runtime is Ollama through its OpenAI-compatible `/v1` endpoint. The OpenAI Agents SDK supplies `Agent`, `Runner`, function tools, structured output, and orchestration. OpenAI-hosted models are not required for this configuration, and tracing is disabled so local Ollama runs do not upload traces.

## Run locally

1. Copy `.env.example` to `.env` and select a model installed in Ollama.
2. Install the project: `pip install -e ".[dev]"`.
3. Pull the model: `ollama pull gpt-oss:20b-cloud` (or your configured model).
4. Start the API: `uvicorn app.main:app --reload`.
5. Open `http://localhost:8000/docs`.

The same services can run with `docker compose up --build`. The SQLite database is stored in `data/`, and the Ollama model cache is stored in a named Docker volume.

## Campaign API

Create a campaign with `POST /api/campaigns`, then run it with `POST /api/campaigns/{campaign_id}/run`. The run searches public web results and fetches public business websites. It records only leads with a public email address as email drafts; leads without email remain discoverable through the campaign lead records once the UI is added.

Review drafts with `GET /api/campaigns/{campaign_id}/drafts`. Approve an unchanged or edited draft:

```json
{
	"action": "approve",
	"subject": "A thought for your social content",
	"body": "Approved email body"
}
```

Then call `POST /api/drafts/{draft_id}/send`. The API rejects every draft that does not have an approval record with action `approve`.

## Gmail setup

Create a desktop OAuth client in Google Cloud, enable the Gmail API, download the client JSON to the configured credentials path, and make sure the OAuth scope allows `gmail.send`. The first send opens a local OAuth consent flow and stores the refresh token in the configured token path. Never commit either file.

## Boundaries

- Ollama is the only model provider; there is no cloud-model fallback.
- Web access is implemented as explicit Agents SDK function tools and is restricted to public HTTP(S) research.
- Web content is evidence, never instructions to the agent.
- Human approval is mandatory before Gmail sending.
- Alembic migrations run automatically in Compose. The worker consumes durable queued campaign runs and the browser dashboard provides campaign creation and draft approval.