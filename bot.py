import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from messages import MESSAGES
from dotenv import load_dotenv
from itertools import zip_longest

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

LANGUAGE_KEYBOARD = [["🇺🇦 Українська", "🇬🇧 English"]]

# Групування списку по 2 кнопки в ряд
def group_menu(items, n=2):
    args = [iter(items)] * n
    return [list(filter(None, group)) for group in zip_longest(*args)]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MESSAGES["ua"]["start"],
        reply_markup=ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True)
    )

async def notify_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = (
        f"📬 Новий запит на зв’язок від користувача:\n"
        f"Імʼя: {user.full_name}\n"
        f"Username: @{user.username if user.username else 'немає'}\n"
        f"ID: {user.id}"
    )
    await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=message)

async def handle_contact_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_manager(update, context)
    await update.message.reply_text("Наш менеджер скоро з вами звʼяжеться 🙌")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang")

    # Вибір мови
    if text == "🇺🇦 Українська":
        context.user_data["lang"] = "ua"
        lang = "ua"
    elif text == "🇬🇧 English":
        context.user_data["lang"] = "en"
        lang = "en"

    # Якщо мову ще не вибрано
    if not lang:
        await update.message.reply_text("Будь ласка, оберіть мову / Please choose a language.")
        return

    # Показати головне меню після вибору мови
    if text in ["🇺🇦 Українська", "🇬🇧 English"]:
        raw_menu = MESSAGES[lang]["menu"]
        menu = group_menu(raw_menu, n=2)
        await update.message.reply_text(
            MESSAGES[lang]["main"],
            reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True)
        )
        return

    # Реакція на меню
    responses = {
        "ua": {
            "📦 Каталог саун": "Ось наш каталог саун: [PDF / посилання]",
            "🪵 Матеріали": "Ми використовуємо термоосику, термоясен, мінеральну вату тощо...",
            "🛠 Додаткові опції": "Дивіться всі доступні опції за посиланням:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Кастомна sauna": "Напишіть нам свої побажання — зробимо індивідуальний проєкт!",
            "📞 Зв’язатися з менеджером": handle_contact_request,
            "🌍 Змінити мову": start
        },
        "en": {
            "📦 Sauna catalog": "Here is our sauna catalog: [PDF / link]",
            "🪵 Materials": "We use thermo-aspen, thermo-ash, mineral wool, etc...",
            "🛠 Extra features": "See all available features here:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Custom sauna": "Send us your ideas — we’ll design a custom sauna for you!",
            "📞 Contact a manager": handle_contact_request,
            "🌍 Change language": start
        }
    }

    reply = responses[lang].get(text)

    if callable(reply):
        await reply(update, context)
    elif isinstance(reply, str):
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("Виберіть дію з меню 👇")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
