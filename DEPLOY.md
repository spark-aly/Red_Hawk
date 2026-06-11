# Deploying Red Hawk

Red Hawk is two processes that run together: a deliberately-vulnerable **target bot**
(Flask, internal port `5001`) and the **Streamlit dashboard** (port `8501`, or the
platform's `$PORT`). The dashboard drives the live pipeline
(`generate_attack → fire_at_target → judge`) against the target bot.

A single `pip install -r requirements.txt` now installs the **entire** app, and the
included `Dockerfile` runs both processes in one container.

## Required configuration (all environments)

Supply these via environment variables (or a `.env` for local runs — never commit it):

| Variable | Purpose |
|---|---|
| `GOOGLE_GENAI_USE_VERTEXAI=1` | Use Vertex AI (recommended for GCP credits) |
| `GOOGLE_CLOUD_PROJECT` | Your GCP project id |
| `GOOGLE_CLOUD_LOCATION` | e.g. `us-central1` |
| `GOOGLE_API_KEY` | *Alternative* to Vertex — set this instead of the three above |
| `PHOENIX_API_KEY` | Phoenix Cloud key (`px_live_...`), optional but enables tracing |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix hostname incl. `/s/<space>` |
| `GEMINI_MODEL` / `JUDGE_MODEL` | Optional model overrides (default `gemini-2.5-flash`) |

On the Vertex path you also need **Application Default Credentials** (ADC): either run
on a GCP service account with the *Vertex AI User* role, or mount local gcloud creds
(see below). See `gemini-hackathon/.env.example` for the full annotated list.

## Option A — Local Docker (one box)

```bash
docker build -t red-hawk .

docker run --rm -p 8501:8501 \
  -e GOOGLE_GENAI_USE_VERTEXAI=1 \
  -e GOOGLE_CLOUD_PROJECT=<your-project> \
  -e GOOGLE_CLOUD_LOCATION=us-central1 \
  -e PHOENIX_API_KEY=<px_live_...> \
  -e PHOENIX_COLLECTOR_ENDPOINT=<https://app.phoenix.arize.com/s/your-space> \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  red-hawk
# open http://localhost:8501
```

(The `-v ...gcloud` mount supplies ADC for Vertex. With `GOOGLE_API_KEY` instead, drop
the mount and the Vertex vars.)

## Option B — Google Cloud Run

```bash
gcloud run deploy red-hawk \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account <vertex-enabled-sa>@<project>.iam.gserviceaccount.com \
  --set-env-vars GOOGLE_GENAI_USE_VERTEXAI=1,GOOGLE_CLOUD_PROJECT=<project>,GOOGLE_CLOUD_LOCATION=us-central1,PHOENIX_API_KEY=<key>,PHOENIX_COLLECTOR_ENDPOINT=<endpoint>
```

Cloud Run injects `$PORT`; the entrypoint binds Streamlit to it and keeps the target
bot internal on `5001`. The service account's IAM provides ADC automatically — no key
files needed.

## Option C — Plain VM (no Docker)

```bash
pip install -r requirements.txt
gcloud auth application-default login          # ADC for Vertex
export GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT=<project> GOOGLE_CLOUD_LOCATION=us-central1
TARGET_BOT_HOST=0.0.0.0 python target_bot.py &  # background
python -m streamlit run dashboard.py --server.address 0.0.0.0
```

## Local development (uv, unchanged)

The agent's uv environment remains the source of truth for ADK work:

```bash
cd gemini-hackathon && uv sync
cd .. && gemini-hackathon/.venv/Scripts/python.exe -m streamlit run dashboard.py
```

## Note on Streamlit Community Cloud

Streamlit Cloud runs a **single** process, so it can host the dashboard but **cannot**
run the target bot alongside it. Point the dashboard at an externally-hosted target by
setting `TARGET_URL` to that bot's `/attack` endpoint (and deploy the bot via Option A/B).
For a self-contained demo, prefer Docker/Cloud Run.

## Red-teaming a real chatbot (the adapter)

Red Hawk's `fire_at_target` sends `POST {"message": "<text>"}` and reads the
`response` field back. Real chatbots usually use a different JSON shape, so
`adapter.py` sits in between: it speaks Red Hawk's contract on `/attack` and
forwards each message to your real bot, translating both ways.

**1. Point it at your bot.** Set the upstream URL:

    # Windows PowerShell
    $env:UPSTREAM_URL = "https://your-bot.example.com/chat"
    # macOS/Linux
    export UPSTREAM_URL="https://your-bot.example.com/chat"

**2. Match your bot's JSON.** Open `adapter.py` and edit only the two
`# adjust shape` lines:
  - **(1/2)** the request body sent upstream — e.g. change `{"message": message}`
    to `{"prompt": message}` or `{"input": {"text": message}}`.
  - **(2/2)** where the reply text lives — e.g. change
    `body.get("response", ...)` to `body["choices"][0]["message"]["content"]`.

**3. Run the adapter.**

    pip install -r requirements.txt
    python adapter.py        # serves on 0.0.0.0:5002 (override with $PORT)

Sanity-check it: `GET /health` echoes the configured upstream.

**4. Point Red Hawk at the adapter.** In the dashboard's **Target chatbot URL**
box, enter the adapter's address ending in `/attack`, e.g.
`http://<adapter-host>:5002/attack`, then click **Start Assessment**.

> The adapter must be reachable **from wherever Red Hawk runs**. If Red Hawk is
> on Cloud Run, the adapter needs a public URL (deploy it, or expose a local one
> with a tunnel like ngrok) — `localhost` on your laptop is not reachable from
> the cloud. Only test bots you own or are authorized to assess.
