#!/usr/bin/env python3
"""
save_keys.py — secure stdin-based key entry for VPS deployment.
Reads 4 secrets from stdin (one per line) and appends to .env.
Does NOT echo values, does NOT log, does NOT write to shell history.

Usage:
  python3 save_keys.py
"""
import sys
import os
from pathlib import Path

ENV = Path("/root/.hermes/profiles/prpo_ai/.env")
KEYS = [
    ("PRIVATE_KEY_SOL_TREASURY", "SOL private key (base58 or JSON array)"),
    ("RPC_URL", "Solana RPC URL (e.g. https://mainnet.helius-rpc.com/?api-key=XXX)"),
    ("TELEGRAM_BOT_TOKEN", "Telegram bot token from @BotFather"),
    ("TELEGRAM_CHAT_ID", "Telegram chat ID (numeric, default 1963809645)"),
    ("HELIUS_API_KEY", "Helius API key (https://helius.dev) [optional]"),
]


def getpass(prompt):
    print(prompt, end="", flush=True)
    try:
        return open("/dev/tty").readline().rstrip("\n")
    except Exception:
        return sys.stdin.readline().rstrip("\n")


def mask_existing(env_path):
    text = env_path.read_text() if env_path.exists() else ""
    return {k: ("SET" if any(line.startswith(k + "=") and len(line) > len(k) + 5
                              for line in text.splitlines())
                  else "NOT_SET")
            for k, _ in KEYS}


def main():
    if not ENV.exists():
        print(f"FATAL: {ENV} not found", file=sys.stderr)
        sys.exit(1)
    print(f"Target: {ENV}")
    cur = mask_existing(ENV)
    print("Current state:")
    for k, label in KEYS:
        print(f"  [{cur[k]:>8}]  {k}  ({label})")
    print()
    if getpass("Proceed? Type 'yes' to continue: ").strip().lower() != "yes":
        print("aborted")
        return

    new_values = {}
    for k, label in KEYS:
        optional = k in ("HELIUS_API_KEY",)
        prompt = f"  {k} ({label}){' [optional]' if optional else ''}: "
        v = getpass(prompt).strip()
        if not v and optional:
            print(f"    -> skip")
            continue
        if not v:
            print(f"    -> EMPTY (not saved)")
            continue
        new_values[k] = v

    if not new_values:
        print("\nNothing to update. Exit.")
        return

    lines = ENV.read_text().splitlines()
    updated = set()
    new_lines = []
    for line in lines:
        replaced = False
        for k in new_values:
            if line.startswith(k + "="):
                new_lines.append(f"{k}={new_values[k]}")
                updated.add(k)
                replaced = True
                break
        if not replaced:
            new_lines.append(line)
    for k, v in new_values.items():
        if k not in updated:
            new_lines.append(f"{k}={v}")

    print("\nPreview (lengths only):")
    for k, v in new_values.items():
        print(f"  {k} = (len={len(v)})")
    if getpass("\nSave these? Type 'yes' to confirm: ").strip().lower() != "yes":
        print("aborted")
        return

    backup = ENV.with_suffix(".env.bak")
    if backup.exists():
        backup = ENV.with_suffix(f".env.bak.{int(os.path.getmtime(ENV))}")
    backup.write_text(ENV.read_text())
    os.chmod(backup, 0o600)
    ENV.write_text("\n".join(new_lines) + "\n")
    os.chmod(ENV, 0o600)
    print(f"\nSaved {len(new_values)} keys to {ENV}")
    print(f"Backup: {backup}")
    print(f"Perms:  {oct(ENV.stat().st_mode & 0o777)}")


if __name__ == "__main__":
    main()
