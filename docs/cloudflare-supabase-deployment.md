# Cloudflare Workers + Supabase MVP deployment

## Runtime layout

- Cloudflare Workers: Next.js frontend and public HTTP API
- Supabase: PostgreSQL, shared API cache, and collected dashboard data
- Scheduled collectors: repository workflows connect to the Supabase transaction pooler
- KIS domestic quotes: refresh-based REST snapshots; the long-running WebSocket worker is disabled

Domestic detail quotes use a shared TTL according to the Korean market session:

- NXT pre-market (08:00-08:50): 30 seconds
- Opening transition (08:50-09:00): 60 seconds
- KRX/NXT main session (09:00-15:30): 10 seconds for detail, 30 seconds for home
- Closing transition (15:30-15:40): 30 seconds
- NXT after-market (15:40-20:00): 30 seconds for detail, 60 seconds for home
- Closed market and weekends: 12 hours

The KIS market code follows the actual NXT continuous sessions. It uses `NX` during
08:00-08:50, 09:00:30-15:20, and 15:40-20:00 on weekdays, and `J` otherwise.
If a symbol is not available from NXT, the API falls back to KRX and returns the actual
source in `market_source`; the UI must display that value rather than inferring a source.

Charts are cached for five minutes while a domestic market is open and 12 hours otherwise.
Valuation metadata is cached for 24 hours.

## Supabase setup

1. Create a project in the closest available region.
2. Open **Connect** and copy the transaction pooler URI on port `6543`.
3. Change the scheme to `postgresql+psycopg://` and retain `sslmode=require`.
4. Set `DATABASE_URL` locally without committing it.
5. Apply migrations from `backend`:

   ```bash
   alembic upgrade head
   ```

6. Confirm that revision `20260826_0016` is at Alembic head.

Use the pooler URI for serverless functions and scheduled jobs. Never expose the database password,
KIS keys, DART key, Solar key, or Supabase service-role key through a `NEXT_PUBLIC_` variable.

## Required production secrets

- Cloudflare Worker: `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `DART_API_KEY`
- GitHub Actions: `SUPABASE_DATABASE_URL`, `KIS_APP_KEY`, `KIS_APP_SECRET`, `DART_API_KEY`,
  `BOK_ECOS_API_KEY`, `SOLAR_API_KEY`

Set `KIS_IS_MOCK=false`, `KIS_ON_DEMAND_REFRESH_ENABLED=true`, and
`KIS_REALTIME_ENABLED=false` in production.

`SUPABASE_SECRET_KEY` must be a dedicated `sb_secret_...` server key. It is read only by the
Worker runtime and must never use a `NEXT_PUBLIC_` prefix. The database migration grants
`service_role` read access to dashboard tables and narrowly scoped write access to `api_cache`,
`kis_tokens`, and `disclosures`; it does not grant Data API access to `anon` or `authenticated`.

The disclosure page checks a shared Supabase cache on every request. If the last OpenDART check is
more than two minutes old, one request refreshes the shared cache and upserts only unseen receipt
numbers. Refresh failures keep serving the last stored disclosures and retry after two minutes.
The same refresh removes disclosure rows older than the current and previous KST calendar dates.

## Cloudflare frontend migration prerequisite

The current frontend is Next.js 16. Install Node.js 22 LTS, then run from `frontend`:

```bash
npx vinext init --platform=cloudflare
npm run build:vinext
```

Commit the generated `vite.config.ts`, `wrangler.jsonc`, package manifest, and lock file only after the
compatibility check and build succeed. Configure `stock.hwijade.com` as the Worker custom domain after
the preview deployment is verified.

Because local Wrangler authentication can be blocked by a corporate TLS proxy, production deployment
uses Cloudflare Workers Builds connected to GitHub:

- root directory: `frontend`
- build command: `npm run build:vinext`
- deploy command: `npm run deploy:vinext`
- Worker name: `stock-hanaro-frontend`

Add the five Worker secrets in **Workers & Pages > stock-hanaro-frontend > Settings > Variables and Secrets**.
Add the collector secrets in **GitHub > Settings > Secrets and variables > Actions**. The
`collect-supabase-production.yml` workflow runs morning, closing, and weekly stock-master batches directly
against the Supabase transaction pooler, so no permanently running FastAPI server is required.

## Data retention for the Supabase Free plan

- Upsert the latest quote instead of storing every tick.
- Keep daily/weekly/monthly candles; do not retain realtime ticks.
- Delete pipeline logs older than 30 days.
- Store research metadata and source URLs, not PDF files.
- Monitor database size and export a periodic logical backup because the Free plan has no automatic backups.
