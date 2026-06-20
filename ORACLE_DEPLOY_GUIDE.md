# prpo_ai — Oracle Cloud Free Tier Deployment Guide

Target: Deploy sniper bot + Meridian agent di VPS gratis 24/7,
bebaskan HP B0x70 dari beban baterai.

Total waktu: ~90 menit (mostly signup + provisioning, deployment script ~15 min).

## Kenapa Oracle Cloud Always Free?

- ALWAYS FREE (no credit card required untuk Always Free tier)
- ARM Ampere A1: sampai 4 OCPU + 24 GB RAM (cukup untuk sniper + meridian)
- Region Singapore/Tokyo tersedia (latency Asia bagus)
- Uptime dijamin SLA 99.95%
- Bisa install Ubuntu 22.04 / Oracle Linux 8/9
- Backup snapshot gratis

## STEP 1: Signup Oracle Cloud (15 menit)

1. Buka https://cloud.oracle.com/
2. Klik "Start for Free"
3. Isi email + password (BISA pakai email prpoai495@gmail.com yang sudah ada)
4. Pilih Home Region: **Singapore** atau **Tokyo** (paling dekat ke validator Solana Asia)
   - CATATAN: region TIDAK BISA DIUBAH setelah signup. Pilih yang strategis.
5. Verifikasi email + phone
6. Tunggu provisioning akun (5-15 menit, dapat email konfirmasi)
7. Login ke https://cloud.oracle.com/console/ dengan email Anda

## STEP 2: Provision ARM VM (10 menit)

1. Di Console, klik hamburger menu (top-left) > Compute > Instances > Create Instance
2. **Name**: prpo-ai-vm (atau nama apa saja)
3. **Placement**: 
   - Availability domain: biarkan default
   - Image: Ubuntu 22.04 (atau Oracle Linux 9 ARM)
4. **Shape**: klik "Edit" > Ampere > VM.Standard.A1.Flex (Always Free)
   - OCPU: 1 (bisa naik sampai 4 gratis)
   - RAM: 6 GB (bisa sampai 24 GB gratis)
   - Total Always Free quota: 4 OCPU + 24 GB RAM (jika pakai 1 instance, set 4/24)
5. **Networking**: 
   - Pilih VCN default atau create new
   - Subnet: default
   - Public IPv4: ASSIGN
6. **SSH Keys**: 
   - Generate key pair (recommended: pakai yang sudah ada di Termux)
   - Atau klik "Save Private Key" untuk download .key file
   - ATAU paste PUBLIC key dari laptop/HP Anda
7. Klik **Create** — provisioning 2-3 menit
8. Catat PUBLIC IP ADDRESS (mis. 158.101.45.23)

## STEP 3: SSH ke VPS (5 menit)

Dari Termux HP B0x70:

```bash
# Set permission untuk key yang didownload
chmod 600 ~/Downloads/oracle-key.key

# SSH (ganti IP dengan IP VPS Anda)
ssh -i ~/Downloads/oracle-key.key ubuntu@158.101.45.23
```

Atau kalau pakai username `ubuntu` dengan key default:
```bash
ssh ubuntu@158.101.45.23
```

Anda akan masuk ke Ubuntu prompt. Lanjut ke STEP 4.

## STEP 4: Run Deployment Script (15-20 menit, mostly automated)

Di VPS (setelah SSH masuk):

```bash
# 1. Switch ke root
sudo su -

# 2. Setup script (Anda copy script dari HP, atau langsung download dari repo)
# Opsi A: clone repo dulu, baru run script
git clone https://github.com/33ai-wq/prpo_ai.git /root/prpo_ai
cd /root/prpo_ai

# Opsi B: jika script sudah ada di repo
bash deploy_oracle.sh

# Script akan otomatis:
#   - Update sistem
#   - Install python3, nodejs, npm, pm2
#   - Setup venv untuk sniper
#   - Konfigurasi .env (akan prompt)
#   - Setup firewall + fail2ban
#   - Hardening SSH (disable password)
#   - Verify via Telegram
```

