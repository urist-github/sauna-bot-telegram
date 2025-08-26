import os
import html
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from messages import MESSAGES
from dotenv import load_dotenv
from itertools import zip_longest

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID"))

LANGUAGE_KEYBOARD = [["🇺🇦 Українська", "🇬🇧 English"]]
CANCEL_WORDS = {"/cancel", "Скасувати", "Cancel", "❌ Скасувати", "❌ Cancel"}

# --- утиліти відповіді -------------------------------------------------------
DEFAULT_REPLY_KW = dict(disable_web_page_preview=True)

async def send_reply(update: Update, text: str, **kw):
    kw = {**DEFAULT_REPLY_KW, **kw}
    return await update.message.reply_text(text, **kw)

# Групування списку по 2 кнопки в ряд
def group_menu(items, n=2):
    args = [iter(items)] * n
    return [list(filter(None, group)) for group in zip_longest(*args)]

# --- спільні утиліти ---------------------------------------------------------
async def notify_manager(update: Update, context: ContextTypes.DEFAULT_TYPE, extra_text: str = ""):
    """Шле службове повідомлення менеджеру про користувача + довільний текст запиту (HTML safe)."""
    user = update.effective_user
    full_name = html.escape(user.full_name or "")
    username = user.username or "—"
    user_id = user.id

    if user.username:
        contact_link = f"https://t.me/{user.username}"
        contact_caption = "Відкрити чат з користувачем"
    else:
        contact_link = f"tg://user?id={user.id}"
        contact_caption = "Відкрити чат (по ID)"

    base = (
        f"📬 Новий запит від користувача<br>"
        f"• Name: {full_name}<br>"
        f"• Username: <code>@{html.escape(username)}</code><br>"
        f"• User ID: <code>{user_id}</code>"
    )
    if extra_text:
        base += f"<br><br>📝 Повідомлення:<br>{html.escape(extra_text)}"
    base += f'<br><br>👉 <a href="{html.escape(contact_link)}">{contact_caption}</a>'

    await context.bot.send_message(
        chat_id=MANAGER_CHAT_ID,
        text=base,
        parse_mode="HTML",
        disable_web_page_preview=True
    )

# --- старт/меню --------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("awaiting_custom", None)
    await send_reply(
        update,
        MESSAGES["ua"]["start"],
        reply_markup=ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True)
    )

async def handle_contact_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # лише сповіщення менеджеру + підтвердження користувачу
    await notify_manager(update, context, extra_text="🔔 Кнопка: Зв’язатися з менеджером")
    await send_reply(update, "Наш менеджер скоро з вами звʼяжеться 🙌")

# --- КАСТОМНА САУНА ----------------------------------------------------------
async def start_custom_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ua")
    context.user_data["awaiting_custom"] = True
    prompts = {
        "ua": (
            "✍️ Напишіть, будь ласка, ваші побажання щодо *кастомної сауни* "
            "(розміри, кількість людей, тип печі, бюджет тощо).\n\n"
            "Щоб скасувати — надішліть */cancel*."
        ),
        "en": (
            "✍️ Please describe your *custom sauna* request "
            "(dimensions, capacity, heater type, budget, etc.).\n\n"
            "Send */cancel* to abort."
        )
    }
    await send_reply(update, prompts.get(lang, prompts["ua"]), parse_mode="Markdown")

async def handle_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text in CANCEL_WORDS:
        context.user_data.pop("awaiting_custom", None)
        lang = context.user_data.get("lang", "ua")
        msg = {"ua": "Скасовано ✅", "en": "Cancelled ✅"}.get(lang, "Скасовано ✅")
        await send_reply(update, msg)
        return

    await notify_manager(update, context, extra_text=f"🧩 Кастомна сауна — заявка користувача:\n{text}")
    lang = context.user_data.get("lang", "ua")
    ok = {
        "ua": "Дякуємо! Ваше повідомлення надіслано менеджеру. Ми відповімо якнайшвидше 🙌",
        "en": "Thanks! Your message has been sent to the manager. We'll get back to you soon 🙌",
    }.get(lang, "Дякуємо! Ваше повідомлення надіслано менеджеру. Ми відповімо якнайшвидше 🙌")
    await send_reply(update, ok)
    context.user_data.pop("awaiting_custom", None)

