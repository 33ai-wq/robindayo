#!/usr/bin/env python3
"""
fix_env.py — strip leading '+' from KEY=VALUE lines in .env
- Backup before write
- Skip empty lines and lines starting with # (preserve comments)
- Strip '+' ONLY from lines that match KEY=VALUE pattern
- Preserves original line content for all other lines (whitespace, etc.)
- Verifies after write
"""
import os
import re
from pathlib import Path

ENV = Path("/root/.hermes/profiles/prpo_ai/.env")
BACKUP = ENV.with_suffix(".env.bak." + str(int(os.path.getmtime(ENV))))
KEY_VAL_RE = re.compile(r"^\+?([A-Z_][A-Z0-9_]*)=(.*)$")


def main():
    raw = ENV.read_bytes().decode("utf-8", errors="replace")
    lines = raw.split("\n")

    new_lines = []
    fixed = 0
    for line in lines:
        stripped = line.lstrip()
        # Empty line
        if not stripped:
            new_lines.append(line)
            continue
        # Standard comment
        if stripped.startswith("#"):
            new_lines.append(line)
            continue
        # KEY=VALUE pattern (with optional leading +)
        m = KEY_VAL_RE.match(line)
        if m:
            key, val = m.group(1), m.group(2)
            new_lines.append(f"{key}={val}")
            fixed += 1
        else:
            new_lines.append(line)

    # Write backup first
    BACKUP.write_text(raw)
    os.chmod(BACKUP, 0o600)

    # Write fixed
    ENV.write_text("\n".join(new_lines))
    os.chmod(ENV, 0o600)

    print(f"✓ Fixed {fixed} lines")
    print(f"✓ Backup: {BACKUP}")
    print(f"✓ Wrote:  {ENV}")
    print(f"✓ Perms:  {oct(ENV.stat().st_mode & 0o777)}")

    # Verify by re-reading and checking key presence
    print()
    print("=== POST-FIX VERIFY ===")
    content = ENV.read_text().splitlines()
    keys_to_check = [
        "PRIVATE_KEY_TREASURY_ADDRESS_03",
        "PUMFUN_PRIVATE_KEY",
        "HELIUS_API_KEY",
        "RPC_URL",
        "TELEGRAM_CHAT_ID_PRPOAI",
        "TELEGRAM_HOME_CHANNEL",
        "TELEGRAM_BOT_TOKEN",
    ]
    for k in keys_to_check:
        for line in content:
            if line.startswith(k + "="):
                v = line[len(k) + 1:].strip()
                print(f"  {'✓' if v else '✗'} {k:<42} len={len(v)}")
                break
        else:
            print(f"  ✗ {k:<42} NOT FOUND")


if __name__ == "__main__":
    main()
