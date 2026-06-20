"""
price_feed.py — multi-source price lookup via DexScreener + Birdeye
Used for TP/SL trigger evaluation. Conservative: prefer DexScreener (free, no key).
"""
import aiohttp
import asyncio
import time
import config


DEXSCREENER = "https://api.dexscreener.com/latest/dex/tokens/{}"
BIRDEYE = "https://public-api.birdeye.so/defi/price?address={}"


async def get_price_dex(token_mint: str) -> dict | None:
    """Free, no key. Returns {'priceUsd': float, 'priceChange24h': float, 'liquidity': float, 'volume24h': float, 'pairAddress': str}"""
    try:
        url = DEXSCREENER.format(token_mint)
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=10) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        pairs = data.get("pairs") or []
        # pick highest-liquidity pair (raydium / pump.fun / meteora)
        best = max(pairs, key=lambda p: (p.get("liquidity") or {}).get("usd", 0) or 0, default=None)
        if not best:
            return None
        return {
            "priceUsd": float(best.get("priceUsd") or 0),
            "priceChange24h": float((best.get("priceChange") or {}).get("h24") or 0),
            "priceChange1h": float((best.get("priceChange") or {}).get("h1") or 0),
            "liquidity": float((best.get("liquidity") or {}).get("usd") or 0),
            "volume24h": float((best.get("volume") or {}).get("h24") or 0),
            "pairAddress": best.get("pairAddress"),
            "dexId": best.get("dexId"),
            "url": best.get("url"),
            "ts": time.time(),
        }
    except Exception as e:
        print(f"[price dex error] {e}")
        return None


async def get_price_birdeye(token_mint: str) -> float | None:
    """Optional. Requires BIRDEYE_API_KEY. Higher rate-limit."""
    if not config.BIRDEYE_API_KEY:
        return None
    try:
        url = BIRDEYE.format(token_mint)
        headers = {"X-API-KEY": config.BIRDEYE_API_KEY, "accept": "application/json"}
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=10) as r:
                if r.status != 200:
                    return None
                data = await r.json()
        v = data.get("data", {}).get("value")
        return float(v) if v else None
    except Exception as e:
        print(f"[birdeye error] {e}")
        return None


async def get_price(token_mint: str) -> dict | None:
    """Birdeye first (faster + paid), fallback to DexScreener."""
    p = await get_price_birdeye(token_mint)
    if p:
        return {"priceUsd": p, "source": "birdeye"}
    return await get_price_dex(token_mint)


if __name__ == "__main__":
    # SOL test
    out = asyncio.run(get_price("So11111111111111111111111111111111111111112"))
    print(out)
