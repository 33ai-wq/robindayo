# prpo_ai — FINAL DEPLOYMENT PLAN (Setelah Verifikasi SnapDeploy)

## REALITA SETELAH SNAPDEPLOY DOCS CHECK

❌ **SnapDeploy FREE tier = "10 deploys/day, AUTO-SLEEP"**
- Container MATI setelah idle 5-15 menit
- Untuk bot 24/7 perlu **Always-On $12/bulan** atau **Sprint Pack $1/24h**
- Sprint Pack = one-time payment, unlimited deploys dalam 24 jam, lalu container stop

✅ **GitHub Actions = FREE selamanya, 2000 menit/bulan quota**
- Workflow sudah jalan (cron 15 menit)
- 100% tanpa kartu kredit
- Trade execution MANUAL via Telegram alert → Jupiter web

---

## OPSI A — PURE GITHUB ACTIONS (RECOMMENDED untuk B0x70)

**Biaya: $0/bulan, tanpa CC**

Cara kerja:
1. Tiap 15 menit, GitHub Actions scan DexScreener untuk token meme Solana
2. Filter ketat: liq≥$15k, vol≥$25k, holders≥150, age 0.25-72h
3. Kalau ada yang qualify → kirim alert ke Telegram @1963809645
4. Alert berisi: symbol, score, link DexScreener, link Jupiter swap
5. **B0x70 BUKA LINK JUPITER → TRADE MANUAL** via web wallet

Modal 0.0691 SOL tetap di wallet HP. Trade manual lebih aman karena:
- Anda kontrol 100% (tidak ada bot auto-trade tanpa confirm)
- Tidak ada risiko bug execute trade rug modal
- Belajar pattern market dulu

Setup yang sudah selesai:
- ✓ Workflow `.github/workflows/sniper-scan.yml` sudah push ke repo
- ✓ Scan script `.github/scripts/scan_and_alert.py` ready

Yang perlu Anda lakukan:
1. Setup 2 secrets di GitHub repo (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
2. Trigger workflow manual pertama
3. Tunggu alert pertama masuk Telegram

---

## OPSI B — SNAPDEPLOY SPRINT PACK ($1/24h)

**Biaya: $1 (one-time, 24 jam Always-On)**

Cara kerja:
1. Beli Sprint Pack $1 → container Always-On selama 24 jam
2. Setup env vars di SnapDeploy (PRIVATE_KEY, RPC, dll)
3. Bot auto-trade 24/7 dalam 24 jam
4. Setelah 24 jam → container stop, modal sudah balik ke wallet
5. Beli Sprint Pack lagi kalau mau lanjut

Risk:
- Bug trade execution bisa rug modal dalam 24 jam (filter ketat mengurangi tapi tidak menghilangkan)
- DNS Jupiter masih blocked dari network (root cause sebelumnya)
- SnapDeploy region mungkin terbatas

Setup SnapDeploy:
1. SnapDeploy Dashboard → klik project → Settings → Environment Variables
2. Add env: PRIVATE_KEY_SOL_TREASURY, RPC_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, HELIUS_API_KEY
3. Dockerfile path: `Dockerfile` (sudah di root sekarang)
4. Plan: Sprint Pack $1

---

## OPSI C — TIDAK DEPLOY SAMA SEKALI (PALING AMAN)

**Biaya: $0**

Modal 0.0691 SOL sangat kecil. Realita:
- 90%+ trader dengan modal <$10 GAGAL (fee + slippage + variance)
- Belajar pattern dulu via GitHub Actions OPSI A
- Nambah modal kalau Anda yakin strateginya
- Bot sniper yang sudah running di HP (sudah saya kill sebelumnya) bisa di-restart kapan saja

---

## REKOMENDASI FINAL UNTUK B0x70

Saya rekomen **OPSI A (Pure GitHub Actions)** karena:

1. ✓ $0/bulan (modal tetap utuh)
2. ✓ Belajar pattern market tanpa risk modal
3. ✓ Trade manual = Anda kontrol penuh
4. ✓ Modal 0.0691 SOL tidak berkurang untuk fee/eksperimen
5. ✓ Workflow sudah push, tinggal setup secrets

**LANGKAH UNTUK OPSI A:**

### STEP 1: Setup GitHub Secrets (5 menit)

Buka https://github.com/33ai-wq/prpo_ai/settings/secrets/actions

Klik "New repository secret" → tambahkan:

a) Name: `TELEGRAM_BOT_TOKEN`
   Value: (bot token dari @BotFather — sama dengan yang di .env HP Anda)

