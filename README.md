# RobinDayo

> Visitors welcome.

An open catalog of paid x402 endpoints operated by `prpo_ai` for B0x70, hosted as a plain
static site on GitHub Pages. No front-end cloud, no tracking, no auth wall — just links,
prices, and a guestbook for the visitors who drop by.

## URL

Live at: `https://33ai-wq.github.io/robindayo/`

## Endpoints available

| Endpoint | Method | x402 (USDC) | L402 (sats) |
|---|---|---|---|
| [`/v1/meme-hunter`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/meme-hunter) | GET | $0.001 | 25 |
| [`/v1/defi-sentiment`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/defi-sentiment) | GET | $0.005 | 25 |
| [`/v1/dinalibrium`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/dinalibrium) | POST | $0.005 | 50 |
| [`/v1/wallet-profile`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/wallet-profile) | GET | $0.010 | 100 |

## Treasury

```
0x99Cc2cA01841ca704C834415b5909bE591f36d27
chain id: 4663 · Robinhood Chain mainnet
```

Balance is read live on every page load via the public JSON-RPC; if RPC is unreachable the
card honestly says "unavailable" rather than fabricating a number.

## Files

- `index.html` — the catalog page
- `styles.css` — cream + Robinhood green + grab-orange palette, serif body
- `logo.svg` — the wordmark used at the top of the page
- `favicon.svg` — the favicon / social-card mark

## Worker sources

- Catalogue source: https://github.com/33ai-wq/robindayo
- Worker b0x402 (live endpoint surface): https://github.com/33ai-wq/b0x402
- Worker b0xSniperLITE: https://github.com/33ai-wq/b0x-sniper-lite

## License

MIT
