/**
 * b0xlight-bridge — L402 standalone endpoint (paid in Lightning sats)
 *
 * Arsitektur final (2026-07-12):
 *   Single-source worker. Tidak ada upstream dependency ke x402 b0x402 —
 *   semua endpoint logic tertanam di sini. Hasilnya:
 *     • Zero double-payment (customer bayar sats → kita emit data, tidak ada USDC layer)
 *     • 100% margin untuk operator (B0x70)
 *     • Instant Lightning settlement via LightningFaucet
 *     • Compatible dengan `lw pay-api` CLI (L402 standard subset)
 *
 * Pricing (per-call, sats):
 *   /v1/meme-hunter     25 sats    (real — fetches DexScreener)
 *   /v1/defi-sentiment  25 sats    (stub — identical to b0x402)
 *   /v1/dinalibrium     50 sats    (stub — identical to b0x402)
 *   /v1/wallet-profile  100 sats   (stub — identical to b0x402)
 *
 * L402 Flow (matches LightningFaucet / Lightning Labs spec subset):
 *   1. Hit endpoint tanpa preimage → 402 + Lightning invoice + payment_hash
 *   2. Customer pays invoice via Lightning wallet
 *   3. Customer retries with header:
 *        Authorization: L402 <macaroon>:<preimage_hex>
 *        X-Payment-Hash: <payment_hash_from_step_1>
 *   4. Bridge verifies preimage by SHA256(preimage) === payment_hash
 *      AND queries LightningFaucet check_invoice → status === "settled"
 *   5. If both true → fetch data, return 200.
 *
 * Catatan:
 *   • macaroon field saat ini accept-any (LightningFaucet tidak issue macaroon per-invoice —
 *     preimage+payment_hash cukup sebagai proof of payment)
 *   • Rate-limit: tidak ada di v0.1 — bridge ada di belakang CF edge yg sudah rate-limit DDoS
 */

const LF = "https://lightningfaucet.com/ai-agents/api";

// ─── L402 Header Parser ─────────────────────────────────────────────────────

/**
 * Parse "Authorization: L402 <macaroon>:<preimage>" header.
 * Returns null if header missing/malformed.
 */
function parseL402(header) {
  if (!header) return null;
  if (!header.startsWith("L402 ")) return null;
  const tok = header.slice(5).trim();
  if (!tok) return null;

  // Could be just "L402 <preimage>" (wallet-style) or "L402 <macaroon>:<preimage>" (LSAT-style)
  // Detect by looking for ":" — if exactly 1 sep, treat first as macaroon
  const parts = tok.split(":");
  let macaroon = "";
  let preimage = "";
  if (parts.length === 1) {
    preimage = parts[0];
  } else if (parts.length === 2) {
    macaroon = parts[0];
    preimage = parts[1];
  } else {
    // macaroon itself may contain colons (base64) — preimage is last 64 hex chars
    const last = parts[parts.length - 1];
    if (/^[0-9a-fA-F]{64}$/.test(last)) {
      preimage = last;
      macaroon = parts.slice(0, -1).join(":");
    } else {
      return null;
    }
  }
  if (!/^[0-9a-fA-F]{64}$/.test(preimage)) return null;
  return { macaroon, preimage };
}

// ─── LightningFaucet API Wrappers ───────────────────────────────────────────

async function lfCreateInvoice(agentKey, amountSats, memo, metadata = {}) {
  const res = await fetch(LF, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${agentKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      action: "create_invoice",
      amount_sats: amountSats,
      memo,
      ...metadata,
    }),
  });
  if (!res.ok) {
    throw new Error(`LF create_invoice failed: HTTP ${res.status}`);
  }
  const data = await res.json();
  if (!data.success) {
    throw new Error(`LF create_invoice error: ${data.error || "unknown"}`);
  }
  return data;
}

