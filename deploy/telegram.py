"""
Telegram notifier - send alerts to B0x70
"""
import aiohttp
import asyncio
import config


async def send(msg: str, silent: bool = False) -> bool:
    try:
        url = f"https://api.telegram.org/bot{config.TG_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": config.TG_CHAT_ID,
            "text": msg,
            "disable_notification": silent,
            "parse_mode": "HTML",
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, timeout=10) as r:
                if r.status == 200:
                    return True
                body = await r.text()
                print(f"[TG FAIL {r.status}] {body[:200]}")
                return False
    except Exception as e:
        print(f"[TG ERROR] {e}")
        return False


def send_sync(msg: str, silent: bool = False) -> bool:
    try:
        return asyncio.run(send(msg, silent=silent))
    except Exception as e:
        print(f"[TG SYNC ERROR] {e}")
        return False


if __name__ == "__main__":
    send_sync("prpo_ai sniper: telegram module self-test OK")
