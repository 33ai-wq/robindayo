# prpo_ai sniper bot — Dockerfile for SnapDeploy (deploy/ context)
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl && rm -rf /var/lib/apt/lists/*

COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sniper code from deploy/
COPY deploy/ ./

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

CMD ["python", "-u", "bot.py"]