async function lfCheckInvoice(agentKey, paymentHash) {
  const res = await fetch(LF, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${agentKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      action: "check_invoice",
      payment_hash: paymentHash,
    }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  if (!data.success) return null;
  return data; // { success, status: 'pending'|'settled'|'expired', amount_sats, ... }
}

// ─── SHA256(preimage) === payment_hash verification ────────────────────────

async function preimageMatchesHash(preimageHex, paymentHashHex) {
  if (!/^[0-9a-fA-F]{64}$/.test(preimageHex) || !/^[0-9a-fA-F]{64}$/.test(paymentHashHex)) {
    return false;
  }
  const preimageBytes = hexToBytes(preimageHex);
  const hashBuffer = await crypto.subtle.digest("SHA-256", preimageBytes);
  const computed = bytesToHex(new Uint8Array(hashBuffer));
  return computed.toLowerCase() === paymentHashHex.toLowerCase();
}

function hexToBytes(hex) {
  const out = new Uint8Array(hex.length / 2);
  for (let i = 0; i < out.length; i++) {
    out[i] = parseInt(hex.slice(i * 2, i * 2 + 2), 16);
  }
  return out;
}

function bytesToHex(bytes) {
  return Array.from(bytes).map(b => b.toString(16).padStart(2, "0")).join("");
}

// ─── L402 Challenge Builder ────────────────────────────────────────────────

function l402ChallengeBody(invoice, amountSats, paymentHash) {
  return {
    error: "payment_required",
    protocol: "L402",
    www_authenticate: `L402 macaroon="", invoice="${invoice}"`,
    payment_required: {
      lightning_invoice: invoice,
      payment_hash: paymentHash,
      amount_sats: amountSats,
      network: "lightning/mainnet",
      protocol: "L402",
      settle_method: "Pay invoice from any Lightning wallet, then retry with header: Authorization: L402 <macar>:<preimage_hex>  AND X-Payment-Hash: " + paymentHash,
    },
    usage: "Pay the lightning_invoice above. Then retry this request with two headers: Authorization: L402 <any>:<preimage_hex>  AND X-Payment-Hash: <same payment_hash>. The `<>` placeholders must be replaced with the actual values from your wallet.",
  };
}

// ─── Endpoint Logic (mirrors b0x402 /v1/* 1:1) ──────────────────────────────

async function memeHunter(limit = 10, sortBy = "score") {
  try {
    const resp = await fetch(
      "https://api.dexscreener.com/latest/dex/search?q=base&limit=100",
      { cf: { cacheTtl: 60, cacheEverything: true } }
    );
    const data = await resp.json();
    const pairs = (data.pairs || []).filter(p => p?.chainId === "base");

    const signals = pairs.map(p => {
      try {
        const base = p.baseToken || {};
        const priceUsd = parseFloat(p.priceUsd || 0);
        const change = parseFloat(p.priceChange?.h24 || 0);
        const volume = parseFloat(p.volume?.h24 || 0);
        const liquidity = parseFloat(p.liquidity?.usd || 0);
        const score = Math.min(100, Math.abs(change) * 0.5 + liquidity / 1000 + volume / 500);
        return {
          token_address: base.address || "",
          name: base.name || "Unknown",
          symbol: base.symbol || "??",
          price_usd: parseFloat(priceUsd.toFixed(priceUsd < 0.001 ? 8 : 4)),
          change_24h_pct: parseFloat(change.toFixed(2)),
          volume_24h: parseFloat(volume.toFixed(2)),
          liquidity_usd: parseFloat(liquidity.toFixed(2)),
          mint_status: liquidity > 0 ? "open" : "unknown",
          boosted: !!p.boosted,
          score: parseFloat(score.toFixed(1)),
          link: `https://dexscreener.com/base/${base.address || ""}`,
        };
      } catch (_) { return null; }
    }).filter(Boolean);

    const sortFns = {
      volume: s => s.volume_24h,
      change: s => Math.abs(s.change_24h_pct),
      liquidity: s => s.liquidity_usd,
      score: s => s.score,
      boosted: s => s.boosted ? 1 : 0,
    };
    const fn = sortFns[sortBy] || sortFns.score;
    signals.sort((a, b) => fn(b) - fn(a));
    return { count: signals.length, signals: signals.slice(0, limit) };
  } catch (e) {
    return { count: 0, signals: [], error: String(e) };
  }
}

function defiSentiment() {
  // Mirror b0x402 stub (line 637)
  return { signal: "neutral", timestamp: new Date().toISOString() };
}

function dinalibrium() {
  // Mirror b0x402 stub (line 644)
  return {
    eth_stablecoin_ratio: 0.87,
    stablecoin_supply_change_pct_7d: 2.3,
    timestamp: new Date().toISOString(),
  };
}

function walletProfile(address) {
  // Mirror b0x402 stub (line 655)
  return {
    address: address || "not_provided",
    net_worth_usd: 0,
    tx_count: 0,
    timestamp: new Date().toISOString(),
  };
}

// ─── Route Table ───────────────────────────────────────────────────────────

const ROUTES = {
  "/v1/meme-hunter": {
    sats: 25,
    method: "GET",
    handler: async (req, params, body) => {
      const limit = Math.min(50, Math.max(1, parseInt(params.get("limit") || "10", 10) || 10));
      const sortBy = params.get("sort_by") || "score";
      const data = await memeHunter(limit, sortBy);
      data.fetched_at = new Date().toISOString();
      return data;
    },
  },
  "/v1/defi-sentiment": {
    sats: 25,
    method: "GET",
    handler: async () => defiSentiment(),
  },
  "/v1/dinalibrium": {
    sats: 50,
    method: "POST",
    handler: async (req, params, body) => {
      // Accept both POST and GET (b0x402 is POST but be lenient)
      return dinalibrium();
    },
  },
  "/v1/wallet-profile": {
    sats: 100,
    method: "GET",
    handler: async (req, params, body) => {
      return walletProfile(params.get("address"));
    },
  },
};

// ─── Main Router ───────────────────────────────────────────────────────────

async function handle(request, agentKey) {
  const url = new URL(request.url);
  const pth = url.pathname;
  const customerMethod = request.method.toUpperCase();

  // Discovery document (LightningFaucet registry crawlers hit this)
  if (pth === "/.well-known/l402") {
    return new Response(JSON.stringify({
      protocol: "L402",
      version: "1.0",
      agent_id: "b0xlight-664",
      operator_id: "548",
      invoice_provider: "lightningfaucet.com",
      endpoints: Object.entries(ROUTES).map(([k, v]) => ({
        path: k,
        method: v.method,
        amount_sats: v.sats,
        description: `Paid via Lightning L402 — ${v.sats} sats per call`,
      })),
    }, null, 2), { headers: { "Content-Type": "application/json" } });
  }

  // Root & catalog
  if (pth === "/" || pth === "/catalog" || pth === "/info") {
    return new Response(JSON.stringify({
      service: "b0xlight-bridge",
      description: "L402 standalone endpoints for AI agents. Pay per request in Lightning sats. No API keys, no subscriptions.",
      endpoints: Object.fromEntries(
        Object.entries(ROUTES).map(([k, v]) => [k, { sats: v.sats, method: v.method }])
      ),
      payment_protocol: "L402 (Lightning HTTP 402)",
      settle_method: "LightningFaucet agent wallet (operator_id=548, agent_id=664)",
      note: "Hit any sub-route without L402 payment header to receive a Lightning invoice, then retry with preimage.",
      contact: "yusliarifn78@gmail.com",
    }, null, 2), { headers: { "Content-Type": "application/json" } });
  }

  const route = ROUTES[pth];
  if (!route) {
    return new Response(JSON.stringify({
      error: "not_found",
      hint: "Try /, /.well-known/l402, or one of " + Object.keys(ROUTES).join(", "),
    }), { status: 404, headers: { "Content-Type": "application/json" } });
  }

  // Method check (lenient — POST endpoints accept GET too)
  if (route.method === "POST" && customerMethod !== "POST") {
    // allow but ignore body
  } else if (route.method === "GET" && customerMethod !== "GET" && customerMethod !== "HEAD") {
    return new Response(JSON.stringify({
      error: "method_not_allowed",
      hint: `This endpoint expects ${route.method}, got ${customerMethod}`,
    }), { status: 405, headers: { "Content-Type": "application/json" } });
  }

  // ── Check L402 payment header ────────────────────────────────────────────
  const authz = request.headers.get("Authorization") || request.headers.get("authorization");
  const parsed = parseL402(authz);
  const providedHash = request.headers.get("X-Payment-Hash") || request.headers.get("x-payment-hash") || "";

  if (parsed && providedHash) {
    // Verify SHA256(preimage) === payment_hash
    const hashMatches = await preimageMatchesHash(parsed.preimage, providedHash);

    if (hashMatches) {
      // Verify LightningFaucet recorded the settlement
      const invoice = await lfCheckInvoice(agentKey, providedHash);
      if (invoice && invoice.status === "settled") {
        // Optional: amount sanity check (capped at 10x route price to allow overpayment)
        const paid = invoice.amount_sats || 0;
        if (paid < route.sats) {
          // Insufficient payment — fall through to 402 with new invoice
        } else {
          // Paid! Execute handler
          try {
            const customerBody = customerMethod === "POST" ? await request.clone().text().catch(() => "") : "";
            const data = await route.handler(request, url.searchParams, customerBody);
            return new Response(JSON.stringify(data, null, 2), {
              status: 200,
              headers: {
                "Content-Type": "application/json",
                "X-Bridge-Status": "paid-via-l402",
                "X-Payment-Hash": providedHash,
                "X-Sats-Paid": String(paid),
              },
            });
          } catch (e) {
            return new Response(JSON.stringify({ error: "handler_failed", message: String(e) }), {
              status: 500,
              headers: { "Content-Type": "application/json" },
            });
          }
        }
      }
    }
  }

  // ── Issue new 402 invoice ────────────────────────────────────────────────
  const memo = `b0xlight: ${pth} (1 call)`;
  let inv;
  try {
    inv = await lfCreateInvoice(agentKey, route.sats, memo, {
      metadata_json: JSON.stringify({ route: pth, agent_id: 664, operator_id: 548 }),
    });
  } catch (e) {
    return new Response(JSON.stringify({
      error: "bridge_offline",
      message: String(e),
      hint: "LightningFaucet invoice creation failed — kont@yusliarifn78@gmail.com",
    }), { status: 503, headers: { "Content-Type": "application/json" } });
  }

  const body = l402ChallengeBody(inv.invoice, inv.amount_sats || route.sats, inv.payment_hash);
  return new Response(JSON.stringify(body, null, 2), {
    status: 402,
    headers: {
      "Content-Type": "application/json",
      "WWW-Authenticate": `L402 macaroon="", invoice="${inv.invoice}"`,
      "X-Payment-Hash": inv.payment_hash,
    },
  });
}

// ─── Export ─────────────────────────────────────────────────────────────────

export default {
  async fetch(request, env) {
    const agentKey = env.LF_AGENT_KEY || env.LF_API_KEY || env.HF_Bearer || "";
    if (!agentKey) {
      return new Response(JSON.stringify({
        error: "no_agent_key",
        hint: "Set env.LF_AGENT_KEY in wrangler secrets",
      }), { status: 500, headers: { "Content-Type": "application/json" } });
    }
    try {
      return await handle(request, agentKey);
    } catch (e) {
      return new Response(JSON.stringify({
        error: "internal",
        message: String(e),
      }), { status: 500, headers: { "Content-Type": "application/json" } });
    }
  },
};
