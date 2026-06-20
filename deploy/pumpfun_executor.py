"""
pumpfun_executor.py — direct on-chain swap for Pump.fun bonding curve.
NO Jupiter aggregator. Builds instructions manually using solders primitives.
Suitable for environments where quote-api.jup.ag is blocked.

Reference instruction layout:
  Pump.fun program: 6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P
  Instruction 'buy' discriminator:  [102, 6, 61, 18, 255, 87, 91, 111]
  Instruction 'sell' discriminator: [51, 230, 133, 164, 1, 127, 131, 173]

Bonding curve state layout (after 8-byte discriminator):
  0-8:   virtual_token_reserves (u64)
  8-16:  virtual_sol_reserves  (u64)
  16-24: real_token_reserves   (u64)
  24-32: real_sol_reserves     (u64)
  32-40: token_total_supply    (u64)
  40-48: complete              (bool, 1 byte)
"""
import struct
import json
import base64
from typing import Tuple, List

from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.instruction import Instruction, AccountMeta
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.hash import Hash

from spl.token.instructions import get_associated_token_address, create_associated_token_account
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID

import config
import wallet
from executor import get_client, get_balance_sol, confirm_tx


# Program constants
PUMP_PROGRAM = Pubkey.from_string("6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P")
PUMP_GLOBAL = Pubkey.from_string("4wTV1YmiEkRvAtNtsSGPtUrqRYQMe5N8i8Xvj4Lj8Q6P")
PUMP_FEE_RECIPIENT = Pubkey.from_string("CebN5WGQ4jvEPvsVU4EoHEpgzq1VV7AbicfbsWde3jTU")
PUMP_EVENT_AUTHORITY = Pubkey.from_string("Ce6TQbcnY6YyR4YDSsUdsyFyuV3GJcg26TUc6H7MaT98")
SYSTEM_PROGRAM = Pubkey.from_string("11111111111111111111111111111111")

BUY_DISCRIMINATOR = bytes([102, 6, 61, 18, 255, 87, 91, 111])
SELL_DISCRIMINATOR = bytes([51, 230, 133, 164, 1, 127, 131, 173])


def find_bonding_curve(mint: Pubkey) -> Pubkey:
    """PDA: seeds = ['bonding-curve', mint_key]"""
    pda, _bump = Pubkey.find_program_address([b"bonding-curve", bytes(mint)], PUMP_PROGRAM)
    return pda


def get_curve_vault_pubkey(mint: Pubkey) -> Pubkey:
    """Vault = bonding curve's ATA for the mint"""
    curve = find_bonding_curve(mint)
    return get_associated_token_address(curve, mint, TOKEN_PROGRAM_ID)


def get_bonding_curve_state(curve: Pubkey) -> dict | None:
    """Read bonding curve account to get reserves + completion status."""
    try:
        c = get_client()
        info = c.get_account_info(curve)
        if not info.value:
            return None
        data = info.value.data
        if len(data) < 49:
            return None
        vtr = struct.unpack("<Q", data[8:16])[0]
        vsr = struct.unpack("<Q", data[16:24])[0]
        rtr = struct.unpack("<Q", data[24:32])[0]
        rsr = struct.unpack("<Q", data[32:40])[0]
        tts = struct.unpack("<Q", data[40:48])[0]
        complete = data[48] != 0
        return {
            "virtual_token_reserves": vtr,
            "virtual_sol_reserves": vsr,
            "real_token_reserves": rtr,
            "real_sol_reserves": rsr,
            "token_total_supply": tts,
            "complete": complete,
        }
    except Exception as e:
        print(f"[curve state err] {e}")
        return None


def compute_buy_amount_out(sol_in_lamports: int, state: dict) -> int:
    """Constant-product formula using virtual reserves."""
    if state.get("complete"):
        return 0
    vtr = state["virtual_token_reserves"]
    vsr = state["virtual_sol_reserves"]
    if vtr == 0 or vsr == 0:
        return 0
    k = vtr * vsr
    new_vsr = vsr + sol_in_lamports
    new_vtr = k // new_vsr
    tokens_out = vtr - new_vtr
    return max(0, tokens_out)


