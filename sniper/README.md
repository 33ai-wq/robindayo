# prpo_ai Meme Sniper — Solana

Autonomous meme-coin sniper + smart-money copy-trade. Designed for small-capital
survival: strict filters, tight risk guardrails, Telegram visibility.

## Architecture

  sniper/
    bot.py            # orchestrator (scan/monitor/report loops)
    config.py         # env loader + tunable strategy params
    wallet.py         # keypair loader (base58 / JSON array)
    telegram.py       # async notifier to B0x70
    price_feed.py     # multi-source price (DexScreener + Birdeye fallback)
    gmgn_signal.py    # candidate discovery (DexScreener boosted + trending)
    executor.py       # Jupiter Aggregator v6 swap execution
    position.py       # local JSON position ledger (open/closed/daily)
    risk.py           # pre-trade guardrails (kill switch, cooldown, sizing)
    state/            # runtime JSON state
    logs/             # stderr stdout
    reports/          # periodic summary outputs

## Required env (.env at /root/.hermes/profiles/prpo_ai/.env, chmod 600)

    PRIVATE_KEY_SOL_TREASURY=<base58 or JSON array of 64 bytes>
    SOL_RPC_URL=https://api.mainnet-beta.solana.com    # or premium (Helius/QuickNode)
    TELEGRAM_BOT_TOKEN=<from @BotFather>
    TELEGRAM_CHAT_ID=1963809645                         # B0x70 chat

    # Optional (improves signal + speeds up price feed)
    BIRDEYE_API_KEY=
    WALLET_ADDRESS_SOL=7P7w3M9yQs5PCH2WbfmMxVWnkrobVsq1ARZBFfJ5W5zN
    HELIUS_API_KEY=

    # Tunables (defaults shown — override per risk appetite)
    SNIPER_MIN_LIQ_USD=15000
    SNIPER_MIN_VOL24H_USD=25000
    SNIPER_MIN_HOLDERS=150
    SNIPER_MAX_CANDIDATES=8
    SNIPER_RISK_PCT=0.20
    SNIPER_MAX_PER_TRADE_SOL=0.015
    SNIPER_HARD_TRADE_CAP_SOL=0.020
    SNIPER_MAX_OPEN=3
    SNIPER_MAX_DAILY_TRADES=10
    SNIPER_MAX_DAILY_DD_PCT=30
    SNIPER_LOSS_STREAK=3
    SNIPER_COOLDOWN_MIN=60
    SNIPER_SLIPPAGE_BPS=2000
    SNIPER_PRIO_FEE_LAMP=10000
    SNIPER_USE_JITO=false
    SNIPER_TP1_PCT=30
    SNIPER_TP2_PCT=80
    SNIPER_TP1_SIZE=0.50
    SNIPER_SL_PCT=30
    SNIPER_TRAIL_PCT=20
    SNIPER_MAX_HOLD_HOURS=24
    SNIPER_SCAN_INTERVAL=120
    SNIPER_MONITOR_INTERVAL=30

## Run

    source /root/.venv-sniper/bin/activate
    cd /root/prpo_ai/sniper
    python bot.py

## Strategy

  - Signal: DexScreener `token-boosts/latest/v1` (newest boosted = early launches)
    + DexScreener `search?q=solana%20pump` (volume momentum).
  - Filter gates (any fail = reject):
      liq >= $15k   vol24 >= $25k   holders >= 150
      age 0.25h - 72h   pc24h > -50%
      buy/sell ratio >= 0.30 (else exit liquidity)
  - Sizing: MIN(free*20%, max_per_trade $0.015). Hard cap $0.020.
  - Entries: TP1 +30% exit 50%, TP2 +80% exit rest.
  - Stop: -30% hard SL OR max hold 24h.
  - Trailing: after TP1, trail 20% from peak.

## Risk guardrails (B0x70)

  - Max 3 open positions concurrent
  - Max 10 trades/day
  - Daily drawdown >= 30% -> kill switch (Telegram alert + halt)
  - 3 losses in 1h -> 60min cooldown (no new entries)
  - Position timeout: 24h (auto-close to free capital)
  - All actions persist to state/positions.json (survives restart)
  - Manual kill: `pkill -f "sniper/bot.py"`

## Reality check (B0x70 should read)

  - Capital $4.90, target $70k = 14,285x. NOT achievable via sniper.
  - Realistic outcome: compound profit OR total loss. No middle path.
  - Expected monthly variance: -50% to +30% on capital.
  - Bot is designed to SURVIVE, not moon. If you want moon, you need
    asymmetric bet (not sniper). Use this for income, not lottery.
