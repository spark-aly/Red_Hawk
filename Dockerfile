# Red Hawk — single-image deploy.
# Runs the deliberately-vulnerable target bot (internal :5001) and the Streamlit
# dashboard (the platform port) together in one container. Works on Cloud Run,
# any VM with Docker, or locally. Vertex/ADC + Phoenix credentials are supplied at
# runtime via environment variables / a mounted service account — never baked in.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first so this layer caches across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code (the .dockerignore keeps out .venv, .env, caches, etc.).
COPY . .

# Normalize line endings (in case of a Windows checkout) and make the entrypoint executable.
RUN sed -i 's/\r$//' /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# In-container wiring: the dashboard reaches the target bot over localhost.
ENV TARGET_BOT_HOST=0.0.0.0 \
    TARGET_BOT_PORT=5001 \
    TARGET_URL=http://127.0.0.1:5001/attack \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true

# 8501 = dashboard (Cloud Run overrides via $PORT); 5001 = target bot (optional).
EXPOSE 8501 5001

ENTRYPOINT ["/app/docker-entrypoint.sh"]
