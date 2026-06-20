#!/bin/bash
# prpo_ai sniper runner — use as cron entrypoint
set -e
source /root/.venv-sniper/bin/activate
cd /root/prpo_ai/sniper
exec python -u bot.py >> logs/bot.log 2>&1
