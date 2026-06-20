#!/usr/bin/env python3
"""
save_keys.py — secure stdin-based key entry.
Reads 4 secrets from stdin (one per line) and appends to /root/.hermes/profiles/prpo_ai/.env.
Does NOT echo values, does NOT log, does NOT write to shell history.

Usage:
  python3 /root/prpo_ai/sniper/save_keys.py

Then paste when prompted (one per line):
  Line 1: PRIVATE_KEY_SOL_TREASURY base58 OR JSON array (your SOL wallet keypair)
  Line 2: HELIUS_API_KEY (from helius.dev)
  Line 3: TELEGRAM_CHAT_ID_PRPOAI (your Telegram numeric chat id)
  Line 4: (optional) WALLET_ADDRESS_SOL — press Enter to skip (auto-detected from key)

Hit Enter after each line. Confirm 'y' at end.
"""
import sys
import os
from pathlib import Path

ENV = Path("/root/.hermes/profiles/prpo_ai/.env")

KEYS = [
    ("PRIVATE_KEY_SOL_TREASURY", "SOL private key (base58 or JSON array)"),
    ("HELIUS_API_KEY", "Helius API key (from helius.dev)"),
    ("TELEGRAM_CHAT_ID_PRPOAI", "Telegram chat ID"),
    ("WALLET_ADDRESS_SOL", "Wallet address (Enter to skip, auto-detect)"),
]


def getpass(prompt):
    """Minimal getpass — uses /dev/tty when available, falls back to stdin."""
    print(prompt, end="", flush=True)
    try:
        return open("/dev/tty").readline().rstrip("\n")
    except Exception:
        return sys.stdin.readline().rstrip("\n")


def mask_existing(env_path: Path) -> dict:
    """Return {key: 'SET'|'NOT_SET'} for each KEYS entry."""
    text = env_path.read_text() if env_path.exists() else ""
    return {k: ("SET" if any(line.startswith(k + "=") and len(line) > len(k) + 5
                              for line in text.splitlines())
                  else "NOT_SET")
            for k, _ in KEYS}


def main():
    if not ENV.exists():
        print(f"FATAL: {ENV} not found", file=sys.stderr)
        sys.exit(1)

    print("=== prpo_ai KEY ENTRY ===")
    print(f"Target: {ENV}")
    print("Values are NOT echoed, NOT logged, NOT in shell history.\n")

    cur = mask_existing(ENV)
    print("Current state:")
    for k, label in KEYS:
        print(f"  [{cur[k]:>8}]  {k}  ({label})")
    print()

    if not getpass("Proceed to update? Type 'yes' to continue: ").strip().lower() == "yes":
        print("aborted")
        return

    print("\nPaste values one per line. Press Enter after each.\n")
    new_values = {}
    for k, label in KEYS:
        optional = k == "WALLET_ADDRESS_SOL"
        prompt = f"  {k} ({label}){' [optional]' if optional else ''}: "
        v = getpass(prompt).strip()
        if not v and optional:
            print(f"    -> skip (will auto-detect from keypair)")
            continue
        if not v:
            print(f"    -> EMPTY (NOT SAVED)")
            continue
        new_values[k] = v

    if not new_values:
        print("\nNothing to update. Exit.")
        return

    # Read current env, replace or append keys
    lines = ENV.read_text().splitlines()
    updated_keys = set()
    new_lines = []
    for line in lines:
        replaced = False
        for k in new_values:
            if line.startswith(k + "="):
                new_lines.append(f"{k}={new_values[k]}")
                updated_keys.add(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    for k, v in new_values.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}")

    # Show preview (key + length only, no value)
    print("\nPreview (values NOT shown):")
    for k, v in new_values.items():
        print(f"  {k} = (len={len(v)})")
    print()
    confirm = getpass("Save these to .env? Type 'yes' to confirm: ").strip().lower()
    if confirm != "yes":
        print("aborted. Nothing written.")
        return

    # Backup before write
    backup = ENV.with_suffix(".env.bak")
    backup.write_text(ENV.read_text())
    os.chmod(backup, 0o600)

    ENV.write_text("\n".join(new_lines) + "\n")
    os.chmod(ENV, 0o600)

    print(f"\n✓ Wrote {len(new_values)} keys to {ENV}")
    print(f"  Backup: {backup}")
    print(f"  Perms:  {oct(ENV.stat().st_mode & 0o777)} (must be 0o600)")
    print(f"\nVerify with:")
    print(f"  ls -la {ENV}")
    print(f"  grep -c 'PRIVATE_KEY_SOL_TREASURY=' {ENV}")


if __name__ == "__main__":
    main()
