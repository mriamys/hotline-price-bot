import asyncio
import re
from playwright.async_api import async_playwright

HEADERS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
}

def clean_price(price_str):
    if not price_str:
        return 0
    # Сначала находим все числа (с пробелами внутри), потом чистим
    # "35 640 – 54 199 грн" -> ['35 640', '54 199'] -> берём первое -> 35640
    matches = re.findall(r'[\d][\d\s]*\d|\d+', price_str.replace('\xa0', ' '))
    if not matches:
        return 0
    first = re.sub(r'\s+', '', matches[0])
    return int(first) if first.isdigit() else 0


async def search_hotline(query):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent=HEADERS["user_agent"],
            viewport={'width': 1280, 'height': 1024},
            locale="uk-UA",
        )
        page = await context.new_page()
        try:
            await page.goto(
                f"https://hotline.ua/ua/sr/?q={query.replace(' ', '+')}",
                wait_until="domcontentloaded",
                timeout=30000
            )
            await page.wait_for_selector('.list-item', timeout=10000)
            items = await page.query_selector_all('.list-item')
            results = []
            for item in items[:5]:
                title_elem = await item.query_selector('.item-title')
                if not title_elem:
                    continue

                # Перебираем возможные селекторы цены
                price_text = None
                for sel in [
                    '.price-format__main',
                    '.list-item__value',
                    '.price-md',
                    '.cost',
                ]:
                    price_elem = await item.query_selector(sel)
                    if price_elem:
                        raw = await price_elem.inner_text()
                        if raw and any(c.isdigit() for c in raw):
                            price_text = raw.strip().replace('\xa0', ' ')
                            break

                img_elem = await item.query_selector('.list-item__photo img')
                title = (await title_elem.inner_text()).strip()
                href = await title_elem.get_attribute('href')
                img_url = await img_elem.get_attribute('src') if img_elem else None

                results.append({
                    "title": title,
                    "price": price_text or "Цена не указана",
                    "link": f"https://hotline.ua{href}" if href else "#",
                    "img": (
                        f"https://hotline.ua{img_url}"
                        if img_url and img_url.startswith('/')
                        else img_url
                    ),
                })
            return results
        except Exception as e:
            print(f"[search_hotline] Ошибка: {e}")
            return []
        finally:
            await browser.close()


async def get_price_by_link(link):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 900},
            locale="uk-UA",
        )
        page = await context.new_page()
        try:
            print(f"📡 Загружаю: {link}")
            response = await page.goto(link, wait_until="networkidle", timeout=60000)
            if response.status >= 400:
                print(f"❌ HTTP {response.status}")
                return None

            # Ждём появления блока с ценой (он грузится через JS)
            try:
                await page.wait_for_selector("span.many__price-sum", timeout=15000)
            except:
                print("⚠️ Блок many__price-sum не появился, пробуем дальше...")

            # Убираем мешающие слои
            await page.evaluate("""() => {
                ['.tooltip-wrapper', '.modal-backdrop', '.app-promotion', '.bug-report-button']
                    .forEach(s => document.querySelectorAll(s).forEach(el => el.remove()));
                document.body.style.overflow = 'auto';
            }""")

            price_selectors = [
                "span.many__price-sum.text-orange",  # ← главный, точный класс
                "div.many__price",  # ← запасной (весь блок)
                ".price-range",  # ← ещё запасной
            ]

            price_text = None
            for sel in price_selectors:
                try:
                    element = await page.wait_for_selector(sel, timeout=5000)
                    if element:
                        raw = await element.inner_text()
                        if raw and any(c.isdigit() for c in raw):
                            price_text = raw.strip().replace('\xa0', ' ')
                            print(f"✅ Цена найдена ({sel}): {price_text}")
                            break
                except Exception:
                    continue

            if not price_text:
                print("⚠️ Цена не найдена, сохраняю скриншот")
                await page.screenshot(path="debug_final.png")

            return price_text

        except Exception as e:
            print(f"❌ Ошибка get_price_by_link: {e}")
            return None
        finally:
            await browser.close()