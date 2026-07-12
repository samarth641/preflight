# Deploy frontend to Vercel

**Production URL:** [https://preflight-eta.vercel.app](https://preflight-eta.vercel.app)

The **Next.js UI** deploys to Vercel. The **FastAPI backend** does not — host it on DigitalOcean/Docker (or similar) and set `NEXT_PUBLIC_API_URL`.

## One-time setup

1. In [Vercel](https://vercel.com): Import `samarth641/preflight`
2. Set **Root Directory** to `frontend`
3. Environment variables (Production + Preview):

| Name | Value |
|------|--------|
| `NEXT_PUBLIC_DEMO_MODE` | `true` |
| `NEXT_PUBLIC_USE_MOCK` | `true` (until backend URL is ready) |
| `NEXT_PUBLIC_API_URL` | `https://YOUR-BACKEND/api/v1` (when live) |

Optional Firebase: `NEXT_PUBLIC_FIREBASE_*` (leave empty with demo mode).

4. Deploy.

## CLI

```bash
cd frontend
npx vercel --prod
```

## After backend is up (e.g. DigitalOcean droplet)

1. Set `NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api/v1`
2. Set `NEXT_PUBLIC_USE_MOCK=false`
3. Redeploy (public env vars are baked at build time)
4. Ensure backend CORS allows your Vercel domain (already `allow_origins=["*"]`)
