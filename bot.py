import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from messages import MESSAGES
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

LANGUAGE_KEYBOARD = [["🇺🇦 Українська", "🇬🇧 English"]]

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
    return await update.message.reply_text("Наш менеджер скоро з вами звʼяжеться 🙌")

async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Українська" in text:
        context.user_data["lang"] = "ua"
    elif "English" in text:
        context.user_data["lang"] = "en"
    else:
        await update.message.reply_text("Будь ласка, оберіть мову / Please choose a language.")
        return

    lang = context.user_data["lang"]
    menu = [[m] for m in MESSAGES[lang]["menu"]]
    await update.message.reply_text(
        MESSAGES[lang]["main"],
        reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True)
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ua")
    text = update.message.text

    responses = {
        "ua": {
            "📦 Каталог саун": "Ось наш каталог саун: [PDF / посилання]",
            "🪵 Матеріали": "Ми використовуємо термоосику, термоясен, мінеральну вату тощо...",
            "🛠 Додаткові опції": "Доступні опції: панорамне вікно, RGB освітлення, Bluetooth...",
            "✍️ Кастомна sauna": "Напишіть нам свої побажання — зробимо індивідуальний проєкт!",
            "📞 Зв’язатися з менеджером": await notify_manager(update, context),
            "🌍 Змінити мову": await start(update, context)
        },
        "en": {
            "📦 Sauna catalog": "Here is our sauna catalog: [PDF / link]",
            "🪵 Materials": "We use thermo-aspen, thermo-ash, mineral wool, etc...",
            "🛠 Extra features": "Available: panoramic window, RGB lighting, Bluetooth audio...",
            "✍️ Custom sauna": "Send us your ideas — we’ll design a custom sauna for you!",
            "📞 Contact a manager": await notify_manager(update, context),
            "🌍 Change language": await start(update, context)
        }
    }

    reply = responses[lang].get(text)
    if isinstance(reply, str):
        await update.message.reply_text(reply)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
