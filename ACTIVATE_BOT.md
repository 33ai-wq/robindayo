# prpo_ai — Aktifkan Sniper Bot (Step by Step)

Push workflow SUDAH SUKSES. Sekarang aktifkan bot sniper.

## STEP 1: Setup GitHub Secrets (WAJIB, 5 menit)

Sniper workflow butuh secrets untuk kirim alert ke Telegram.

1. Buka: https://github.com/33ai-wq/prpo_ai/settings/secrets/actions
2. Klik "New repository secret"
3. Tambahkan 2 secrets:

   a) Name: TELEGRAM_BOT_TOKEN
      Value: (paste bot token Telegram Anda, format: 123456:ABC-DEF...)

   b) Name: TELEGRAM_CHAT_ID
      Value: 1963809645

4. Klik "Add secret" untuk masing-masing

## STEP 2: Trigger Workflow Manual (test, 2 menit)

1. Buka: https://github.com/33ai-wq/prpo_ai/actions
2. Klik workflow "prpo_ai Sniper Scan" di sidebar kiri
3. Klik "Run workflow" → "Run workflow" (dropdown kanan)
4. Tunggu 30-60 detik sampai selesai
5. Klik run yang baru selesai → lihat log
6. Kalau ada "[scan] telegram ok" — success!
7. Cek Telegram chat 1963809645, harusnya dapat pesan alert

## STEP 3: Aktifkan Cron Otomatis (sudah built-in, no action needed)

Workflow sudah ada baris:
```
on:
  schedule:
    - cron: '*/15 * * * *'
```

Artinya otomatis trigger TIAP 15 MENIT (24/7). Tidak perlu enable manual.

## STEP 4: Setup SnapDeploy untuk Full Execution (10 menit, OPSIONAL)

Workflow GitHub Actions hanya SIGNAL SCAN (kirim alert, no trade).
Untuk AUTO-TRADE, setup SnapDeploy:

1. Buka https://snapdeploy.dev
2. Sign up via GitHub (33ai-wq)
3. New Project → Docker
4. Pilih repo `33ai-wq/prpo_ai`
5. Path Dockerfile: `sniper/Dockerfile`
6. Environment variables:
   - PRIVATE_KEY_SOL_TREASURY = (base58 SOL wallet keypair)
   - RPC_URL = https://mainnet.helius-rpc.com/?api-key=XXX
   - TELEGRAM_BOT_TOKEN = (sama)
   - TELEGRAM_CHAT_ID = 1963809645
   - HELIUS_API_KEY = (Helius key)
7. Plan: Free $5 credit tier
8. Deploy

SnapDeploy akan jalan 24/7 sampai credit habis (~2 minggu).

## OPSI TANPA SNAPDEPLOY

Kalau Anda tidak mau setup SnapDeploy dulu, mode signal-only via GitHub Actions sudah cukup:
- Tiap 15 menit scan DexScreener
- Kirim alert ke Telegram kalau ada token qualify
- Anda buka link Jupiter → trade manual

## VERIFICATION

Setelah setup, monitor:
1. Telegram chat 1963809645:
   - Tiap 15 menit: alert scan (qualified: 0 atau list token)
   - Tiap 1 jam: hourly report (kalau SnapDeploy aktif)

2. GitHub Actions:
   - https://github.com/33ai-wq/prpo_ai/actions
   - Tab "All workflows" → lihat run history

3. SnapDeploy dashboard (kalau aktif):
   - Logs real-time
   - Credit usage

## TROUBLESHOOTING

Q: Workflow run gagal "Bad credentials"
A: Cek secrets TELEGRAM_BOT_TOKEN. Pastikan value adalah token valid,
   bukan username atau nama lain.

Q: Workflow run OK tapi Telegram tidak dapat alert
A: Cek TELEGRAM_CHAT_ID = 1963809645 (numeric, no quotes).

Q: SnapDeploy build gagal
A: Cek Dockerfile path: sniper/Dockerfile (case-sensitive).
   Cek requirements.txt ada di folder sniper/.

Q: Modal 0.069 SOL tidak cukup untuk SnapDeploy trade
A: Trade size di config: SNIPER_MAX_PER_TRADE_SOL=0.015 default.
   Modal 0.069 > 0.015, cukup untuk 4 trade cycle.
   TAPI: trade butuh fee ~0.0001 SOL + rent ~0.002 SOL per ATA.
   Modal 0.069 SOL efektif untuk ~3-4 trade cycle saja.

## ESTIMASI WAKTU

Step 1 (GitHub secrets): 5 menit
Step 2 (trigger manual test): 2 menit
Step 3 (cron auto): 0 menit (sudah built-in)
Step 4 (SnapDeploy opsional): 10 menit

Total minimum: 7 menit untuk aktifkan signal-only bot.

## BIAYA

- GitHub Actions: $0/bulan
- SnapDeploy: $0 (free $5 credit, ~2 minggu)
- Telegram: $0
- **Total: $0/bulan**

B0x70 — setelah Step 1+2 selesai, Anda akan mulai dapat alert Telegram
tiap 15 menit. Itu indikator paling jelas bahwa bot sudah jalan.