Saat prompt untuk isi GitHub PAT dan keys, paste:
- GITHUB_TOKEN: dari https://github.com/settings/tokens/new (scope: repo)
- PRIVATE_KEY_SOL_TREASURY: base58 SOL wallet Anda
- HELIUS_API_KEY: dari https://helius.dev
- TELEGRAM_BOT_TOKEN: sudah ada (sama dengan HP)

## STEP 5: Sync Sniper Code dari HP ke VPS (5 menit)

Di HP (Termux):

```bash
# Sync sniper folder ke VPS via rsync over SSH
rsync -avz -e "ssh -i ~/Downloads/oracle-key.key" \
  /root/prpo_ai/sniper/ \
  ubuntu@158.101.45.23:/root/prpo_ai/sniper/

# Sync meridian folder
rsync -avz -e "ssh -i ~/Downloads/oracle-key.key" \
  /root/.hermes/profiles/prpo_ai/meridian_copy/ \
  ubuntu@158.101.45.23:/root/.hermes/profiles/prpo_ai/meridian_copy/
```

Atau pakai SCP (lebih simple):
```bash
scp -i ~/Downloads/oracle-key.key -r /root/prpo_ai/sniper ubuntu@158.101.45.23:/root/prpo_ai/
scp -i ~/Downloads/oracle-key.key -r /root/.hermes/profiles/prpo_ai/meridian_copy ubuntu@158.101.45.23:/root/.hermes/profiles/prpo_ai/
```

## STEP 6: Start Services (5 menit)

Di VPS:

```bash
# Install deps untuk meridian
cd /root/.hermes/profiles/prpo_ai/meridian_copy
npm install --production

# Sync sniper code, lalu:
cd /root/prpo_ai
pm2 start ecosystem.config.cjs
pm2 save
pm2 startup systemd    # IMPORTANT: copy-paste output command (sudo env PATH=...)

# Verify
pm2 list
pm2 logs --lines 50
```

## STEP 7: Verify di Telegram

Anda akan menerima pesan Telegram:
```
🟢 prpo_ai — ORACLE CLOUD DEPLOYED
host: prpo-ai-vm
arch: aarch64
sniper + meridian ready
standby for first cycle...
```

Lalu tiap jam ada hourly report. Saat ada trade, dapat BUY/CLOSE alert.

## STEP 8: Setup Backup Cron (5 menit)

Tambahkan cron job untuk sync state files ke GitHub setiap 6 jam:

```bash
crontab -e
# Add line:
0 */6 * * * cd /root/prpo_ai && git add sniper/logs sniper/state && git commit -m "vps state $(date)" && git push
```

## OPSIONAL: Domain Custom (Biar VPS punya hostname)

1. Beli domain murah di Namecheap/Cloudflare (~$5-10/tahun)
2. Set A record ke IP VPS
3. Setup reverse DNS di Oracle Console

## MAINTENANCE

Setiap minggu (1-2 menit dari HP):

```bash
ssh ubuntu@<vps-ip>
pm2 logs --lines 50
pm2 list
```

## TROUBLESHOOTING

- **VPS tidak bisa SSH**: cek Oracle Console > Instance > "Stop" lalu "Start" (reboot)
- **Service down**: `pm2 restart all`
- **Bot lupa key**: edit `/root/.hermes/profiles/prpo_ai/.env` lalu `pm2 restart all`
- **Full disk**: `df -h`, hapus logs lama
- **Always Free reclaimed**: jika idle >7 hari, Oracle bisa hapus instance. Setup daily cron (daily_farmer.py atau signal scan) supaya selalu ada traffic.

## BIAYA

- VPS: $0/bulan
- Domain: $0-10/tahun (opsional)
- Helius RPC: $0 (free tier)
- Telegram: $0
- **Total: $0/bulan**

## NEXT LEVEL (kalau perlu performa lebih)

- Upgrade ke Hetzner CX22 €4/bulan: 2 vCPU + 4GB RAM + 40GB NVMe (Lokasi: Germany/Finland/US)
- Lebih reliable untuk latency-sensitive sniper
