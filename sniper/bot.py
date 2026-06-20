"""
bot.py — main orchestrator. Run with: python bot.py
Loops:
  - SCAN: collect candidates, score, decide entries
  - MONITOR: for each open position, check TP/SL, trigger exit if hit
  - REPORT: every hour, send Telegram summary
  - SAFETY: kill switch on drawdown, persist state on shutdown
"""
import asyncio
import signal
import sys
import time
from pathlib import Path

import config
import executor
import gmgn_signal
import position as pos_mod
import price_feed
import risk
import telegram as tg


STARTING_CAPITAL_SOL = 0.069
RUNNING = True


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


async def report_startup():
    print("[boot] report_startup enter", flush=True)
    bal = executor.get_balance_sol()
    print(f"[boot] balance={bal}", flush=True)
    daily = pos_mod.get_daily()
    msg = (
        f"<b>prpo_ai SNIPER — START</b>\n"
        f"wallet: <code>{(await get_my_address())}</code>\n"
        f"balance: <b>{bal:.4f} SOL</b>\n"
        f"strategy: smart-money copy + filtered trending\n"
        f"max open: {config.MAX_OPEN_POSITIONS} | max/trade: {config.MAX_PER_TRADE_SOL} SOL\n"
        f"TP1 +{config.TP1_PCT}% exit {int(config.TP1_SIZE*100)}% | TP2 +{config.TP2_PCT}% | SL -{config.SL_PCT}%\n"
        f"scan every {config.SCAN_INTERVAL_SEC}s | monitor every {config.MONITOR_INTERVAL_SEC}s\n"
        f"daily: {daily['trades']} trades, {daily['realized_sol']:+.4f} SOL"
    )
    print("[boot] sending telegram...", flush=True)
    ok = await tg.send(msg)
    print(f"[boot] telegram sent: {ok}", flush=True)


async def get_my_address() -> str:
    import wallet
    return wallet.get_address()


async def evaluate_and_enter(candidates: list):
    bal = executor.get_balance_sol()
    if bal < 0.005:
        log(f"balance too low: {bal} SOL")
        return
    # Reserve fee/priority buffer
    free = max(0.0, bal - 0.008)
    if free <= 0:
        log("no free capital after buffer")
        return

    open_now = pos_mod.list_open().get("open", [])
    open_mints = {p["mint"] for p in open_now}

    for c in candidates:
        ok, reason = risk.can_open()
        if not ok:
            log(f"skip {c.get('symbol')} — {reason}")
            continue
        if c["mint"] in open_mints:
            continue
        kill, reason = risk.daily_kill_switch(STARTING_CAPITAL_SOL)
        if kill:
            log(f"KILL SWITCH: {reason}")
            await tg.send(f"⚠️ <b>DAILY KILL SWITCH</b>\n{reason}")
            return

        size = risk.position_size_sol(free)
        if size < 0.001:
            log("size below minimum")
            return

        log(f"BUY {c.get('symbol')} {c['mint']} size={size:.4f} SOL score={c.get('score',0):.2f}")
        result = await executor.buy_token(c["mint"], size)
        if not result.get("ok"):
            log(f"buy failed: {result.get('reason')}")
            await tg.send(f"❌ BUY FAIL {c.get('symbol')}: {result.get('reason')}")
            continue

        price = await price_feed.get_price(c["mint"])
        entry_price = price["priceUsd"] if price else 0.0
        pos_mod.open_position(
            mint=c["mint"],
            symbol=c.get("symbol") or c["mint"][:6],
            sol_in=size,
            price_usd=entry_price,
            tx_sig=result.get("sig", ""),
            source=c.get("source", ""),
        )
        await tg.send(
            f"✅ <b>BUY</b> {c.get('symbol')}\n"
            f"size: {size:.4f} SOL\n"
            f"entry: ${entry_price:.8f}\n"
            f"score: {c.get('score',0):.2f} | source: {c.get('source')}\n"
            f"slip: {result.get('price_impact_pct',0):.2f}%\n"
            f"tx: <code>{result.get('sig','')[:20]}...</code>"
        )
        open_mints.add(c["mint"])
        # single new entry per cycle
        return


