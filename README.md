# Lead Search Agent

**Local-first AI prospecting and human-approved outreach for focused B2B campaigns.**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Runtime-Docker%20Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-See%20LICENSE-6B7280)](LICENSE)

Lead Search Agent is an open-source platform for research-driven B2B prospecting. It combines deterministic qualification, public-web evidence, local AI orchestration, and a human approval workflow in one deployable application.

**Repository:** [github.com/kandarpa02/lead_agent](https://github.com/kandarpa02/lead_agent)

## Contents

- [Overview](#overview)
- [Capabilities](#capabilities)
- [Workflow](#workflow)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Configuration](#configuration)
- [API](#api)
- [Safety and operating boundaries](#safety-and-operating-boundaries)
- [Development](#development)
- [Operations and troubleshooting](#operations-and-troubleshooting)
- [Production deployment](#production-deployment)
- [License](#license)

## Overview

Lead Search Agent turns a campaign brief into an evidence-backed prospecting workflow. It researches public business websites and search results, scores leads against a transparent qualification matrix, identifies growth opportunities, and creates channel-specific outreach drafts for review.

The application uses [FastAPI](https://fastapi.tiangolo.com/), PostgreSQL, and the OpenAI Agents SDK. Connect any OpenAI-compatible model API from the dashboard by entering its base URL and API key, then choose an available model.

## Capabilities

- Builds a structured campaign brief from targeting criteria and an optional AI-assisted chat.
- Discovers public prospects using industry, location, growth-signal, and social-profile search patterns.
- Stores source URLs and research evidence alongside each lead.
- Applies an eight-factor qualification model and assigns `HOT`, `WARM`, `COLD`, or `SKIP` priority.
- Produces a lead audit with observations, opportunity gaps, offer angles, and personalization notes.
- Drafts outreach for Instagram, LinkedIn, Facebook, and email.
- Provides a dashboard for lead status, evidence, activities, follow-ups, and draft approvals.
- Sends approved email drafts through Gmail when Gmail OAuth is configured.

## Workflow

```text
Workspace setup
	 -> Campaign brief and targeting
	 -> Public-web research
	 -> Evidence-backed lead qualification
	 -> Lead audit and opportunity analysis
	 -> Channel-specific draft generation
	 -> Human review and approval
	 -> Manual social sending or optional Gmail delivery
	 -> Contact history and follow-up tracking
```

## Architecture

```text
Browser
	|
	v
FastAPI API (:8000) ---- PostgreSQL (:5432)
	|                         ^
	|                         |
	+---- durable campaign queue ---- Worker
	|
	+---- OpenAI-compatible HTTP ---- configured AI API
```

The Compose stack contains the API, background worker, and PostgreSQL. The API and worker use the provider settings saved through the dashboard.

## Prerequisites

Install the following before starting:

- [Docker Desktop](https://docs.docker.com/desktop/) with Compose enabled
- An API key for an OpenAI-compatible model provider
- Git

The documented path uses Docker for the application and database. A local Python environment is only needed for development commands such as tests and linting.

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/kandarpa02/lead_agent.git
cd lead_agent
```

### 2. Configure the application

Create a `.env` file in the repository root for application-level settings. Provider credentials are added in the dashboard and stored with the application configuration.

```dotenv
AI_TIMEOUT_SECONDS=90
```

Useful settings:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AI_TIMEOUT_SECONDS` | `90` | AI provider request timeout |
| `DATABASE_URL` | Compose-managed PostgreSQL URL | SQLAlchemy database connection |
| `GMAIL_CREDENTIALS_FILE` | `credentials.json` | Google OAuth client file for optional email sending |
| `GMAIL_TOKEN_FILE` | `token.json` | Local Gmail OAuth token cache |

Do not commit `.env`, Google client secrets, OAuth tokens, or other credentials.

### 3. Build and start the stack

From the repository directory:

```bash
docker compose up --build
```

On the first run, the API container applies all Alembic migrations before starting FastAPI. The worker waits for the database and API health checks, then begins consuming queued campaign runs.

### 4. Open the dashboard

Choose **AI Provider**, enter an OpenAI-compatible API base URL (for example, `https://api.openai.com/v1`) and API key, then connect. The Models drawer lists models returned by the provider; select one before using AI features.

Visit [http://localhost:8000](http://localhost:8000) and complete the workspace setup wizard. The API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs), and health endpoints are available at [http://localhost:8000/health](http://localhost:8000/health) and [http://localhost:8000/health/ready](http://localhost:8000/health/ready).

### 6. Run your first campaign

1. Save your business profile in the workspace setup screen.
2. Create a campaign with a niche, location, country, budget, lead count, and primary channel.
3. Use the campaign chat assistant to refine the brief, or edit the generated brief directly.
4. Start the campaign and monitor its status in the dashboard.
5. Review evidence, qualification scores, audits, and drafts.
6. Approve and revise drafts before contacting a prospect.
7. Send social messages manually. Approved email drafts can be sent through Gmail when configured.

## Configuration

### AI provider connectivity

Check that the configured base URL is reachable from both the API and worker containers, the API key is valid, and the provider exposes the OpenAI-compatible models endpoint. Use the Models drawer to refresh the provider's model list.

### Optional Gmail delivery

Email delivery is disabled until Google OAuth is configured. To enable it:

1. Create a Google Cloud project and enable the Gmail API.
2. Create an OAuth client for a desktop application.
3. Download the client file as `credentials.json` in the repository root, or set `GMAIL_CREDENTIALS_FILE` to its path.
4. Approve the Gmail authorization flow the first time an approved email is sent.
5. Keep the generated `token.json` private and outside source control.

The application requests the `gmail.send` scope and only sends drafts that have passed the in-app approval step.

## API

The frontend uses the FastAPI JSON API. The most important endpoints are:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` / `PUT` | `/api/ai/provider` | Read provider status or connect an OpenAI-compatible API endpoint |
| `GET` | `/api/ai/models` | Fetch the connected provider's available models |
| `PUT` | `/api/ai/model` | Select the model used by AI features |
| `GET` / `PUT` | `/api/workspace` | Read or save the local workspace profile |
| `POST` | `/api/campaigns` | Create a campaign |
| `GET` | `/api/campaigns` | List campaigns |
| `POST` | `/api/campaigns/{id}/messages` | Refine a campaign brief with the assistant |
| `PUT` | `/api/campaigns/{id}/brief` | Save a campaign brief |
| `POST` | `/api/campaigns/{id}/run` | Queue research and drafting |
| `GET` | `/api/campaigns/{id}/dashboard` | Read campaign metrics and current run state |
| `GET` | `/api/campaigns/{id}/leads` | List campaign leads |
| `GET` | `/api/campaigns/{id}/drafts` | List generated outreach drafts |
| `POST` | `/api/drafts/{id}/approval` | Approve or reject a draft |
| `POST` | `/api/drafts/{id}/revise` | Request a draft revision |
| `POST` | `/api/drafts/{id}/send` | Send an approved email through Gmail |
| `POST` | `/api/drafts/{id}/mark-contacted` | Record manually sent outreach |

Interactive OpenAPI documentation is generated at `/docs`.

## Safety and Operating Boundaries

- Research is limited to public HTTP(S) web content and explicit web tools.
- Retrieved web content is treated as evidence, not as instructions to the agent.
- Instagram, LinkedIn, and Facebook messages are never sent by API or browser automation.
- Human approval is required before a draft can be marked contacted or sent.
- The system sends model prompts to the configured provider. Review that provider's data handling and privacy terms.
- Provider API keys are never returned by the application API. Protect access to the application database and deployment.
- API authentication, TLS termination, secret management, backups, and rate limiting must be added before exposing this reference deployment to the public internet.

## Data and Persistence

PostgreSQL data is stored in the named `postgres-data` Docker volume. The repository's `data/` directory is mounted into the API and worker containers for local application data. Stop the stack without removing volumes to preserve state:

```bash
docker compose down
```

To remove the database and start over, explicitly remove the named volume:

```bash
docker compose down -v
```

This permanently deletes local PostgreSQL data.

## Development

Create a virtual environment and install development dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Run the test suite and linter:

```bash
pytest
ruff check .
```

Run the API without Docker when using a local database:

```bash
uvicorn app.main:app --reload
```

For a local SQLite development database, omit `DATABASE_URL`. Configure the model provider through the dashboard after starting the application.

## Operations and Troubleshooting

View service logs:

```bash
docker compose logs -f api worker db
```

Rebuild after dependency or source changes:

```bash
docker compose up --build
```

Check service state:

```bash
docker compose ps
curl http://localhost:8000/health/ready
```

Common issues:

| Symptom | Check |
| --- | --- |
| Model request fails | Provider base URL, API key, model availability, and configured request timeout |
| Worker does not start | `docker compose logs worker`; confirm the API and database health checks pass |
| Port `8000` is busy | Stop the conflicting process or change the host side of the Compose port mapping |
| Data disappears unexpectedly | Avoid `docker compose down -v`; it deletes the PostgreSQL volume |
| Gmail send fails | Confirm OAuth files, Gmail API enablement, and the authorization scope |

## Production Deployment

This repository is designed to be easy to demonstrate locally and straightforward to harden for deployment. Before serving real users or exposing it publicly:

- Put the API behind a reverse proxy with HTTPS.
- Add authentication and authorization to the API and dashboard.
- Move secrets to a managed secret store and rotate them regularly.
- Use a managed PostgreSQL instance with automated backups and tested restores.
- Pin and scan the application image and Python dependencies.
- Add request, worker, model, and database metrics with alerting.
- Configure structured logs and centralized log retention.
- Restrict outbound research traffic and apply provider-aware rate limits.
- Add per-workspace isolation, audit-log retention, and privacy/data-deletion procedures.
- Run migrations as a controlled release step rather than relying only on container startup.

## License

See [LICENSE](LICENSE).