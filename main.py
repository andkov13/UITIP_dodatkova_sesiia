import asyncio
import json
from playwright.async_api import async_playwright

from urllib.parse import urlparse

TARGET_URL = "https://www.apple.com/"
DOMAIN_NAME = urlparse(TARGET_URL).netloc
if DOMAIN_NAME.startswith("www."):
    DOMAIN_NAME = DOMAIN_NAME[4:]

LANGUAGES = ["uk", "de", "fr"]

PRIVACY_KEYWORDS = ["privacy", "конфіденційність", "приватність", "datenschutzrichtlinie", "confidentialité"]
COOKIE_KEYWORDS = ["cookie", "cookies", "куки"]
CONSENT_KEYWORDS = ["consent", "згода", "відмовитися", "відмова"]

def calculate_gdpr_score(audit):
    score = 100
    if not audit["localized_page_found"]:
        score -= 20
    if not audit["cookie_banner"]:
        score -= 25
    if not audit["privacy_policy_found"]:
        score -= 30
    elif not audit["privacy_mentions_data"]:
        score -= 10
    if not audit["cookie_policy_found"]:
        score -= 15
    elif not audit["cookie_policy_detailed"]:
        score -= 5
    return max(score, 0)

def estimate_fine(score):
    if score == 100:
        return "No risk of GDPR fines."
    elif score >= 80:
        return "Low risk of GDPR fines."
    elif score >= 50:
        return "Moderate risk of GDPR fines."
    else:
        return "High risk of GDPR fines. Immediate action recommended."

async def audit_language(playwright, language):
    browser = await playwright.chromium.launch(headless=True)
    context = await browser.new_context(locale=language)
    page = await context.new_page()

    print(f"\nПеревірка для мови: {language.upper()}")
    await page.goto(TARGET_URL, wait_until="load")

    localized_url = None
    hreflangs = await page.locator("link[rel='alternate']").all()
    for tag in hreflangs:
        hreflang = await tag.get_attribute("hreflang")
        href = await tag.get_attribute("href")
        if hreflang and href and language in hreflang.lower():
            localized_url = href
            break

    if not localized_url:
        links = await page.locator("a").all()
        for link in links:
            href = await link.get_attribute("href")
            if href and any(code in href.lower() for code in ["/ua", "/uk", "/uk-ua", "/ukrainian", "/ua/"] if language == "uk"):
                localized_url = href if href.startswith("http") else f"{TARGET_URL.rstrip('/')}/{href.lstrip('/')}"
                break

    if localized_url:
        print(f"Знайдено локалізовану сторінку: {localized_url}")
        await page.goto(localized_url, wait_until="load")
        localized_found = True
    else:
        print("Локалізована версія не знайдена, залишаємося на основній сторінці.")
        localized_found = False

    lang_attr = await page.locator("html").get_attribute("lang")
    print(f"Mова сторінки: {lang_attr or 'не вказано'}")

    banner_found = False
    for keyword in COOKIE_KEYWORDS + CONSENT_KEYWORDS:
        locator = page.get_by_text(keyword, exact=False)
        if await locator.count() > 0:
            banner_found = True
            print(f"Знайдено згадку про cookie або згоду: «{keyword}»")
            break
    if not banner_found:
        print("Cookie-банер не знайдено.")

    links = await page.locator("a").all()
    privacy_url = None
    cookie_url = None
    for link in links:
        try:
            text = (await link.inner_text()).lower()
            href = await link.get_attribute("href")
            if not href:
                continue
            if not href.startswith("http"):
                href = page.url.rstrip("/") + "/" + href.lstrip("/")
            if any(k in text for k in PRIVACY_KEYWORDS) and not privacy_url:
                privacy_url = href
            if any(k in text for k in COOKIE_KEYWORDS) and not cookie_url:
                cookie_url = href
        except:
            continue

    privacy_mentions_data = False
    if privacy_url:
        print(f"Privacy Policy: {privacy_url}")
        await page.goto(privacy_url)
        text = await page.content()
        if any(k in text.lower() for k in ["data", "персональні дані", "особисті дані"]):
            print("Privacy Policy містить згадки про персональні дані.")
            privacy_mentions_data = True
        else:
            print("Немає згадок про обробку персональних даних.")
    else:
        print("Privacy Policy не знайдено.")

    cookie_policy_detailed = False
    if cookie_url:
        print(f"Cookie Policy: {cookie_url}")
        await page.goto(cookie_url)
        text = await page.content()
        if any(k in text.lower() for k in ["cookie", "cookies", "печиво", "track", "зберігається", "відмовитись"]):
            print("Cookie Policy пояснює використання cookies.")
            cookie_policy_detailed = True
        else:
            print("Cookie Policy не містить необхідної інформації.")
    else:
        print("Cookie Policy не знайдено.")

    await browser.close()

    score = calculate_gdpr_score({
        "localized_page_found": localized_found,
        "cookie_banner": banner_found,
        "privacy_policy_found": bool(privacy_url),
        "privacy_mentions_data": privacy_mentions_data,
        "cookie_policy_found": bool(cookie_url),
        "cookie_policy_detailed": cookie_policy_detailed
    })
    fine_estimate = estimate_fine(score)

    return {
        "language": language,
        "localized_page_found": localized_found,
        "page_language": lang_attr or "not specified",
        "cookie_banner": banner_found,
        "privacy_policy_found": bool(privacy_url),
        "privacy_mentions_data": privacy_mentions_data,
        "cookie_policy_found": bool(cookie_url),
        "cookie_policy_detailed": cookie_policy_detailed,
        "gdpr_compliance_score": score,
        "gdpr_fine_estimate": fine_estimate
    }

async def main():
    async with async_playwright() as p:
        results = {"domain": DOMAIN_NAME,}
        for lang in LANGUAGES:
            result = await audit_language(p, lang)
            results[lang] = result

        with open(f"{DOMAIN_NAME}.json", "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\nРезультати збережено в {DOMAIN_NAME}.json")

if __name__ == "__main__":
    asyncio.run(main())