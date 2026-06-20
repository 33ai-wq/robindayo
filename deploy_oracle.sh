#!/bin/bash
# ============================================================================
# prpo_ai — Oracle Cloud Always Free ARM Deployment Script
# Tested on: Oracle Linux 8/9 ARM (aarch64), Ubuntu 22.04 ARM
# Run as: bash deploy_oracle.sh
# ============================================================================
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $*"; }
warn() { echo -e "${YELLOW}[!]${NC} $*"; }
err()  { echo -e "${RED}[✗]${NC} $*"; }

# ---- Pre-flight checks ----
echo "============================================================================"
echo " prpo_ai — Oracle Cloud Deployment"
echo "============================================================================"
echo ""

if [ "$EUID" -ne 0 ]; then
  err "Jalankan sebagai root: sudo bash deploy_oracle.sh"
  exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
  . /etc/os-release
  log "OS detected: $NAME $VERSION (arch: $(uname -m))"
else
  err "Cannot detect OS. /etc/oracle-release not found."
  exit 1
fi

# ---- 1. System update + essentials ----
log "STEP 1: System update + essentials"
if [[ "$ID" == "ol" ]] || [[ "$ID" == "centos" ]] || [[ "$ID" == "rhel" ]]; then
  dnf update -y
  dnf install -y git curl wget tar python3 python3-pip python3-devel gcc make
elif [[ "$ID" == "ubuntu" ]] || [[ "$ID" == "debian" ]]; then
  apt update -y && apt upgrade -y
  apt install -y git curl wget tar python3 python3-pip python3-venv build-essential
fi
log "System packages installed"

# ---- 2. Node.js (for Meridian) ----
log "STEP 2: Node.js LTS install"
if ! command -v node &>/dev/null; then
  curl -fsSL https://rpm.nodesource.com/setup_20.x | bash - 2>/dev/null || \
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  if [[ "$ID" == "ol" ]] || [[ "$ID" == "centos" ]]; then
    dnf install -y nodejs
  else
    apt install -y nodejs
  fi
fi
NODE_VER=$(node --version)
log "Node.js installed: $NODE_VER"

# ---- 3. pm2 globally ----
log "STEP 3: pm2 (process manager) global install"
npm install -g pm2 2>&1 | tail -3
log "pm2 installed: $(pm2 --version)"

# ---- 4. Clone repo ----
log "STEP 4: Clone prpo_ai private repo"
mkdir -p /root
cd /root
if [ -d "prpo_ai" ]; then
  warn "prpo_ai already exists. Pulling latest..."
  cd prpo_ai && git pull origin main
else
  # Need GitHub PAT — prompt user
  echo ""
  echo "Masukkan GitHub Personal Access Token (dengan scope 'repo'):"
  read -s GITHUB_TOKEN
  echo ""
  if [ -z "$GITHUB_TOKEN" ]; then
    err "Token kosong. Ambil dari https://github.com/settings/tokens/new"
    exit 1
  fi
  git clone https://${GITHUB_TOKEN}@github.com/33ai-wq/prpo_ai.git
  cd prpo_ai
fi
log "Repo cloned at $(pwd)"

# ---- 5. Setup Python venv for sniper ----
log "STEP 5: Python venv + sniper dependencies"
python3 -m venv /root/.venv-sniper
source /root/.venv-sniper/bin/activate
pip install --quiet --upgrade pip
pip install --quiet 'solana>=0.34.0,<0.36' 'solders>=0.21.0,<0.23' \
                   base58 aiohttp websockets python-dotenv 'spl-token'
deactivate
log "Sniper Python venv ready at /root/.venv-sniper"

