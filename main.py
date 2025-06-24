import asyncio
import json
from playwright.async_api import async_playwright

from urllib.parse import urlparse

from audit_language import audit_language

TARGET_URL = "https://chess.com/"
DOMAIN_NAME = urlparse(TARGET_URL).netloc
if DOMAIN_NAME.startswith("www."):
    DOMAIN_NAME = DOMAIN_NAME[4:]

LANGUAGES = ["uk", "de", "fr"]

proxy_servers = {
    "de": "http://s-26696.sp2.ovh:11001",
    "fr": "http://s-26696.sp2.ovh:11002"
}
usernames = {
    "de": "wmJabM2_0",
    "fr": "wmJabM2_1"
}

async def main():
    async with async_playwright() as p:
        results = {"domain": DOMAIN_NAME,}
        for lang in LANGUAGES:
            result = await audit_language(p, lang, proxy_servers, usernames, TARGET_URL)
            results[lang] = result

        with open(f"results/{DOMAIN_NAME}.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nРезультати збережено в {DOMAIN_NAME}.json")

if __name__ == "__main__":
    asyncio.run(main())