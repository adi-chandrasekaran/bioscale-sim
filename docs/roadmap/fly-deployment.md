# Fly.io Deployment Plan

This repo is prepared for a two-app Fly.io deployment:

- `bioscale-sim-backend` for the FastAPI API
- `bioscale-sim-frontend` for the Vite frontend

The split matches the current Docker setup and keeps deployment simple.

## What is already in the repo

- `backend/fly.toml`
- `frontend/fly.toml`
- `.github/workflows/fly-deploy.yml`
- `backend/Dockerfile`
- `frontend/Dockerfile`

## One-time Fly setup

1. Install Fly CLI if needed:

   ```bash
   brew install flyctl
   ```

2. Log in:

   ```bash
   fly auth login
   ```

3. Create the apps once:

   ```bash
   cd backend
   fly apps create bioscale-sim-backend

   cd frontend
   fly apps create bioscale-sim-frontend
   ```

4. Set backend CORS for the frontend domain:

   ```bash
   fly secrets set \
     BIOSCALE_CORS_ORIGINS="https://bioscale-sim-frontend.fly.dev,http://localhost:5173,http://127.0.0.1:5173" \
     -a bioscale-sim-backend
   ```

## Local deploy checks

Before enabling GitHub Actions, verify both apps deploy from your machine:

```bash
cd backend
fly deploy

cd frontend
fly deploy
```

The frontend build is configured to talk to the backend Fly app URL in `frontend/fly.toml`.
If you rename either app, update the Fly config and keep the two URLs aligned.

## GitHub Actions CI/CD

The workflow at `.github/workflows/fly-deploy.yml` does three things:

- runs backend tests on every push and pull request to `main`
- builds the frontend on every push and pull request to `main`
- deploys both apps on pushes to `main` after tests pass

### Required GitHub secret

- `FLY_API_TOKEN`

Generate it from your Fly account and add it in the GitHub repository settings.

## AI chatbot note

The AI chatbot is currently backed by local Ollama. That is great for local development, but it is not automatically deployed with Fly.

For Fly production, you have two choices:

- keep the chatbot disabled in production and rely on the fallback UI
- add a hosted model service later and point the backend to it

## Rollout order

Recommended release sequence:

1. deploy backend manually once
2. deploy frontend manually once
3. add the GitHub Actions secret
4. let the workflow take over continuous deployment
