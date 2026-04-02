import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from hotline_parser import search_hotline
from checker import check_prices
from database import Database
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте переменные окружения.")

# Очистка токена от возможных кавычек и лишних пробелов (распространенная проблема в Railway)
TOKEN = TOKEN.strip().replace('"', '').replace("'", "")
bot = Bot(token=TOKEN)
dp = Dispatcher()
db = Database()

def get_main_menu():
    kb = ReplyKeyboardBuilder()
    kb.button(text="🔍 Поиск")
    kb.button(text="🔔 Мои подписки")
    kb.button(text="❓ Помощь")
    kb.adjust(2)
    return kb.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Выбери действие:", reply_markup=get_main_menu())

@dp.message(F.text.casefold().in_(["🔍 поиск", ".поиск", "поиск"]))
async def ask_search(message: types.Message):
    await message.answer("Напиши название товара:")

@dp.message(F.text == "🔔 Мои подписки")
async def show_subs(message: types.Message):
    subs = db.get_user_subscriptions(message.from_user.id)
    if not subs:
        await message.answer("Подписок нет.")
        return
    for idx, (title, link, price) in enumerate(subs, 1):
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🔗 Перейти", url=link))
        kb.row(types.InlineKeyboardButton(text="❌ Удалить", callback_data=f"remove_{idx-1}"))
        await message.answer(f"{idx}. {title}\n💰 Цена: {price}", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("track_"))
async def track_cb(callback: types.CallbackQuery):
    title = callback.message.caption.split('\n')[0].replace('📦 ', '')
    price = callback.message.caption.split('\n')[1].replace('💰 Цена: ', '')
    link = callback.message.reply_markup.inline_keyboard[0][0].url
    if db.add_subscription(callback.from_user.id, title, link, price):
        await callback.answer("✅ Добавлено!")
    else:
        await callback.answer("Уже следите!", show_alert=True)


@dp.callback_query(F.data.startswith("remove_"))
async def remove_subs_cb(callback: types.CallbackQuery):
    idx = int(callback.data.split('_')[1])
    subs = db.get_user_subscriptions(callback.from_user.id)
    if 0 <= idx < len(subs):
        title, link, _ = subs[idx]
        db.remove_subscription(callback.from_user.id, link)
        await callback.message.delete()
        await callback.answer(f"❌ Удалено: {title}")
    else:
        await callback.answer("Ошибка удаления")


@dp.message(F.text == "❓ Помощь")
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "🤖 *Как пользоваться ботом?*\n\n"
        "1️⃣ Нажми **🔍 Поиск** и введи название товара (например, `iPhone 15`).\n"
        "2️⃣ Выбери нужный товар и нажми **🔔 Следить**.\n"
        "3️⃣ Бот будет проверять цену каждые 10 минут и пришлет уведомление, если она изменится.\n\n"
        "📍 *Управление:*\n"
        "— **🔔 Мои подписки**: список товаров, за которыми ты следишь.\n"
        "— **❌ Удалить**: прекратить отслеживание товара."
    )
    await message.answer(help_text, parse_mode="Markdown")


@dp.message()
async def handle_text(message: types.Message):
    if message.text in ["🔍 Поиск", "🔔 Мои подписки", "❓ Помощь"]: return
    res = await search_hotline(message.text)
    if not res:
        await message.answer("Ничего не нашел.")
        return
    for item in res:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="🔗 На сайт", url=item['link']))
        kb.row(types.InlineKeyboardButton(text="🔔 Следить", callback_data="track_"))
        caption = f"📦 *{item['title']}*\n💰 Цена: {item['price']}"
        if item['img']:
            await message.answer_photo(item['img'], caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")
        else:
            await message.answer(caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(check_prices, 'interval', minutes=60, args=[bot]) # Раз в 10 минут
    scheduler.start()
    print("✅ Планировщик и бот запущены!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())