def compute_sell_amount_out(token_amount: int, state: dict) -> int:
    if state.get("complete"):
        return 0
    vtr = state["virtual_token_reserves"]
    vsr = state["virtual_sol_reserves"]
    if vtr == 0 or vsr == 0:
        return 0
    k = vtr * vsr
    new_vtr = vtr + token_amount
    if new_vtr == 0:
        return 0
    new_vsr = k // new_vtr
    sol_out = vsr - new_vsr
    return max(0, sol_out)


def _buy_accounts(mint: Pubkey, user: Pubkey) -> Tuple[Pubkey, Pubkey, Pubkey, List[AccountMeta]]:
    curve = find_bonding_curve(mint)
    curve_vault = get_curve_vault_pubkey(mint)
    user_ata = get_associated_token_address(user, mint, TOKEN_PROGRAM_ID)
    accounts = [
        AccountMeta(pubkey=PUMP_GLOBAL, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_FEE_RECIPIENT, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
        AccountMeta(pubkey=curve, is_signer=False, is_writable=True),
        AccountMeta(pubkey=curve_vault, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user, is_signer=True, is_writable=True),
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_EVENT_AUTHORITY, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_PROGRAM, is_signer=False, is_writable=False),
    ]
    return curve, curve_vault, user_ata, accounts


def _sell_accounts(mint: Pubkey, user: Pubkey) -> List[AccountMeta]:
    curve = find_bonding_curve(mint)
    curve_vault = get_curve_vault_pubkey(mint)
    user_ata = get_associated_token_address(user, mint, TOKEN_PROGRAM_ID)
    return [
        AccountMeta(pubkey=PUMP_GLOBAL, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_FEE_RECIPIENT, is_signer=False, is_writable=True),
        AccountMeta(pubkey=mint, is_signer=False, is_writable=False),
        AccountMeta(pubkey=curve, is_signer=False, is_writable=True),
        AccountMeta(pubkey=curve_vault, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user_ata, is_signer=False, is_writable=True),
        AccountMeta(pubkey=user, is_signer=True, is_writable=True),
        AccountMeta(pubkey=SYSTEM_PROGRAM, is_signer=False, is_writable=False),
        AccountMeta(pubkey=ASSOCIATED_TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_EVENT_AUTHORITY, is_signer=False, is_writable=False),
        AccountMeta(pubkey=PUMP_PROGRAM, is_signer=False, is_writable=False),
    ]


def buy_pumpfun(mint_str: str, sol_amount: float, slippage_bps: int = 3000) -> dict:
    """Buy token on Pump.fun bonding curve directly."""
    try:
        kp = wallet.load_keypair()
        user = kp.pubkey()
        mint = Pubkey.from_string(mint_str)

        sol_in_lamports = int(sol_amount * 1e9)
        if sol_in_lamports < 100_000:
            return {"ok": False, "reason": "below_min_100k_lamports"}

        curve = find_bonding_curve(mint)
        state = get_bonding_curve_state(curve)
        if not state:
            return {"ok": False, "reason": "no_curve_state", "curve": str(curve)}
        if state.get("complete"):
            return {"ok": False, "reason": "curve_complete_migrated",
                    "hint": "use Raydium executor"}

        tokens_out = compute_buy_amount_out(sol_in_lamports, state)
        if tokens_out <= 0:
            return {"ok": False, "reason": "no_tokens_out_computed"}

        min_tokens_out = max(1, int(tokens_out * (1 - slippage_bps / 10000)))

        # Build ix: amount(u64) + max_sol_cost(u64)
        # Note: Pump.fun buy order is: amount, max_sol_cost
        buy_data = BUY_DISCRIMINATOR + struct.pack("<QQ", tokens_out, sol_in_lamports)

        _, _, _, buy_accounts = _buy_accounts(mint, user)
        ix_buy = Instruction(program_id=PUMP_PROGRAM, data=buy_data, accounts=buy_accounts)
        ix_ata = create_associated_token_account(payer=user, owner=user, mint=mint)

        # Build & sign
        c = get_client()
        bh_resp = c.get_latest_blockhash()
        if not bh_resp.value:
            return {"ok": False, "reason": "no_blockhash"}
        bh = bh_resp.value.blockhash

        msg = MessageV0.try_compile(
            payer=user,
            instructions=[ix_ata, ix_buy],
            address_lookup_table_accounts=[],
            recent_blockhash=bh,
        )
        tx = VersionedTransaction(msg, [kp])
        raw = bytes(tx)

        send_resp = c.send_raw_transaction(raw, opts={"skip_preflight": False, "max_retries": 3})
        if not send_resp.value:
            return {"ok": False, "reason": "send_no_sig"}
        sig = str(send_resp.value)
        print(f"[pumpfun buy] tx sent: {sig}")

        confirmed = confirm_tx(sig, timeout_sec=90)
        return {
            "ok": confirmed,
            "sig": sig,
            "sol_spent": sol_amount,
            "tokens_est": tokens_out,
            "min_tokens_out": min_tokens_out,
            "curve": str(curve),
            "confirmed": confirmed,
            "reason": "ok" if confirmed else "tx_unconfirmed",
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "reason": f"exception:{type(e).__name__}:{e}"}


