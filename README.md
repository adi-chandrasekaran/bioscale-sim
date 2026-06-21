# BioScale Simulator

A student-friendly computational biology MVP that links:

`Disease Discovery -> Candidate Gene -> Mutation -> Protein -> Pathway -> Cell -> Population -> Ecosystem`

This project is intentionally modular. Each layer is a small scientific model with structured inputs and outputs, so you can expand one layer at a time into a research paper.

## What it does

The default demo models a cancer/p53 case study:

- Disease discovery ranks TP53 and related genes.
- A mutation engine interprets TP53 p.R175H.
- A protein layer converts mutation effects into activity/stability/binding parameters.
- A pathway simulator propagates the effect through the p53 pathway.
- A cell simulator converts pathway disruption into phenotype probabilities.
- A population simulator models normal vs mutated cell expansion.
- An ecosystem simulator adds immune pressure, inflammation, nutrient stress, and tissue burden.

## Project structure

```text
backend/
  app/
    main.py                FastAPI app
    models.py              Shared typed data models
    services/              One biological layer per file
    adapters/              Optional real-world API connector stubs
  data/knowledge_base.json Demo knowledge base
  tests/                   Pytest tests
  pyproject.toml           Ruff and pytest configuration
frontend/
  src/                     React + TypeScript UI
  package.json             Vite app
docs/
  README.md                Documentation index

See also:

- [Agent constitution](./AGENTS.md)
- [Documentation index](./docs/README.md)
```

## Run backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Test backend:

```bash
cd backend
pytest -q
```

For local Python linting, install the dev dependency listed in `backend/requirements-dev.txt`
and run `ruff check .` from `backend/`.

If you want the AI chatbot to work locally, install Ollama and start a model:

```bash
ollama serve
ollama pull llama3.2
```

Then create `backend/.env` from `backend/.env.example` and ensure it contains:

```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

If you are using Docker Compose with the bundled Ollama service, set:

```bash
OLLAMA_BASE_URL=http://ollama:11434
```

## Run frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the local Vite URL, usually `http://localhost:5173`.

Type-check the frontend with:

```bash
cd frontend
npm run lint
```

## API

### Health

```bash
curl http://localhost:8000/api/health
```

### Catalog

```bash
curl http://localhost:8000/api/catalog
```

### Run simulation

```bash
curl -X POST http://localhost:8000/api/simulate \
  -H "Content-Type: application/json" \
  -d '{"disease":"cancer","gene":"TP53","mutation":"p.R175H","steps":60,"initial_mutated_fraction":0.02}'
```

## Docker

The repository includes Docker scaffolding for local orchestration:

```bash
docker compose up --build
```

That starts:

- `backend` on `http://localhost:8000`
- `frontend` on `http://localhost:5173`

If you want a local Ollama container instead of the host process, start the optional profile:

```bash
docker compose --profile ollama up --build
```

Then pull the model inside the Ollama container or on your host machine.

If you prefer to use a host-run Ollama with Docker Compose, set:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## Fly.io Deployment

The repo is also prepared for Fly.io deployment with GitHub Actions.

- Backend Fly config: [`backend/fly.toml`](backend/fly.toml)
- Frontend Fly config: [`frontend/fly.toml`](frontend/fly.toml)
- Deployment guide: [`docs/roadmap/fly-deployment.md`](docs/roadmap/fly-deployment.md)

The planned CI/CD flow is:

1. run backend tests and frontend build on every push and pull request to `main`
2. deploy backend and frontend to Fly on pushes to `main`
3. keep Ollama local-only for now, or replace it later with a hosted model service if you want production AI

## Research angle

Possible paper title:

**A Modular Multi-Scale Framework for Simulating Disease-Associated Genetic Perturbations from Protein Function to Ecosystem-Level Dynamics**

The MVP does not claim to beat expert tools like Open Targets, AlphaMissense, Reactome, VCell, or PhysiCell. Instead, it demonstrates a simplified linked framework where each layer passes interpretable parameters to the next.