async def monitor_positions():
    open_now = pos_mod.list_open().get("open", [])
    if not open_now:
        return
    for p in list(open_now):
        try:
            cur = await price_feed.get_price(p["mint"])
            if not cur or cur.get("priceUsd", 0) <= 0:
                continue
            cur_px = cur["priceUsd"]
            entry = p["entry_price_usd"]
            pct = ((cur_px / entry) - 1) * 100 if entry else 0
            hold_h = (time.time() - p["entry_ts"]) / 3600

            # Stale position timeout
            if hold_h >= config.MAX_HOLD_HOURS:
                await close_pos(p, cur_px, reason="timeout")
                continue

            # Stop Loss
            if pct <= -config.SL_PCT:
                await close_pos(p, cur_px, reason=f"SL -{config.SL_PCT}%")
                continue

            # TP1 — partial exit
            if not p.get("tp1_hit") and pct >= config.TP1_PCT:
                bal_raw = executor.get_token_balance_raw(p["mint"])
                if bal_raw > 0:
                    sell = await executor.sell_token(p["mint"], bal_raw, exit_pct=config.TP1_SIZE)
                    if sell.get("ok"):
                        sol_partial = sell.get("sol_received", 0)
                        pos_mod.update_position(p["mint"], tp1_hit=True)
                        await tg.send(
                            f"🟢 <b>TP1 hit</b> {p['symbol']}\n"
                            f"+{pct:.1f}% | partial exit {int(config.TP1_SIZE*100)}% "
                            f"= +{sol_partial:.4f} SOL\n"
                            f"tx: <code>{sell.get('sig','')[:20]}...</code>"
                        )

            # TP2 — full exit
            if not p.get("tp2_hit") and pct >= config.TP2_PCT:
                await close_pos(p, cur_px, reason=f"TP2 +{config.TP2_PCT}%")
                continue

            # Trailing stop after TP1
            if p.get("tp1_hit") and not p.get("tp2_hit"):
                # crude trailing: track peak since tp1
                peak = max(p.get("peak_pct", pct), pct)
                pos_mod.update_position(p["mint"], peak_pct=peak)
                if pct < peak - config.TRAILING_PCT:
                    await close_pos(p, cur_px, reason=f"trail -{config.TRAILING_PCT}% from peak {peak:.1f}%")

        except Exception as e:
            log(f"monitor err {p.get('mint')}: {e}")


async def close_pos(p: dict, exit_price_usd: float, reason: str):
    bal_raw = executor.get_token_balance_raw(p["mint"])
    if bal_raw <= 0:
        # nothing left — record zero pnl close
        closed = pos_mod.close_position(p["mint"], exit_price_usd, 0.0, reason, "")
        await tg.send(f"⚠️ CLOSED {p['symbol']} {reason} (balance=0)")
        return
    sell = await executor.sell_token(p["mint"], bal_raw, exit_pct=1.0)
    sol_out = sell.get("sol_received", 0.0) if sell.get("ok") else 0.0
    closed = pos_mod.close_position(p["mint"], exit_price_usd, sol_out, reason, sell.get("sig", ""))
    if closed:
        emoji = "🟢" if closed["pnl_sol"] > 0 else "🔴"
        await tg.send(
            f"{emoji} <b>CLOSE</b> {closed['symbol']} ({reason})\n"
            f"pnl: {closed['pnl_sol']:+.4f} SOL ({closed['pnl_pct']:+.1f}%)\n"
            f"hold: {(closed['close_ts']-closed['entry_ts'])/3600:.1f}h\n"
            f"tx: <code>{closed.get('close_tx','')[:20]}...</code>"
        )


async def scan_loop():
    while RUNNING:
        try:
            print("[scan] cycle start", flush=True)
            cands = await gmgn_signal.collect_candidates()
            print(f"[scan] {len(cands)} candidates", flush=True)
            if cands:
                await evaluate_and_enter(cands)
        except Exception as e:
            print(f"[scan err] {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
        print(f"[scan] sleeping {config.SCAN_INTERVAL_SEC}s...", flush=True)
        await asyncio.sleep(config.SCAN_INTERVAL_SEC)


async def monitor_loop():
    while RUNNING:
        try:
            await monitor_positions()
        except Exception as e:
            print(f"[monitor err] {type(e).__name__}: {e}", flush=True)
            import traceback
            traceback.print_exc()
        await asyncio.sleep(config.MONITOR_INTERVAL_SEC)


async def report_loop():
    while RUNNING:
        try:
            bal = executor.get_balance_sol()
            open_now = pos_mod.list_open().get("open", [])
            daily = pos_mod.get_daily()
            unrealized = 0.0
            for p in open_now:
                cur = await price_feed.get_price(p["mint"])
                if cur and cur.get("priceUsd") and p["entry_price_usd"]:
                    pct = (cur["priceUsd"] / p["entry_price_usd"] - 1) * 100
                    unrealized += p["sol_in"] * (pct / 100)
            wr = (daily["wins"] / max(daily["trades"], 1)) * 100
            msg = (
                f"📊 <b>HOURLY</b>\n"
                f"balance: <b>{bal:.4f} SOL</b>\n"
                f"open: {len(open_now)} | unrealized: {unrealized:+.4f} SOL\n"
                f"daily: {daily['trades']} trades ({wr:.0f}% WR)\n"
                f"realized: {daily['realized_sol']:+.4f} SOL"
            )
            await tg.send(msg)
        except Exception as e:
            log(f"report err: {e}")
        await asyncio.sleep(3600)


def shutdown_handler(*_):
    global RUNNING
    log("shutdown requested")
    RUNNING = False


async def main():
    log("prpo_ai sniper boot")
    try:
        await report_startup()
    except Exception as e:
        log(f"startup report failed: {e}")
    # Use loop.add_signal_handler for asyncio-safe shutdown (Linux/Mac)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, shutdown_handler)
        except (NotImplementedError, RuntimeError):
            signal.signal(sig, shutdown_handler)
    log("starting scan/monitor/report loops...")
    tasks = [
        asyncio.create_task(scan_loop(), name="scan"),
        asyncio.create_task(monitor_loop(), name="monitor"),
        asyncio.create_task(report_loop(), name="report"),
    ]
    log(f"{len(tasks)} tasks created. entering gather...")
    await asyncio.gather(*tasks, return_exceptions=True)
    log("all tasks ended. shutting down.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("interrupted")
    except Exception as e:
        log(f"FATAL: {e}")
        sys.exit(1)
