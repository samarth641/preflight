# PreFlight — AI Training Intelligence Platform (Frontend)

Next.js dashboard for PreFlight. Predicts training cost, runtime, and VRAM. Monitors live training. Recommends hardware.

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## Pages

| Route | What it does |
|-------|-------------|
| `/` | Dashboard — bento grid stats, system status, quick actions, collapsible recent activity |
| `/analyze` | Redirects to `/analyze/ml-duration` |
| `/analyze/ml-duration` | ML Duration Prediction — estimated hours, cost, human-readable duration |
| `/analyze/pre-training` | Pre-Training Estimates — AI explanation, recommendations, OOM risk |
| `/dataset` | Dataset Intelligence — quality score, metrics, warnings, recommendations |
| `/gpu` | GPU Recommender — ranked candidates, cloud offerings, benchmark throughput |
| `/training` | Live Training Monitor — loss/accuracy curves, convergence, health score, saved jobs |
| `/history` | Experiment History — past runs with convergence and accuracy results |
| `/settings` | Settings — API config, preferences |

## Tech Stack

- Next.js 15 (App Router) + TypeScript
- Tailwind CSS 4
- Recharts (charts)
- Lucide React (icons)

## Project Structure

```
frontend/
├── app/                          # Next.js pages (App Router)
│   ├── layout.tsx                # Root layout — sidebar + PageResultsProvider
│   ├── page.tsx                  # Dashboard
│   ├── globals.css               # Design tokens + dashboard layout CSS
│   ├── analyze/
│   │   ├── page.tsx              # Redirects to /analyze/ml-duration
│   │   ├── ml-duration/page.tsx  # ML Duration Prediction
│   │   └── pre-training/page.tsx # Pre-Training Estimates
│   ├── dataset/                  # Dataset intelligence page
│   ├── gpu/                      # GPU recommender page
│   ├── training/                 # Live training monitor page
│   ├── history/                  # Experiment history page
│   └── settings/                 # Settings page
├── components/
│   ├── layout/                   # Sidebar (with analyze dropdown), TopBar
│   ├── providers/                # PageResultsContext — persists results across navigation
│   └── ui/                       # Card, Button, Badge, Select, etc.
├── lib/
│   ├── api.ts                    # API client — returns mock data (swap with fetch when ready)
│   ├── mock-data.ts              # Mock data matching backend Pydantic models
│   ├── types.ts                  # TypeScript types — mirror backend schemas
│   └── utils.ts                  # Formatting helpers (USD, hours, percent, etc.)
├── INTEGRATION.md                # Guide for connecting the real backend
└── package.json
```

## What's New (agentq/frontend-iteration)

- **Analyze page split**: Two focused pages (ML Duration + Pre-Training) with sidebar dropdown
- **Result persistence**: Analysis results survive page navigation via React Context
- **Dashboard redesign**: Bento 2×2 grid, viewport-relative sizing, collapsible recent activity
- **Training demo job**: Seeds a demo job on first visit so visitors can quickly view training data
- **History crash fix**: Fixed `listExperiments()` return type mismatch
- **GPU page fix**: Added missing `GPURecommendationRequest` fields for type safety
- **Logo**: Paper plane SVG (angular, upward trajectory — fits "pre-flight" concept)
- **Hydration fix**: Sidebar SSR/client mismatch resolved
- **Responsive**: `clamp()`-based typography/spacing, short viewport scroll fallback
- **Code cleanup**: Unused imports removed, no type errors (`tsc --noEmit` clean)

## Current State: Mock Mode

All API calls in `lib/api.ts` return mock data. No backend required to run the UI.

The mock data in `lib/mock-data.ts` matches the backend Pydantic models. When the backend is ready, see [INTEGRATION.md](./INTEGRATION.md) for how to swap mock calls for real ones. It is a single-file change — only `lib/api.ts` changes. Components and types stay the same.

## Important Files

- **`lib/types.ts`** — TypeScript interfaces that mirror the backend Pydantic models. If you change a backend model, update this file to match.
- **`lib/api.ts`** — All API function signatures. This is the contract between frontend and backend. Swap mock implementations for `fetch()` calls when ready.
- **`lib/mock-data.ts`** — Mock data constants. Shows the exact shapes the frontend expects.
- **`app/globals.css`** — Design tokens (colors, typography scale, spacing) and dashboard layout. All sizing uses `clamp()` for viewport responsiveness.
