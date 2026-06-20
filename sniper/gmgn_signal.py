"""
signal.py — smart-money / trending signal via DexScreener only.
GMGN.ai blocks bot User-Agent (403), so we use DexScreener free API which
covers Pump.fun, Raydium, Meteora bonding curves and trending pools.

Two streams:
  - dexscreener_profiles: latest boosted/trending Solana pairs
  - dexscreener_search: token discovery via trending queries

Filter tuned for EARLY-stage meme (1h-24h old, small but active).
"""
import aiohttp
import asyncio
import time
import config


DS_TRENDING = "https://api.dexscreener.com/latest/dex/search?q=solana%20meme"
DS_PUMPSWAP = "https://api.dexscreener.com/latest/dex/search?q=solana%20pump"
DS_BOOSTED = "https://api.dexscreener.com/latest/dex/tokens/{}"  # single mint
DS_PAIRS_SOL = "https://api.dexscreener.com/latest/dex/pairs/solana/{}"
# Latest token profiles (DexScreener paid feature — try free equivalent first)
DS_TOKEN_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
DS_TOKEN_BOOSTS = "https://api.dexscreener.com/token-boosts/latest/v1"


def _to():
    return aiohttp.ClientTimeout(total=12)


async def _fetch(url: str) -> dict | None:
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0"}, timeout=_to()) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return None
                return await r.json()
    except Exception as e:
        print(f"[signal fetch err] {url}: {e}")
        return None


async def search_solana(queries: list[str]) -> list:
    """Run multiple search queries in parallel; return deduped raw pairs."""
    results = await asyncio.gather(*[_fetch(q) for q in queries])
    out = []
    seen = set()
    for r in results:
        if not r:
            continue
        for p in r.get("pairs") or []:
            if p.get("chainId") != "solana":
                continue
            key = p.get("pairAddress")
            if key in seen:
                continue
            seen.add(key)
            out.append(p)
    return out


async def boosted_tokens(limit: int = 30) -> list[str]:
    """Return list of Solana mint addresses from latest token-boosts feed."""
    data = await _fetch(DS_TOKEN_BOOSTS)
    if not data or not isinstance(data, list):
        return []
    mints = []
    for item in data:
        if item.get("chainId") == "solana":
            addr = item.get("tokenAddress")
            if addr:
                mints.append(addr)
    return mints[:limit]


async def pair_data_for_mints(mints: list[str]) -> list:
    """Resolve mint -> best pair via DS_TOKEN endpoint."""
    out = []
    for m in mints[:8]:  # rate-limit friendly
        d = await _fetch(DS_BOOSTED.format(m))
        if not d:
            continue
        for p in d.get("pairs") or []:
            if p.get("chainId") == "solana":
                out.append(p)
                break
    return out


def _pair_to_candidate(p: dict) -> dict | None:
    base = p.get("baseToken") or {}
    mint = base.get("address")
    if not mint:
        return None
    liq = (p.get("liquidity") or {}).get("usd") or 0
    vol24 = (p.get("volume") or {}).get("h24") or 0
    vol1 = (p.get("volume") or {}).get("h1") or 0
    vol6 = (p.get("volume") or {}).get("h6") or 0
    pc24 = (p.get("priceChange") or {}).get("h24") or 0
    pc1 = (p.get("priceChange") or {}).get("h1") or 0
    pc5m = (p.get("priceChange") or {}).get("m5") or 0
    age_ms = p.get("pairCreatedAt")
    age_h = (time.time() * 1000 - age_ms) / (1000 * 3600) if age_ms else 9999
    return {
        "mint": mint,
        "symbol": base.get("symbol") or mint[:6],
        "name": base.get("name") or "",
        "priceUsd": float(p.get("priceUsd") or 0),
        "liq_usd": liq,
        "vol24h": vol24,
        "vol1h": vol1,
        "vol6h": vol6,
        "pc_24h": pc24,
        "pc_1h": pc1,
        "pc_5m": pc5m,
        "age_hours": age_h,
        "dex": p.get("dexId"),
        "pair_address": p.get("pairAddress"),
        "url": p.get("url"),
        "fdv": p.get("fdv"),
        "market_cap": p.get("marketCap"),
        "txns_24h": (p.get("txns") or {}).get("h24", {}),
    }


