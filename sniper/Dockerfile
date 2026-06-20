# prpo_ai sniper bot — Dockerfile for SnapDeploy / generic Docker
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy sniper code
COPY . .

# Health check (SnapDeploy needs this to keep container alive)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run bot
CMD ["python", "-u", "bot.py"]