# --- каталог / файли ---------------------------------------------------------
async def send_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "ua")
    caption = {
        "ua": "Ось наш актуальний каталог PDF файлом 📄",
        "en": "Here is our latest sauna catalog as a PDF 📄"
    }.get(lang, "Catalog 📄")
    with open("catalog.pdf", "rb") as pdf_file:
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=pdf_file,
            filename="LakeGlow_Sauna_Catalog.pdf",
            caption=caption
        )

# --- службові команди ---------------------------------------------------------
async def unpin_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.unpin_all_chat_messages(chat_id=update.effective_chat.id)
    await send_reply(update, "Прикріплені повідомлення знято ✅")

# --- головний хендлер тексту -------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang")

    if context.user_data.get("awaiting_custom"):
        await handle_custom_message(update, context)
        return

    if text == "🇺🇦 Українська":
        context.user_data["lang"] = "ua"; lang = "ua"
    elif text == "🇬🇧 English":
        context.user_data["lang"] = "en"; lang = "en"

    if not lang:
        await send_reply(update, "Будь ласка, оберіть мову / Please choose a language.")
        return

    if text in ["🇺🇦 Українська", "🇬🇧 English"]:
        raw_menu = MESSAGES[lang]["menu"]
        menu = group_menu(raw_menu, n=2)
        await send_reply(
            update,
            MESSAGES[lang]["main"],
            reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True)
        )
        return

    responses = {
        "ua": {
            "📦 Каталог саун": send_catalog,
            "🪵 Матеріали": (
                "🪵 *Матеріали, які ми використовуємо у наших сауна-бані:*\n\n"
                "Каркас з сосни 50×100 мм, утеплення — 10 см мінеральної вати.\n\n"
                "🔹 *Зовні:*\n— 2 стіни: металевий клік-фальц\n— 2 стіни: дерев’яний планкен або гонт\n\n"
                "🔹 *Пиріг стіни (зовні → всередину):*\n"
                "1. Металевий клік-фальц або дерев’яний фасад\n2. Монтажна рейка\n3. Вітрозахисна мембрана\n"
                "4. Мінеральна вата 100 мм\n5. Фольгований паробар’єр\n6. Вагонка з вільхи\n\n"
                "🔹 *Всередині парної:*\n— Лежаки з вільхи\n— Панорамне гартоване скло 6 мм"
            ),
            "🛠 Додаткові опції": "Дивіться всі доступні опції за посиланням:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Кастомна sauna": start_custom_request,
            "📞 Зв’язатися з менеджером": handle_contact_request,
            "🌍 Змінити мову": start
        },
        "en": {
            "📦 Sauna catalog": send_catalog,
            "🪵 Materials": (
                "🪵 *Materials we use in our outdoor sauna cabins:*\n\n"
                "Frame: pine 50×100 mm, insulation — 100 mm mineral wool.\n\n"
                "🔹 *Exterior:*\n— 2 walls: metal click-lock\n— 2 walls: wooden cladding/shingles\n\n"
                "🔹 *Wall build-up (outside → inside):*\n"
                "1. Metal click-lock or wooden facade\n2. Battens\n3. Windproof membrane\n"
                "4. 100 mm mineral wool\n5. Foil vapor barrier\n6. Alder paneling\n\n"
                "🔹 *Steam room:*\n— Alder benches\n— Tempered glass 6 mm"
            ),
            "🛠 Extra features": "See all available features here:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Custom sauna": start_custom_request,
            "📞 Contact a manager": handle_contact_request,
            "🌍 Change language": start
        }
    }

    reply = responses[lang].get(text)
    if callable(reply):
        await reply(update, context)
    elif isinstance(reply, str):
        await send_reply(update, reply, parse_mode="Markdown")
    else:
        await send_reply(update, "Виберіть дію з меню 👇")

# --- main --------------------------------------------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", handle_custom_message))
    app.add_handler(CommandHandler("unpin", unpin_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
