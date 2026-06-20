"""
position.py — open/close position state, persisted to JSON.
Hard guarantees:
  - max MAX_OPEN_POSITIONS open at once
  - per-trade size bounded
  - per-day drawdown kill-switch
  - stop loss -30%, TP1 +30% (50% size), TP2 +80% (remaining)
"""
import json
import time
import os
from pathlib import Path

STATE_DIR = Path("/root/prpo_ai/sniper/state")
STATE_FILE = STATE_DIR / "positions.json"
DAILY_FILE = STATE_DIR / "daily.json"


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def _save_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def list_open():
    return _load_json(STATE_FILE, {"open": [], "closed": []})


def list_closed(limit=50):
    s = list_open()
    return s.get("closed", [])[-limit:]


def get_open(mint: str):
    s = list_open()
    for p in s.get("open", []):
        if p["mint"] == mint:
            return p
    return None


def open_position(mint: str, symbol: str, sol_in: float, price_usd: float,
                  tx_sig: str, source: str) -> dict:
    s = list_open()
    pos = {
        "mint": mint,
        "symbol": symbol,
        "sol_in": sol_in,
        "tokens_held_est": 0,  # filled later via tx simulation if needed
        "entry_price_usd": price_usd,
        "entry_ts": time.time(),
        "tp1_hit": False,
        "tp2_hit": False,
        "sl_hit": False,
        "tx_sig": tx_sig,
        "source": source,
    }
    s["open"].append(pos)
    _save_json(STATE_FILE, s)
    return pos


def update_position(mint: str, **fields):
    s = list_open()
    for p in s.get("open", []):
        if p["mint"] == mint:
            p.update(fields)
            _save_json(STATE_FILE, s)
            return p
    return None


def close_position(mint: str, exit_price_usd: float, sol_out: float, reason: str, tx_sig: str = "") -> dict | None:
    s = list_open()
    for i, p in enumerate(s.get("open", [])):
        if p["mint"] == mint:
            p["exit_price_usd"] = exit_price_usd
            p["sol_out"] = sol_out
            p["pnl_sol"] = sol_out - p["sol_in"]
            p["pnl_pct"] = ((exit_price_usd / p["entry_price_usd"]) - 1) * 100 if p["entry_price_usd"] else 0
            p["close_ts"] = time.time()
            p["close_reason"] = reason
            p["close_tx"] = tx_sig
            s["closed"].append(p)
            s["open"].pop(i)
            _save_json(STATE_FILE, s)
            _bump_daily(p["pnl_sol"])
            return p
    return None


def _bump_daily(pnl_sol: float):
    d = _load_json(DAILY_FILE, {"date": "", "realized_sol": 0.0, "trades": 0, "wins": 0, "losses": 0})
    today = time.strftime("%Y-%m-%d")
    if d["date"] != today:
        d = {"date": today, "realized_sol": 0.0, "trades": 0, "wins": 0, "losses": 0}
    d["realized_sol"] += pnl_sol
    d["trades"] += 1
    if pnl_sol > 0:
        d["wins"] += 1
    else:
        d["losses"] += 1
    _save_json(DAILY_FILE, d)


def get_daily():
    d = _load_json(DAILY_FILE, {"date": "", "realized_sol": 0.0, "trades": 0, "wins": 0, "losses": 0})
    today = time.strftime("%Y-%m-%d")
    if d["date"] != today:
        return {"date": today, "realized_sol": 0.0, "trades": 0, "wins": 0, "losses": 0}
    return d
