# Hackathon deploy (Docker)

Run the full Preflight stack (API + dashboard) with Docker Compose. No Python or Node install required.

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/Mac) or Docker Engine + Compose v2 (Linux)

## One command

```bash
git clone https://github.com/samarth641/preflight.git
cd preflight
docker compose up --build
```

Then open:

| Service | URL |
|---------|-----|
| **Dashboard** | http://localhost:3000 |
| **API docs** | http://localhost:8000/docs |
| **Health** | http://localhost:8000/health |

Stop with `Ctrl+C`, or run detached:

```bash
docker compose up --build -d
docker compose down
```

## Demo mode (default)

Compose sets `NEXT_PUBLIC_DEMO_MODE=true`, so judges can use the UI **without Google / Firebase login**. The frontend calls the live backend at `http://localhost:8000/api/v1`.

## Optional env

Copy [`.env.example`](../.env.example) to `.env` if you need to change ports/URLs or enable Firebase:

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|----------|---------|--------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Must be reachable from the **browser** (host ports), not the Docker service name |
| `NEXT_PUBLIC_DEMO_MODE` | `true` | Set `false` only if Firebase is configured and you want a login gate |
| `NEXT_PUBLIC_FIREBASE_*` | empty | Optional Google sign-in |

Rebuild the frontend after changing `NEXT_PUBLIC_*` values (they are baked in at build time):

```bash
docker compose up --build
```

## Services

| Service | Image build | Port |
|---------|-------------|------|
| `backend` | [`backend/Dockerfile`](../backend/Dockerfile) (repo-root context + `knowledge/`) | 8000 |
| `frontend` | [`frontend/Dockerfile`](../frontend/Dockerfile) (Next.js standalone) | 3000 |

MongoDB is **not** required for this demo.

## Troubleshooting

**Port already in use** — change host ports in `docker-compose.yml`, e.g. `"3001:3000"`.

**Frontend can't reach API** — confirm backend health at http://localhost:8000/health and that `NEXT_PUBLIC_API_URL` uses `localhost`, not `backend`.

**Blank / login loop** — ensure demo mode is on (`NEXT_PUBLIC_DEMO_MODE=true`) and rebuild frontend.
