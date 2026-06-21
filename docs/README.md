# Documentation Index

This folder is organized by purpose:

- `reference/` for stable background material and domain explanations.
- `roadmap/` for implementation plans and phased delivery docs.
- `audits/` for review findings and historical analyses.
- `ui-help.json` for the canonical panel help text, field tooltips, and metric/definition copy used by the app.

## Reference

- [Biology primer](./biology-primer.md)
- [UI help content](./ui-help.json)

The UI help catalog is intentionally kept in one file so the app can render panel help, field definitions, metric explanations, candidate gene hover text, and pathway-node guidance from a single source of truth.

The AI chatbot is not stored in this file. It is a runtime feature backed by the app's `/api/ai/chat` endpoint, the current simulation context, and a local Ollama model running on the backend machine.

## Deployment Prep

Docker scaffolding lives at the repo root:

- [`docker-compose.yml`](docker-compose.yml)
- [`backend/Dockerfile`](backend/Dockerfile)
- [`frontend/Dockerfile`](frontend/Dockerfile)
- [`backend/fly.toml`](backend/fly.toml)
- [`frontend/fly.toml`](frontend/fly.toml)
- [Fly deployment plan](./roadmap/fly-deployment.md)

The current compose file is intended for local orchestration and keeps the frontend and backend split cleanly for Fly.io deployment work.

## Roadmap

- [Research roadmap](./research-roadmap.md)
- [Database-backed simulator plan](./database_backed_simulator_plan.md)
- [Phase 1 database integration](./phase1_database_integration.md)

## Audits

- [Hardcoded model audit](./hardcoded_model_audit.md)