def _score(c: dict) -> float:
    """Score 0-10. <0 = reject. Tuned for $5 capital, need high-velocity memes."""
    liq = c.get("liq_usd", 0) or 0
    vol24 = c.get("vol24h", 0) or 0
    vol1 = c.get("vol1h", 0) or 0
    age = c.get("age_hours", 9999) or 9999
    pc1 = c.get("pc_1h", 0) or 0
    pc24 = c.get("pc_24h", 0) or 0
    pc5m = c.get("pc_5m", 0) or 0
    txns = c.get("txns_24h", {}) or {}
    buys = (txns.get("buys") or 0)
    sells = (txns.get("sells") or 0)

    # Hard reject
    if liq < config.MIN_LIQ_USD:
        return -1
    if age > 72:
        return -1
    if age < 0.25:  # <15min — way too early
        return -1
    if pc24 < -50:
        return -1
    if vol24 < config.MIN_VOL24H_USD:
        return -1
    # Buy pressure check
    if buys + sells > 0:
        bs_ratio = buys / (buys + sells)
        if bs_ratio < 0.30:  # mostly selling
            return -1
    else:
        return -1

    score = 0.0
    # Liquidity depth (sweet spot 20k-200k)
    if 20_000 <= liq <= 200_000:
        score += 2.0
    elif liq > 200_000:
        score += 1.2
    # Volume
    score += min(vol24 / 50_000, 2.5)
    score += min(vol1 / 5_000, 1.5)  # recent activity
    # Age sweet spot 1-12h
    if 1 <= age <= 6:
        score += 1.5
    elif 6 < age <= 24:
        score += 1.0
    elif 24 < age <= 48:
        score += 0.5
    # Momentum
    if 10 < pc1 < 200:
        score += min(pc1 / 50, 1.5)
    if 5 < pc5m < 50:
        score += 0.7
    # Buy pressure bonus
    if buys + sells > 0:
        score += min((buys / max(buys + sells, 1)) * 1.5, 1.2)
    return round(score, 2)


async def collect_candidates() -> list:
    """Returns top-N scored candidates sorted by score desc."""
    # Primary: latest boosted tokens (early stage new launches)
    mints = await boosted_tokens(limit=20)
    boosted_pairs = await pair_data_for_mints(mints)
    # Secondary: trending search (volume momentum)
    search_pairs = await search_solana([DS_TRENDING, DS_PUMPSWAP])
    pairs = boosted_pairs + search_pairs

    cands = []
    for p in pairs:
        c = _pair_to_candidate(p)
        if not c:
            continue
        s = _score(c)
        if s < 0:
            continue
        c["score"] = s
        cands.append(c)
    # Dedupe by mint, keep highest score
    by_mint = {}
    for c in cands:
        prev = by_mint.get(c["mint"])
        if not prev or c["score"] > prev["score"]:
            by_mint[c["mint"]] = c
    out = sorted(by_mint.values(), key=lambda x: x["score"], reverse=True)
    print(f"[signal] {len(out)} qualified (boosted={len(boosted_pairs)} + search={len(search_pairs)} pairs)")
    return out[: config.MAX_CANDIDATES]  # type: ignore[attr-defined] if config.MAX_CANDIDATES missing


if __name__ == "__main__":
    import config as cfg
    cands = asyncio.run(collect_candidates())
    for c in cands[:10]:
        sym = c.get("symbol", "?")
        print(f"  {c.get('score',0):5.2f}  {sym:>14}  liq=${c.get('liq_usd',0):>8,.0f}  vol24=${c.get('vol24h',0):>8,.0f}  age={c.get('age_hours',0):5.1f}h  pc1h={c.get('pc_1h',0):+6.1f}%")
