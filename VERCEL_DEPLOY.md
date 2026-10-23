# Vercel Deployment — Astrocartography

## Files added

- `astrocartography/vercel.json` — project config (builds + routes)
- `astrocartography/api/index.py` — Python serverless handler wrapping the FastAPI app
- `astrocartography/api/requirements.txt` — Python dependencies

## Terminal deployment

```powershell
# 1. Install Vercel CLI (one-time)
npm install -g vercel

# 2. Login to Vercel
vercel login

# 3. Deploy from the astrocartography project directory
cd C:\Users\Evand\Desktop\UNCHAINED3D\ASTRO\astrocartography
vercel

# 4. For production, use:
vercel --prod
```

## How it works

| Route | Target |
|-------|--------|
| `/api/*` | Python serverless handler (`api/index.py`) → FastAPI |
| `/assets/*`, `/cesium/*`, images, `labels.json` | Static files from `frontend/dist/` |
| Everything else | SPA fallback → `frontend/dist/index.html` |

The handler downloads the JPL `de440.bsp` ephemeris kernel to `/tmp` on cold start (before importing the backend), then adapts each Vercel HTTP request into an ASGI call against the FastAPI application.

## Important caveats

1. **`moira-astro` Linux compatibility** — The local wheel (`moira_astro-6.1.0-cp313-cp313-win_amd64.whl`) is Windows-only. Vercel runs Linux. If `moira-astro==6.1.0` has no Linux wheel on PyPI, the Python build will fail. You may need a Linux-compatible version of `moira-astro` or a pure-Python fallback.

2. **Kernel download latency** — `de440.bsp` (~30 MB) is downloaded on cold start. Subsequent warm requests reuse it. Add `MOIRA_KERNEL_PATH=/tmp/de440.bsp` in the Vercel project's Environment Variables if needed (already set in `vercel.json`).

3. **Frontend versions** — `frontend/package.json` lists `typescript: ^7.0.2` and `vite: ^8.2.1`, which don't exist yet. If `npm run build` fails on Vercel, pin to real versions (e.g. `typescript: ^5.x`, `vite: ^5.x` or `^6.x`).

4. **Vercel Hobby limits** — Serverless function timeout is 10 seconds; long calculations (travel timing, grid ranking) may hit this. Consider `/api/travel-timing` with a smaller `days` window.

## Managing in terminal

```powershell
# Redeploy after changes
vercel --prod

# Check deployment status
vercel ls

# Remove a deployment
vercel rm <deployment-url>

# Set environment variables (also in Vercel dashboard)
vercel env add MOIRA_KERNEL_PATH
```
