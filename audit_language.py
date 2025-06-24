from gdpr_score import estimate_fine, calculate_gdpr_score

PRIVACY_KEYWORDS = ["privacy", "конфіденційність", "приватність", "datenschutzrichtlinie", "confidentialité", "policies", "policy", "confidential", "confidentiality"]
COOKIE_KEYWORDS = ["cookie", "cookies", "куки"]
CONSENT_KEYWORDS = ["consent", "згода", "відмовитися", "відмова"]

async def audit_language(playwright, language, proxy_servers, usernames, TARGET_URL):
    browser = await playwright.chromium.launch(headless=True)
    proxy = proxy_servers.get(language)
    username = usernames.get(language)
    context = await browser.new_context(
        locale=language,
        proxy={"server": proxy,"username": username, "password":"RIBkOWJDSbw8"} if proxy else None
    )
    page = await context.new_page()

    print(f"\nПеревірка для мови: {language.upper()}")
    await page.goto(TARGET_URL, wait_until="load", timeout=60000)
    await page.reload()
    await page.wait_for_timeout(timeout=5000)

    main_page_lang = await page.locator("html").get_attribute("lang")
    print(f"Мова основної сторінки: {main_page_lang or 'не вказано'}")

    is_same_language = False
    if main_page_lang:
        page_lang_short = main_page_lang.split('-')[0].lower()
        expected_lang_short = language
        is_same_language = (page_lang_short == expected_lang_short)

    localized_url = None

    if is_same_language:
        localized_url = TARGET_URL

    if not localized_url:
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
            if href and any(code in href.lower() for code in ["/ua"] if language == "uk"):
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

            href_lower = href.lower()

            if not privacy_url and (
                    any(k in text for k in PRIVACY_KEYWORDS) or any(k in href_lower for k in PRIVACY_KEYWORDS)):
                privacy_url = href
                print("Privacy URL:", privacy_url)

            if not cookie_url and (
                    any(k in text for k in COOKIE_KEYWORDS) or any(k in href_lower for k in COOKIE_KEYWORDS)):
                cookie_url = href
                print("Cookie URL:", cookie_url)

        except Exception as e:
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
    elif banner_found:
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
    elif banner_found:
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
        "privacy_policy_found": bool(privacy_url or banner_found),
        "privacy_mentions_data": privacy_mentions_data,
        "cookie_policy_found": bool(cookie_url or banner_found),
        "cookie_policy_detailed": cookie_policy_detailed
    })
    fine_estimate = estimate_fine(score)

    return {
        "language": language,
        "original_page_language": main_page_lang or "not specified",
        "localized_page_found": localized_found,
        "page_language": lang_attr or "not specified",
        "cookie_banner": banner_found,
        "privacy_policy_found": bool(privacy_url or banner_found),
        "privacy_mentions_data": privacy_mentions_data,
        "cookie_policy_found": bool(cookie_url or banner_found),
        "cookie_policy_detailed": cookie_policy_detailed,
        "gdpr_compliance_score": score,
        "gdpr_fine_estimate": fine_estimate
    }