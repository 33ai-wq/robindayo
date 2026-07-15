# RobinDayo

> Visitors welcome.

An open digital living room on Robinhood Chain. Catalog of paid x402 endpoints, a free field-guide PDF for offline reading, and a live house treasury — every number honest, every action opt-in.

## URL

Live at: `https://33ai-wq.github.io/robindayo/`

## What's here (v3)

- **`/`** — the catalog itself: Robinhood Chain treasury (live via Blockscout), four paid x402 endpoints, two Lightning rails, the "how a visit works" 4-step strip, six-fragment philosophy grid.
- **`visitors-companion.pdf`** — an 8-page free field guide. Click the **Download the PDF** button on the page; no email, no signup. SHA-256 of the canonical copy is pinned below; we re-publish this PDF whenever the guide changes.
- **@mycera cross-link** — the operator writes longer-form essays at `paragraph.com/@mycera`. The page canonical-byline makes that cross-link visible to readers who came for the API endpoints and want to read the operator's writing too.

## Endpoints available

| Endpoint | Method | x402 (USDC) | L402 (sats) |
|---|---|---|---|
| [`/v1/meme-hunter`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/meme-hunter) | GET | $0.001 | 25 |
| [`/v1/defi-sentiment`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/defi-sentiment) | GET | $0.005 | 25 |
| [`/v1/dinalibrium`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/dinalibrium) | POST | $0.005 | 50 |
| [`/v1/wallet-profile`](https://x402-cf-worker.mulberry-boar.workers.dev/v1/wallet-profile) | GET | $0.010 | 100 |

## Visitor's Companion (PDF)

```
file:    visitors-companion.pdf
sha256:  d6ce22db52c54250bd7ec1c092833b646206a2492c119f8f47b45ab90f0cb0b1
size:    19,095 bytes
pages:   8
format:  A4 (595.28 × 841.89 pts)
author:  prpo_ai · B0x70
created: 2026-07-14
```

Re-verify locally:

```bash
shasum -a 256 visitors-companion.pdf
# → expect: d6ce22db52c54250bd7ec1c092833b646206a2492c119f8f47b45ab90f0cb0b1
```

PDF chapters: what a visitor pays for · two rails, one question · reading a 402 envelope · Lightning lanes · honourable pricing · what the operator owes a guest · short glossary · where this room came from.

> A paid hard-copy edition is live on Gumroad — [prpoai.gumroad.com/l/robindayo](https://prpoai.gumroad.com/l/robindayo) — $9.99, "Visitor's Companion pocketbook ed.". The free PDF stays free; the pocketbook exists for readers who want a printed, signed copy.

## Treasury

```
address:    0x99Cc2cA01841ca704C834415b5909bE591f36d27
chain:      Robinhood Chain · mainnet · chain id 4663
explorer:   https://robinhoodchain.blockscout.com/address/0x99Cc2cA01841ca704C834415b5909bE591f36d27
```

The balance on the page is read live on every load via the canonical Blockscout endpoint. Robinhood's own public RPC (`rpc.mainnet.chain.robinhood.com`) refuses anonymous browser calls with HTTP 403; the explorer endpoint proxies the same JSON-RPC query on behalf of authenticated RPC partners, so the number the page shows is the same number an authenticated operator would see.

If the explorer is unreachable from the visitor's network, the card falls back to "unavailable" rather than fabricate a balance.

## Files in this repo

```
index.html        — the page body + payment-rail script + treasury block
styles.css        — palette + cards + the new guide-card block
logo.svg          — wordmark
favicon.svg       — monogram favicon
visitors-companion.pdf  — the free field guide
downloads/        — staging area; canonical copy lives at repo root
```

## Hosting

GitHub Pages from `main` / root. Standard JSDelivr+++ pages build, no custom domain, no analytics, no consent banner — by design.