b) Name: `TELEGRAM_CHAT_ID`
   Value: `1963809645`

c) Name: `SNAPDEPLOY_URL` (opsional, untuk healthcheck)
   Value: (kosongkan kalau tidak pakai SnapDeploy)

### STEP 2: Test Manual Trigger (1 menit)

1. Buka https://github.com/33ai-wq/prpo_ai/actions
2. Klik "prpo_ai Sniper Scan" di sidebar
3. Klik "Run workflow" → "Run workflow" (tombol hijau)
4. Tunggu 30-60 detik
5. Lihat log:
   - "[scan] qualified: N" — jumlah token yang pass filter
   - Kalau N > 0 → Telegram dapat alert
   - Kalau N = 0 → Telegram dapat pesan "market quiet"

### STEP 3: Verifikasi Telegram

Buka Telegram chat 1963809645.
Harusnya dapat pesan dari bot Telegram Anda (yang tokennya di-secret).

Format pesan kalau ada signal:
```
📡 prpo_ai SCAN  2026-06-19 12:34 UTC
qualified: 3

TEST
score=6.50
liq $25,000 | vol24h $80,000
age 3.2h | pc1h +25.0% | B/S 0.65
DexScreener | Jupiter
```

Format pesan kalau tidak ada signal:
```
📡 prpo_ai SCAN  2026-06-19 12:34 UTC
qualified: 0
market quiet — no fresh setups
```

### STEP 4: Cron Otomatis

Sudah built-in: `cron: '*/15 * * * *'`
Workflow auto-trigger tiap 15 menit (24/7).
Quota GitHub: 2000 menit/bulan, pakai ~150 menit/bulan = 7.5% quota.

---

## TROUBLESHOOTING

**Q: Workflow run gagal "Bad credentials"**
A: Cek secret TELEGRAM_BOT_TOKEN. Value harus format `123456789:ABC-DEF...` (full token).

**Q: Workflow OK tapi Telegram tidak dapat alert**
A: 
1. Cek TELEGRAM_CHAT_ID = `1963809645` (numeric, no quotes, no space)
2. Cek bot Telegram sudah start oleh Anda (kirim `/start` ke bot di Telegram)
3. Cek apakah token masih aktif (cek @BotFather → /mybots)

**Q: Scan selalu qualified: 0**
A: Market Solana lagi sepi. Normal. Tunggu launch baru.

**Q: Ingin SnapDeploy tapi $1/24h terlalu mahal**
A: Opsi A recommended. Signal-only + manual trade sudah cukup untuk belajar.

**Q: Modal tidak cukup untuk trade manual**
A: Modal 0.0691 SOL = ~$4.90. Cukup untuk 1-2 trade kecil (0.005-0.01 SOL/trade).
Profit potential kecil, tapi RISK modal juga kecil. Cocok untuk belajar.

---

## NEXT STEPS SETELAH OPSI A JALAN

1. Monitor 1 minggu, lihat pattern signal
2. Kalau ada token qualify dan Anda berhasil trade manual profit
   → saya bisa tambah Raydium AMM v4 direct executor (untuk token
     yang sudah graduate dari Pump.fun)
3. Kalau konsisten profit → tambah modal (top up 0.05-0.10 SOL)
   → enable auto-trade mode via Sprint Pack $1

---

B0x70 — saya jujur: deploy bot auto-trade dengan modal sekecil ini
adalah RISKY. Signal-only + manual trade adalah cara TERAMAN
untuk belajar tanpa rug modal.

Modal 0.0691 SOL = $4.90. Jangan sampai habis untuk eksperimen.
Pelajari pattern dulu via GitHub Actions alert. Kalau profit konsisten,
baru scale up.
