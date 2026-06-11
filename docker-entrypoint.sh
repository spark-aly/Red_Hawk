#!/usr/bin/env bash
# Launch the target bot in the background, then run the Streamlit dashboard in the
# foreground on the platform port. Cloud Run injects $PORT; everything else defaults
# to the values set in the Dockerfile.
set -uo pipefail

PORT="${PORT:-${STREAMLIT_SERVER_PORT:-8501}}"
BOT_PORT="${TARGET_BOT_PORT:-5001}"

echo "[entrypoint] starting target bot on :${BOT_PORT} ..."
python target_bot.py &
BOT_PID=$!

# Best-effort readiness wait (non-fatal — the dashboard renders mock data until a
# live run is triggered, and the bot is only needed when 'Start Assessment' is clicked).
for _ in $(seq 1 20); do
  if python - "$BOT_PORT" <<'PY' 2>/dev/null
import sys, urllib.request
urllib.request.urlopen(f"http://127.0.0.1:{sys.argv[1]}/health", timeout=2)
PY
  then
    echo "[entrypoint] target bot is healthy"
    break
  fi
  if ! kill -0 "$BOT_PID" 2>/dev/null; then
    echo "[entrypoint] WARNING: target bot exited early (check Vertex/ADC env)."
    break
  fi
  sleep 1
done

echo "[entrypoint] starting dashboard on :${PORT} ..."
exec python -m streamlit run dashboard.py \
  --server.port "${PORT}" \
  --server.address 0.0.0.0 \
  --server.headless true
