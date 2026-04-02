import asyncio
from hotline_parser import get_price_by_link, clean_price
from database import Database
from aiogram import Bot

db = Database()


async def check_prices(bot: Bot):
    print("\n🚀 [CHECKER] Проверка цен начата...")
    subs = db.get_all_subscriptions()

    for user_id, title, link, last_price in subs:
        print(f"📡 Загружаю страницу: {title}...")
        current_price_raw = await get_price_by_link(link)

        # Даем небольшую паузу между товарами (1-2 секунды)
        await asyncio.sleep(2)

        if not current_price_raw:
            print(f"❌ Ошибка парсинга для {title} (селектор не найден или таймаут)")
            continue

        curr_int = clean_price(current_price_raw)
        last_int = clean_price(last_price)

        print(f"🔍 {title}: База({last_int}) vs Сайт({curr_int})")

        if curr_int != last_int and last_int > 0:
            print(f"🔔 ЦЕНА ИЗМЕНИЛАСЬ с {last_int} на {curr_int}!")
            status = "📉 Подешевело!" if curr_int < last_int else "📈 Подорожало!"

            try:
                await bot.send_message(
                    user_id,
                    f"{status}\n\n📦 *{title}*\nБыло: {last_price}\nСтало: {current_price_raw}\n\n[Открыть на Hotline]({link})",
                    parse_mode="Markdown"
                )
                db.update_price(link, user_id, current_price_raw)
            except Exception as e:
                print(f"Ошибка отправки сообщения: {e}")