# FIX: GitHub PAT "workflow" scope

MASALAH:
  GitHub menolak push file `.github/workflows/*.yml` jika PAT tidak
  punya scope `workflow`. Ini security feature GitHub.

SOLUSI: Buat PAT baru dengan scope `workflow` ditambahkan.

## LANGKAH:

### 1. Buka halaman PAT baru
https://github.com/settings/tokens/new

### 2. Isi form:
- Note: `prpo_ai VPS push 2026 v2`
- Expiration: 90 days (atau sesuai kebutuhan)
- **Owner**: selected repo only → pilih `33ai-wq/prpo_ai`
  (kalau repo selection disabled, biarkan "All repositories")

### 3. SCOPES — CENTANG INI:
```
✓ repo              (full control of private repositories)
✓ workflow          (✓ INI YANG KURANG — update GitHub Actions workflows)
```

### 4. Generate token
Klik "Generate token" di bawah
COPY token (format: ghp_xxxxxxxxxxxxxxx)

### 5. PUSH dari Termux HP

```bash
cd /root/prpo_ai

# Simpan token baru ke .env
echo "GITHUB_TOKEN=***  >> /root/.hermes/profiles/prpo_ai/.env
chmod 600 /root/.hermes/profiles/prpo_ai/.env

# Clear git credential lama (yang salah-scope)
# CARA 1 — unstore semua
git config --global --unset credential.helper
# Lalu push akan prompt ulang

# CARA 2 — pakai URL embed (langsung dengan token baru)
git push https://ghp_NEW_TOKEN@github.com/33ai-wq/prpo_ai.git master
```

Ganti `ghp_NEW_TOKEN` dengan token baru yang baru di-copy.

### 6. Verifikasi
Setelah push sukses, buka:
https://github.com/33ai-wq/prpo_ai/actions

Tab "All workflows" harus menampilkan `prpo_ai Sniper Scan`.

## KENAPA TIDAK BISA AMAN LAIN?

Alternatif lain:
- **GitHub App** dengan `workflows: write` permission — terlalu berat untuk setup
- **Fine-grained PAT** (newer): tidak support workflow scope (hanya classic PAT)
- **SSH key** dengan write access — harus di-config manual + deploy key, lebih ribet

**Classic PAT + workflow scope** adalah cara paling straightforward.

## KALAU MASIH GAGAL

Cek:
1. Token benar-benar baru (bukan token lama yang di-copy)
2. Scope `workflow` benar-benar tercentang (scroll ke bawah di halaman scope)
3. Expiration tidak expired
4. Repo owner benar: 33ai-wq (bukan b0x70 atau username lain)

Pesan error spesifik:
- `Bad credentials` → token salah/revoked
- `Not Found` → token tidak punya akses ke repo
- `refusing to allow a Personal Access Token to create or update workflow` → scope workflow kurang (INI KASUS ANDA SEKARANG)
- `Repository not found` → nama repo salah
