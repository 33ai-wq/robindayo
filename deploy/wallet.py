"""
Wallet module - load keypair from private key (base58 or JSON array)
"""
import json
import base58
from solders.keypair import Keypair
import config


def load_keypair() -> Keypair:
    raw = config.PRIVATE_KEY.strip()
    # JSON array format
    if raw.startswith("["):
        try:
            secret = bytes(json.loads(raw))
            return Keypair.from_bytes(secret)
        except Exception as e:
            raise RuntimeError(f"PRIVATE_KEY JSON array parse failed: {e}")
    # base58 format
    try:
        secret = base58.b58decode(raw)
        return Keypair.from_bytes(secret)
    except Exception as e:
        raise RuntimeError(f"PRIVATE_KEY base58 parse failed: {e}")


def get_address() -> str:
    kp = load_keypair()
    return str(kp.pubkey())


if __name__ == "__main__":
    try:
        addr = get_address()
        print(f"OK wallet loaded. Address: {addr}")
        if config.WALLET_ADDRESS and config.WALLET_ADDRESS != addr:
            print(f"WARN: WALLET_ADDRESS_SOL in env ({config.WALLET_ADDRESS}) differs from derived ({addr})")
    except Exception as e:
        print(f"FAIL: {e}")