def sell_pumpfun(mint_str: str, token_amount_raw: int, exit_pct: float = 1.0,
                 slippage_bps: int = 3000) -> dict:
    """Sell token on Pump.fun bonding curve directly."""
    try:
        kp = wallet.load_keypair()
        user = kp.pubkey()
        mint = Pubkey.from_string(mint_str)

        sell_amount = int(token_amount_raw * exit_pct)
        if sell_amount <= 0:
            return {"ok": False, "reason": "zero_amount"}

        curve = find_bonding_curve(mint)
        state = get_bonding_curve_state(curve)
        if not state:
            return {"ok": False, "reason": "no_curve_state"}
        if state.get("complete"):
            return {"ok": False, "reason": "curve_complete"}

        sol_out = compute_sell_amount_out(sell_amount, state)
        min_sol_out = max(0, int(sol_out * (1 - slippage_bps / 10000)))

        sell_data = SELL_DISCRIMINATOR + struct.pack("<QQ", sell_amount, min_sol_out)
        sell_accounts = _sell_accounts(mint, user)
        ix_sell = Instruction(program_id=PUMP_PROGRAM, data=sell_data, accounts=sell_accounts)

        c = get_client()
        bh_resp = c.get_latest_blockhash()
        if not bh_resp.value:
            return {"ok": False, "reason": "no_blockhash"}
        bh = bh_resp.value.blockhash

        msg = MessageV0.try_compile(
            payer=user,
            instructions=[ix_sell],
            address_lookup_table_accounts=[],
            recent_blockhash=bh,
        )
        tx = VersionedTransaction(msg, [kp])
        raw = bytes(tx)

        send_resp = c.send_raw_transaction(raw, opts={"skip_preflight": False, "max_retries": 3})
        if not send_resp.value:
            return {"ok": False, "reason": "send_no_sig"}
        sig = str(send_resp.value)
        confirmed = confirm_tx(sig, timeout_sec=90)
        return {
            "ok": confirmed,
            "sig": sig,
            "sol_received": sol_out / 1e9,
            "confirmed": confirmed,
            "reason": "ok" if confirmed else "tx_unconfirmed",
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"ok": False, "reason": f"exception:{type(e).__name__}:{e}"}


if __name__ == "__main__":
    test = "u4Vm5MLYiut3Efiy92rJPWLXHRSXbKLwDt9yr9spump"  # GARY (real Pump.fun mint)
    mint = Pubkey.from_string(test)
    curve = find_bonding_curve(mint)
    state = get_bonding_curve_state(curve)
    print(f"Mint: {test}")
    print(f"Curve: {curve}")
    print(f"State: {state}")
    if state and not state.get("complete"):
        sol_lamports = 12_000_000
        out = compute_buy_amount_out(sol_lamports, state)
        print(f"Buy 0.012 SOL -> est tokens (raw): {out}")
        if out > 0:
            # Get token decimals from mint
            from executor import get_client
            c = get_client()
            mint_info = c.get_account_info(mint)
            if mint_info.value:
                decimals = mint_info.value.data[44]  # mint decimals byte offset
                print(f"Token decimals: {decimals}")
                print(f"Buy 0.012 SOL -> est tokens (UI): {out / (10 ** decimals):.4f}")
