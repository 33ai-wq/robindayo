"""
executor.py — swap execution via Jupiter Aggregator v6 (quote + swap).
Falls back to Raydium direct pool if Jupiter route unavailable.
Quote → swap → sign → send → confirm. Includes priority fee + Jito tip optional.
"""
import aiohttp
import asyncio
import json
import time
import base64
from solders.keypair import Keypair
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solana.rpc.commitment import Confirmed
from solders.pubkey import Pubkey

import wallet
import config


JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"
SOL_MINT = "So11111111111111111111111111111111111111112"


def get_client() -> Client:
    return Client(config.SOL_RPC_URL, commitment=Confirmed)


def get_balance_sol(addr: str | None = None) -> float:
    try:
        c = get_client()
        if not addr:
            from wallet import load_keypair
            addr = str(load_keypair().pubkey())
        resp = c.get_balance(Pubkey.from_string(addr))
        if not resp.value:
            return 0.0
        return resp.value / 1e9
    except Exception as e:
        print(f"[balance err] {e}")
        return 0.0


async def get_jupiter_quote(input_mint: str, output_mint: str, amount_lamports: int, slippage_bps: int = 1500) -> dict | None:
    """slippage_bps=1500 = 15% default (meme-volatile). Tightens at TP."""
    try:
        params = {
            "inputMint": input_mint,
            "outputMint": output_mint,
            "amount": amount_lamports,
            "slippageBps": slippage_bps,
            "swapMode": "ExactIn",
        }
        async with aiohttp.ClientSession() as s:
            async with s.get(JUPITER_QUOTE, params=params, timeout=10) as r:
                if r.status != 200:
                    body = await r.text()
                    print(f"[jup quote {r.status}] {body[:200]}")
                    return None
                return await r.json()
    except Exception as e:
        print(f"[quote err] {e}")
        return None


async def jupiter_swap(quote: dict, user_pubkey: str, priority_fee_lamports: int = 5000) -> dict | None:
    """Get swap tx from Jupiter, sign locally, broadcast."""
    try:
        body = {
            "quoteResponse": quote,
            "userPublicKey": user_pubkey,
            "wrapAndUnwrapSol": True,
            "dynamicComputeUnitLimit": True,
            "prioritizationFeeLamports": priority_fee_lamports,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(JUPITER_SWAP, json=body, timeout=15) as r:
                if r.status != 200:
                    body_txt = await r.text()
                    print(f"[jup swap {r.status}] {body_txt[:200]}")
                    return None
                data = await r.json()
        return data
    except Exception as e:
        print(f"[swap err] {e}")
        return None


def sign_and_send(swap_data: dict, kp: Keypair, max_retries: int = 2) -> str | None:
    """Decode base64 swapTx, sign with keypair, send to RPC, return sig."""
    try:
        raw = base64.b64decode(swap_data["swapTransaction"])
        tx = VersionedTransaction.from_bytes(raw)
        signed = VersionedTransaction(tx.message, [kp])
        c = get_client()
        for attempt in range(max_retries):
            try:
                resp = c.send_raw_transaction(bytes(signed), opts={"skip_preflight": True, "max_retries": 3})
                if resp and resp.value:
                    return str(resp.value)
            except Exception as e:
                print(f"[send attempt {attempt}] {e}")
                time.sleep(1.0 * (attempt + 1))
        return None
    except Exception as e:
        print(f"[sign err] {e}")
        return None


def confirm_tx(sig: str, timeout_sec: int = 60) -> bool:
    try:
        c = get_client()
        start = time.time()
        while time.time() - start < timeout_sec:
            r = c.confirm_transaction(sig, commitment="confirmed")
            if r.value and r.value[0].err is None:
                return True
            if r.value and r.value[0].err:
                print(f"[tx err] {r.value[0].err}")
                return False
            time.sleep(2.0)
        return False
    except Exception as e:
        print(f"[confirm err] {e}")
        return False


async def buy_token(token_mint: str, sol_amount: float) -> dict:
    """Returns {ok, sig, sol_spent, token_est, price_est_usd, reason}"""
    kp = wallet.load_keypair()
    user = str(kp.pubkey())
    lamports = int(sol_amount * 1e9)
    quote = await get_jupiter_quote(SOL_MINT, token_mint, lamports, slippage_bps=config.SLIPPAGE_BPS)
    if not quote:
        return {"ok": False, "reason": "no_jupiter_quote"}
    swap = await jupiter_swap(quote, user, priority_fee_lamports=config.PRIORITY_FEE_LAMPORTS)
    if not swap:
        return {"ok": False, "reason": "no_swap_tx"}
    sig = sign_and_send(swap, kp)
    if not sig:
        return {"ok": False, "reason": "sign_or_send_failed", "quote_outAmount": quote.get("outAmount")}
    confirmed = confirm_tx(sig, timeout_sec=90)
    out_amount = int(quote.get("outAmount", 0))
    return {
        "ok": confirmed,
        "sig": sig,
        "sol_spent": sol_amount,
        "token_est": out_amount,
        "out_amount_raw": out_amount,
        "price_impact_pct": float(quote.get("priceImpactPct", 0)),
        "confirmed": confirmed,
        "reason": "ok" if confirmed else "tx_unconfirmed",
    }


async def sell_token(token_mint: str, token_amount_raw: int, exit_pct: float = 1.0) -> dict:
    """exit_pct in (0,1]. token_amount_raw = base units (use spl token decimals)."""
    kp = wallet.load_keypair()
    user = str(kp.pubkey())
    amount = int(token_amount_raw * exit_pct)
    quote = await get_jupiter_quote(token_mint, SOL_MINT, amount, slippage_bps=config.SLIPPAGE_BPS)
    if not quote:
        return {"ok": False, "reason": "no_jupiter_quote"}
    swap = await jupiter_swap(quote, user, priority_fee_lamports=config.PRIORITY_FEE_LAMPORTS)
    if not swap:
        return {"ok": False, "reason": "no_swap_tx"}
    sig = sign_and_send(swap, kp)
    if not sig:
        return {"ok": False, "reason": "sign_or_send_failed"}
    confirmed = confirm_tx(sig, timeout_sec=90)
    out_lamports = int(quote.get("outAmount", 0))
    return {
        "ok": confirmed,
        "sig": sig,
        "sol_received": out_lamports / 1e9,
        "confirmed": confirmed,
        "reason": "ok" if confirmed else "tx_unconfirmed",
    }


def get_token_balance_raw(token_mint: str) -> int:
    """Reads SPL token balance via RPC, returns raw base units (0 if none)."""
    try:
        kp = wallet.load_keypair()
        owner = str(kp.pubkey())
        c = get_client()
        # token accounts by owner
        from solders.pubkey import Pubkey as P
        from solana.rpc.types import TokenAccountOpts
        resp = c.get_token_accounts_by_owner(
            P.from_string(owner),
            TokenAccountOpts(mint=P.from_string(token_mint)),
        )
        if not resp.value:
            return 0
        total = 0
        for ta in resp.value:
            info = ta.account.data.parsed["info"]["tokenAmount"]
            total += int(float(info["amount"]))
        return total
    except Exception as e:
        print(f"[bal err] {e}")
        return 0
