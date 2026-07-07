# PreFlight — AI Training Intelligence Platform (Frontend)

Next.js dashboard for PreFlight. Predicts training cost, runtime, VRAM, convergence, and OOM risk before you allocate a GPU. Monitors live training. Recommends hardware.

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Pages

| Route | What it does |
|-------|-------------|
| `/` | Dashboard — overview stats, recent activity, quick actions |
| `/analyze` | Pre-Training Analysis — predictions for cost, runtime, VRAM, OOM, convergence, accuracy |
| `/dataset` | Dataset Intelligence — quality score, metrics, recommendations |
| `/gpu` | GPU Recommender — ranked candidates, cloud offerings, cost estimates |
| `/training` | Live Training Monitor — loss/accuracy/GPU charts, anomaly detection, health score |
| `/history` | Experiment History — past runs, predictions vs actuals |
| `/settings` | Settings — API config, preferences |

## Tech Stack

- Next.js 15 (App Router) + TypeScript
- Tailwind CSS 4
- Recharts (charts)
- Lucide React (icons)

## Project Structure

```
frontend/
├── app/                 # Next.js pages (App Router)
│   ├── layout.tsx       # Root layout — sidebar + main area
│   ├── page.tsx         # Dashboard
│   ├── analyze/         # Pre-training analysis page
│   ├── dataset/         # Dataset intelligence page
│   ├── gpu/             # GPU recommender page
│   ├── training/        # Live training monitor page
│   ├── history/         # Experiment history page
│   └── settings/        # Settings page
├── components/
│   ├── layout/          # Sidebar, TopBar
│   └── ui/              # Card, Button, Badge, Select, etc. — shared primitives
├── lib/
│   ├── api.ts           # API client — currently returns mock data
│   ├── mock-data.ts     # Mock data — remove when backend is connected
│   ├── types.ts         # TypeScript types — mirror backend Pydantic models
│   └── utils.ts         # Formatting helpers (USD, hours, percent, etc.)
├── INTEGRATION.md       # Guide for connecting the real backend
└── package.json
```

## Current State: Mock Mode

All API calls in `lib/api.ts` return mock data. No backend required to run the UI.

When the backend is ready, see [INTEGRATION.md](./INTEGRATION.md) for how to swap mock calls for real ones. It is a single-file change — only `lib/api.ts` changes. Components and types stay the same.

## Important Files

- **`lib/types.ts`** — TypeScript interfaces that mirror the backend Pydantic models. If you change a backend model, update this file to match.
- **`lib/api.ts`** — All API function signatures. This is the contract between frontend and backend. Swap mock implementations for `fetch()` calls when ready.
- **`lib/mock-data.ts`** — Mock data constants. Shows the exact shapes the frontend expects. Useful as a reference for what the backend should return.
