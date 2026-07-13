# RobinDayo

> Ruang tamu digital di jaringan Robinhood Chain.

Etalase endpoint-endpoint x402 (USDC di Base) yang dijalankan oleh `prpo_ai` untuk B0x70.
Halaman ini cuma HTML — tanpa front-end, tanpa Cloudflare, tanpa tracking. Tinggal klik dan bayar.

## URL

Setelah GitHub Pages aktif: `https://33ai-wq.github.io/robindayo/`

## Endpoint yang dijual

| Endpoint | Method | Harga x402 (USDC) | Mirror L402 |
|---|---|---|---|
| [`/v1/meme-hunter`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/meme-hunter) | GET | $0.001 | 25 sats |
| [`/v1/defi-sentiment`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/defi-sentiment) | GET | $0.005 | 25 sats |
| [`/v1/dinalibrium`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/dinalibrium) | POST | $0.005 | 50 sats |
| [`/v1/wallet-profile`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/wallet-profile) | GET | $0.010 | 100 sats |

## Treasury

```
0x99Cc2cA01841ca704C834415b5909bE591f36d27
chain id: 4663 (Robinhood Chain mainnet)
```

Saldo dibaca langsung dari RPC publik saat halaman dimuat.

## Filosofi

"Tamu" — dalam bahasa Jawa *dayo* — посещающий harus dihormati. Di sini rasa hormat itu
diwujudkan lewat transaksi on-chain yang ringan dan transparan, bukan popup marketing.

## Repo worker

- Etalase ini: https://github.com/33ai-wq/robindayo
- Worker b0x402 (sumber endpoint): https://github.com/33ai-wq/b0x402 (mirror)
- Worker b0xSniperLITE: https://github.com/33ai-wq/b0x-sniper-lite

## Lisensi

MIT
