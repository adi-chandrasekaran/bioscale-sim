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

## Research angle

Possible paper title:

**A Modular Multi-Scale Framework for Simulating Disease-Associated Genetic Perturbations from Protein Function to Ecosystem-Level Dynamics**

The MVP does not claim to beat expert tools like Open Targets, AlphaMissense, Reactome, VCell, or PhysiCell. Instead, it demonstrates a simplified linked framework where each layer passes interpretable parameters to the next.
