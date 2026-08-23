# Demo Deployment — Vercel UI + Live Local Backend

Presents the full project at a public `*.vercel.app` URL with zero hosting cost.
The Vercel-hosted React frontend proxies `/api/*` through an encrypted
Tailscale Funnel tunnel to the complete Docker stack running on this PC.

```
Browser ──> https://<project>.vercel.app        (static UI on Vercel CDN)
                 │  /api/* rewritten by vercel.json
                 ▼
            Tailscale Funnel (TLS)  ──>  this PC :8000
                 │                        docker compose:
                 ▼                        api · worker · mysql · qdrant
                                          neo4j · minio · ollama · nginx
```

## One-time setup

### 1. Tailscale (tunnel)
1. Install Tailscale: `winget install tailscale.tailscale`, then log in with a
   free account (Google/GitHub/Microsoft).
2. In the Tailscale admin console (https://login.tailscale.com):
   - **DNS** page → enable **MagicDNS**
   - **DNS** page → enable **HTTPS Certificates**
3. Get your machine's permanent hostname:
   ```powershell
   tailscale status
   ```
   Note the DNS name, e.g. `yourpc.tail1234.ts.net`.
4. Open the funnel (public HTTPS → localhost:8000), persisted in the background:
   ```powershell
   tailscale funnel --bg 8000
   ```
5. Verify from a phone on mobile data: `https://yourpc.tail1234.ts.net/health`
   should return `{"status":"ok"}`.

### 2. Bake the hostname into the frontend
Edit `frontend/vercel.json` and replace every
`REPLACE-WITH-YOUR-PC.tailnet-name.ts.net` with the hostname from step 3.
Commit and push — Vercel redeploys automatically.

### 3. Vercel (frontend hosting)
1. Go to https://vercel.com → sign in with GitHub.
2. **Add New Project** → import `Vishwakanth1105/Crag-Project`.
3. Configure:
   - **Root Directory**: `frontend`
   - Framework preset: **Vite** (auto-detected; build `npm run build`,
     output `dist`)
4. Deploy. Your URL: `https://<project-name>.vercel.app`
5. Verify: register a user, log in, send a chat message.

## Before every presentation (~5 minutes)

```powershell
# 1. Docker Desktop running, then:
cd "C:\Crag Project\agentic-graph-rag"
docker compose up -d
docker compose ps                # all services healthy

# 2. Tunnel alive (persists across reboots once --bg is set):
tailscale funnel status          # should list https→8000

# 3. End-to-end sanity check from the audience's perspective:
#    open https://<project>.vercel.app, log in, ask one chat question
```

- Disable PC sleep during the demo: Settings → System → Power.
- Keep `tailscale.exe` running in the tray.

## Speed tip for demo day

Local Ollama (`LLM_PROVIDER=local`) is free but takes ~5–20 s per chat reply,
plus upload-bandwidth on top. For snappier live replies, switch `.env` to
Gemini for the day (`LLM_PROVIDER=gemini`, key already present), run
`docker compose up -d api worker`, then switch back afterwards.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Vercel shows 502 / API errors | Tunnel down → rerun `tailscale funnel --bg 8000`; check `docker compose ps` |
| Login works locally but not via Vercel | Hostname in `frontend/vercel.json` stale → update + push |
| First chat reply very slow | Expected cold-start of Ollama model; warm up with one query before going live |
| Changed WiFi/network | Tailscale reconnects automatically; nothing to redo |
