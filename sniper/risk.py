"""
risk.py — pre-trade guardrails. ALL gates must pass before a buy.
"""
import time
import position
import config


def cooldown_active() -> bool:
    """If 3+ losses in last 60min, lock new entries for cooldown minutes."""
    closed = position.list_closed(limit=20)
    recent_losses = [p for p in closed if p.get("pnl_sol", 0) < 0 and (time.time() - p.get("close_ts", 0)) < 3600]
    if len(recent_losses) >= config.LOSS_STREAK_PAUSE:
        latest = max(p["close_ts"] for p in recent_losses)
        elapsed = time.time() - latest
        if elapsed < config.COOLDOWN_MINUTES * 60:
            return True
    return False


def daily_kill_switch(starting_capital_sol: float) -> tuple[bool, str]:
    d = position.get_daily()
    loss_pct = abs(d["realized_sol"]) / starting_capital_sol * 100 if d["realized_sol"] < 0 and starting_capital_sol else 0
    if loss_pct >= config.MAX_DAILY_DRAWDOWN_PCT:
        return True, f"Daily drawdown {loss_pct:.1f}% >= {config.MAX_DAILY_DRAWDOWN_PCT}% (realized {d['realized_sol']:+.4f} SOL)"
    if d["trades"] >= config.MAX_DAILY_TRADES:
        return True, f"Daily trade count {d['trades']} >= {config.MAX_DAILY_TRADES}"
    return False, "OK"


def can_open() -> tuple[bool, str]:
    open_pos = position.list_open().get("open", [])
    if len(open_pos) >= config.MAX_OPEN_POSITIONS:
        return False, f"Max open positions {len(open_pos)}/{config.MAX_OPEN_POSITIONS}"
    cd = cooldown_active()
    if cd:
        return False, "Cooldown active (3 losses in last 1h)"
    return True, "OK"


def position_size_sol(available_sol: float) -> float:
    """Sizing: MIN(MAX_PER_TRADE_SOL, available * RISK_PCT_OF_FREE)"""
    target = available_sol * config.RISK_PCT_OF_FREE
    return min(target, config.MAX_PER_TRADE_SOL, config.HARD_TRADE_CAP_SOL)
