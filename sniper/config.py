"""
prpo_ai Meme Sniper - Config Loader
Loads credentials from /root/.hermes/profiles/prpo_ai/.env
Optional everywhere; required keys only raise on use.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

ENV_PATH = Path("/root/.hermes/profiles/prpo_ai/.env")
load_dotenv(ENV_PATH)


def _opt(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def require(key: str) -> str:
    v = _opt(key)
    if not v:
        raise RuntimeError(
            f"MISSING ENV: {key}. Add to {ENV_PATH}. "
            f"Required for trading: PRIVATE_KEY_SOL_TREASURY, SOL_RPC_URL, "
            f"TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID"
        )
    return v


# Required — accepts both the canonical name and B0x70's existing names as fallback
PRIVATE_KEY = _opt("PRIVATE_KEY_SOL_TREASURY") or _opt("PRIVATE_KEY_TREASURY_ADDRESS_03") or _opt("PUMFUN_PRIVATE_KEY")
SOL_RPC_URL = _opt("SOL_RPC_URL") or _opt("RPC_URL")
TG_BOT_TOKEN = _opt("TELEGRAM_BOT_TOKEN")
TG_CHAT_ID = _opt("TELEGRAM_CHAT_ID") or _opt("TELEGRAM_CHAT_ID_PRPOAI") or _opt("TELEGRAM_HOME_CHANNEL")

# Optional
BIRDEYE_API_KEY = _opt("BIRDEYE_API_KEY")
WALLET_ADDRESS = _opt("WALLET_ADDRESS_SOL")
HELIUS_API_KEY = _opt("HELIUS_API_KEY")

# Strategy params
MIN_LIQ_USD = float(_opt("SNIPER_MIN_LIQ_USD", "15000"))
MIN_VOL24H_USD = float(_opt("SNIPER_MIN_VOL24H_USD", "25000"))
MIN_HOLDERS = int(_opt("SNIPER_MIN_HOLDERS", "150"))
MAX_CANDIDATES = int(_opt("SNIPER_MAX_CANDIDATES", "8"))

# Position sizing
RISK_PCT_OF_FREE = float(_opt("SNIPER_RISK_PCT", "0.20"))
MAX_PER_TRADE_SOL = float(_opt("SNIPER_MAX_PER_TRADE_SOL", "0.015"))
HARD_TRADE_CAP_SOL = float(_opt("SNIPER_HARD_TRADE_CAP_SOL", "0.020"))

# Risk guardrails
MAX_OPEN_POSITIONS = int(_opt("SNIPER_MAX_OPEN", "3"))
MAX_DAILY_TRADES = int(_opt("SNIPER_MAX_DAILY_TRADES", "10"))
MAX_DAILY_DRAWDOWN_PCT = float(_opt("SNIPER_MAX_DAILY_DD_PCT", "30"))
LOSS_STREAK_PAUSE = int(_opt("SNIPER_LOSS_STREAK", "3"))
COOLDOWN_MINUTES = int(_opt("SNIPER_COOLDOWN_MIN", "60"))

# Trade mechanics
SLIPPAGE_BPS = int(_opt("SNIPER_SLIPPAGE_BPS", "2000"))
PRIORITY_FEE_LAMPORTS = int(_opt("SNIPER_PRIO_FEE_LAMP", "10000"))
USE_JITO = _opt("SNIPER_USE_JITO", "false").lower() == "true"

# TP / SL
TP1_PCT = float(_opt("SNIPER_TP1_PCT", "30"))
TP2_PCT = float(_opt("SNIPER_TP2_PCT", "80"))
TP1_SIZE = float(_opt("SNIPER_TP1_SIZE", "0.50"))
SL_PCT = float(_opt("SNIPER_SL_PCT", "30"))
TRAILING_PCT = float(_opt("SNIPER_TRAIL_PCT", "20"))
MAX_HOLD_HOURS = float(_opt("SNIPER_MAX_HOLD_HOURS", "24"))

# Loop timing
SCAN_INTERVAL_SEC = int(_opt("SNIPER_SCAN_INTERVAL", "120"))
MONITOR_INTERVAL_SEC = int(_opt("SNIPER_MONITOR_INTERVAL", "30"))


def sanity() -> dict:
    """Returns a status dict for startup checks."""
    return {
        "have_private_key": bool(PRIVATE_KEY),
        "have_rpc": bool(SOL_RPC_URL),
        "have_tg_token": bool(TG_BOT_TOKEN),
        "have_tg_chat": bool(TG_CHAT_ID),
        "have_birdeye": bool(BIRDEYE_API_KEY),
        "wallet_address": WALLET_ADDRESS,
    }
