# prpo_ai — Hybrid Deployment Guide (SnapDeploy + GitHub Actions)

Target: Trading bot 24/7 tanpa kartu kredit. Modal $0/bulan.

## ARSITEKTUR

```
┌─────────────────────────────────────────────────────────┐
│ GitHub Actions (FREE, no CC)                            │
│  - cron setiap 15 menit                                 │
│  - signal-only scan via DexScreener                    │
│  - kirim alert ke Telegram                              │
│  - ping healthcheck ke SnapDeploy                       │
│  Quota: 2000 menit/bulan (pakai ~5%)                   │
└─────────────────────────────────────────────────────────┘
                         ↓
                    Telegram 1963809645
                         ↑
┌─────────────────────────────────────────────────────────┐
│ SnapDeploy (FREE $5 credit, no CC)                     │
│  - Docker container 24/7                               │
│  - sniper bot full execution                           │
│  - Jupiter routing + Pump.fun direct                   │
│  - 1-2 minggu runtime dari $5 credit                   │
└─────────────────────────────────────────────────────────┘
```

## STEP 1: Setup SnapDeploy (10 menit)

1. Buka https://snapdeploy.dev
2. Sign up dengan GitHub account (33ai-wq)
3. Klik "New Project" → "Docker"
4. Pilih repo: `33ai-wq/prpo_ai`
5. Dockerfile path: `sniper/Dockerfile`
6. Port: kosongkan (sniper tidak expose port; pakai Telegram untuk monitoring)
7. Environment variables (Add):
   - `PRIVATE_KEY_SOL_TREASURY` = (paste dari .env HP)
   - `RPC_URL` = `https://mainnet.helius-rpc.com/?api-key=XXX`
   - `TELEGRAM_BOT_TOKEN` = (sama)
   - `TELEGRAM_CHAT_ID` = `1963809645`
   - `HELIUS_API_KEY` = (Helius key)
8. Plan: pilih free $5 credit tier
9. Deploy → tunggu build 3-5 menit
10. SnapDeploy otomatis expose URL: `https://prpo-ai-XXX.snapdeploy.app`
    (Catat URL ini untuk healthcheck dari GitHub Actions)

## STEP 2: Setup GitHub Actions secrets (5 menit)

1. Buka https://github.com/33ai-wq/prpo_ai/settings/secrets/actions
2. Klik "New repository secret", tambahkan:
   - `TELEGRAM_BOT_TOKEN` = (token bot)
   - `TELEGRAM_CHAT_ID` = `1963809645`
   - `SNAPDEPLOY_URL` = (URL dari Step 1.10)

## STEP 3: Push workflow ke repo (2 menit)

Workflows sudah saya tulis di:
- `.github/workflows/sniper-scan.yml` (cron scan + healthcheck)
- `.github/scripts/scan_and_alert.py` (signal-only scanner)

B0x70 push ke repo:

```bash
cd /root/prpo_ai
git add .github/
git commit -m "Add GitHub Actions sniper-scan workflow"
git push origin master
```

Workflow akan otomatis trigger dan scan tiap 15 menit.

## STEP 4: Monitor

### SnapDeploy dashboard:
- Buka https://snapdeploy.dev/dashboard
- Lihat logs container
- Monitor credit usage (dari $5 free)

### GitHub Actions:
- Buka https://github.com/33ai-wq/prpo_ai/actions
- Lihat workflow runs

### Telegram:
- Akan terima alert tiap 15 menit dari GitHub Actions
- Akan terima trade alerts dari SnapDeploy (real-time)

## STEP 5: Renewal Strategy

Setelah $5 credit SnapDeploy habis (~2 minggu):

OPSI 1 — Buat akun SnapDeploy baru (email baru)
  - Free $5 credit lagi
  - Repo sama, tinggal re-deploy
  - 5 menit setup

OPSI 2 — Pindah ke Render.com free tier
  - Saya adapt script untuk Render
  - 750 jam/bulan free (cukup 1 service 24/7)

OPSI 3 — Tetap di GitHub Actions only
  - Bot jadi signal-only (no auto-execution)
  - Anda trade manual via Jupiter link dari Telegram
  - 100% free selamanya

## COST BREAKDOWN

- SnapDeploy: $0 (free $5 credit, renewable tiap ~2 minggu via email baru)
- GitHub Actions: $0 (2000 menit/bulan free)
- Telegram: $0
- Helius RPC: $0 (free tier)
- **Total: $0/bulan**

## LIMITASI

- Modal trading tetap 0.0691 SOL (di HP wallet, SnapDeploy pakai key yang sama)
- TAPI: trade execution dari SnapDeploy, bukan HP. Modal 100% di keypair, bukan terikat server.
- DNS Jupiter masih blocked, jadi SnapDeploy pakai Pump.fun direct + Raydium raw (yang akan saya tambahkan)

## NEXT: Pump.fun Direct + Raydium Raw Executor

Setelah SnapDeploy running, saya akan tambah Raydium AMM v4 direct swap executor (untuk token yang sudah graduate dari Pump.fun). Ini melengkapi fallback Jupiter aggregator.

Saat ini sniper di SnapDeploy:
- Akan detect token dari DexScreener
- Untuk token di Pump.fun curve (belum complete): pakai pumpfun_executor.py
- Untuk token sudah graduate ke Raydium: akan ada `raydium_executor.py` (akan dibuat)
- Filter tetap konservatif (liq/vol/age/holders)

B0x70 — pilih langkah:
- "SNAPDEPLOY DONE" → saya bantu verify setelah deploy
- "GITHUB ONLY" → saya aktifkan cron-only mode, no SnapDeploy
- "TUNGGU" → saya standby, modal aman di HP