# ---- 6. Copy sniper code from local (if exists) OR create placeholder ----
log "STEP 6: Setup sniper bot directory"
mkdir -p /root/prpo_ai/sniper/{logs,state,reports}
# If local Termux sniper exists, copy from there
if [ -d "/tmp/prpo_sniper_sync" ]; then
  cp -r /tmp/prpo_sniper_sync/* /root/prpo_ai/sniper/
  log "Sniper code synced from local"
else
  warn "Sniper code not in sync. Will clone from local repo after first sync."
fi

# ---- 7. Setup .env (prompt user) ----
log "STEP 7: Configure .env"
mkdir -p /root/.hermes/profiles/prpo_ai
ENV_PATH="/root/.hermes/profiles/prpo_ai/.env"
if [ ! -f "$ENV_PATH" ]; then
  cat > "$ENV_PATH" << 'ENVEOF'
# === prpo_ai .env — DO NOT COMMIT ===
# Required for sniper bot
PRIVATE_KEY_SOL_TREASURY=
RPC_URL=https://mainnet.helius-rpc.com/?api-key=
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=1963809645

# Optional
HELIUS_API_KEY=
BIRDEYE_API_KEY=
WALLET_ADDRESS_SOL=7P7w3M9yQs5PCH2WbfmMxVWnkrobVsq1ARZBFfJ5W5zN
ENVEOF
  chmod 600 "$ENV_PATH"
  warn "Created $ENV_PATH. EDIT MANUALLY with your keys, then re-run this script."
  echo ""
  echo "Isi keys sekarang? (y/n)"
  read -r FILL_ENV
  if [ "$FILL_ENV" = "y" ]; then
    source /root/.venv-sniper/bin/activate
    python3 /root/prpo_ai/save_keys.py
    deactivate
  fi
else
  log ".env already exists at $ENV_PATH"
fi

# ---- 8. Setup meridian env (already exists in repo via meridian_copy/config-only) ----
log "STEP 8: Meridian env setup"
if [ ! -f "/root/.hermes/profiles/prpo_ai/meridian_copy/config-only/meridian.env" ]; then
  warn "Meridian env not found. Copy from local backup if exists."
fi

# ---- 9. pm2 ecosystem file ----
log "STEP 9: pm2 ecosystem config"
cat > /root/prpo_ai/ecosystem.config.cjs << 'PMEOF'
module.exports = {
  apps: [
    {
      name: 'sniper',
      script: '/root/.venv-sniper/bin/python',
      args: '-u /root/prpo_ai/sniper/bot.py',
      cwd: '/root/prpo_ai/sniper',
      instances: 1,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 20,
      min_uptime: '30s',
      out_file: '/root/prpo_ai/sniper/logs/bot.log',
      error_file: '/root/prpo_ai/sniper/logs/bot.err.log',
      merge_logs: true,
      env: {
        NODE_ENV: 'production',
      },
    },
    {
      name: 'meridian',
      script: 'index.js',
      cwd: '/root/.hermes/profiles/prpo_ai/meridian_copy',
      instances: 1,
      autorestart: true,
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      env: {
        NODE_ENV: 'production',
      },
    },
  ],
};
PMEOF
log "ecosystem.config.cjs created"

# ---- 10. pm2 startup + save ----
log "STEP 10: pm2 boot persistence"
pm2 startup systemd -u root --hp /root 2>&1 | tail -5
warn "If pm2 startup prints a 'sudo env PATH=...' command, RUN IT."

# ---- 11. firewall ----
log "STEP 11: UFW firewall (SSH only)"
if command -v ufw &>/dev/null; then
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow ssh
  echo "y" | ufw enable
  ufw status
elif command -v firewall-cmd &>/dev/null; then
  firewall-cmd --permanent --add-service=ssh
  firewall-cmd --reload
fi

# ---- 12. fail2ban ----
log "STEP 12: fail2ban install"
if [[ "$ID" == "ol" ]] || [[ "$ID" == "centos" ]]; then
  dnf install -y epel-release fail2ban 2>&1 | tail -2
else
  apt install -y fail2ban
fi
systemctl enable fail2ban
systemctl start fail2ban
log "fail2ban enabled"

# ---- 13. SSH hardening ----
log "STEP 13: SSH key-only auth"
SSHD_CONF="/etc/ssh/sshd_config"
cp "$SSHD_CONF" "${SSHD_CONF}.bak"
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' "$SSHD_CONF"
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' "$SSHD_CONF"
systemctl restart sshd
warn "SSH password auth DISABLED. Pastikan Anda punya SSH key."

# ---- 14. Telegram verify ----
log "STEP 14: Telegram verify"
source /root/.venv-sniper/bin/activate
python3 << 'PYEOF'
import asyncio, sys
sys.path.insert(0, '/root/prpo_ai/sniper')
import os
os.chdir('/root/prpo_ai/sniper')
try:
    # Clear caches
    for m in list(sys.modules.keys()):
        if 'config' in m or 'dotenv' in m: del sys.modules[m]
    import config, telegram
    print(f"  private_key: {'YES' if config.PRIVATE_KEY else 'NO'}")
    print(f"  rpc_url    : {'YES' if config.SOL_RPC_URL else 'NO'}")
    print(f"  tg_token   : {'YES' if config.TG_BOT_TOKEN else 'NO'}")
    print(f"  tg_chat    : {'YES' if config.TG_CHAT_ID else 'NO'}")
    if config.TG_BOT_TOKEN and config.TG_CHAT_ID:
        msg = (
            "🟢 prpo_ai — ORACLE CLOUD DEPLOYED\n"
            f"host: {os.uname().nodename}\n"
            f"arch: {os.uname().machine}\n"
            "sniper + meridian ready\n"
            "standby for first cycle..."
        )
        ok = asyncio.run(telegram.send(msg))
        print(f"  telegram: {'OK' if ok else 'FAILED'}")
    else:
        print("  telegram: skipped (keys not set)")
except Exception as e:
    print(f"  verify err: {e}")
deactivate
PYEOF

# ---- 15. Final ----
echo ""
echo "============================================================================"
echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
echo "============================================================================"
echo ""
echo "NEXT STEPS:"
echo "  1. Sync sniper code dari HP ke VPS (via rsync):"
echo "     rsync -avz /root/prpo_ai/sniper/ root@<vps-ip>:/root/prpo_ai/sniper/"
echo ""
echo "  2. Edit .env jika belum diisi:"
echo "     nano /root/.hermes/profiles/prpo_ai/.env"
echo ""
echo "  3. Start services:"
echo "     pm2 start /root/prpo_ai/ecosystem.config.cjs"
echo "     pm2 save"
echo "     pm2 logs --lines 30"
echo ""
echo "  4. Verify di Telegram (chat 1963809645):"
echo "     Should receive: '🟢 prpo_ai — ORACLE CLOUD DEPLOYED'"
echo ""
echo "  5. Backup VPS state ke GitHub:"
echo "     cd /root/prpo_ai && git add sniper/logs sniper/state && git commit -m 'VPS state sync'"
echo ""
log "DONE."
