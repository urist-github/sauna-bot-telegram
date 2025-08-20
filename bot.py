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
CANCEL_WORDS = {"/cancel", "Скасувати", "Cancel", "❌ Скасувати", "❌ Cancel"}

# Групування списку по 2 кнопки в ряд
def group_menu(items, n=2):
    args = [iter(items)] * n
    return [list(filter(None, group)) for group in zip_longest(*args)]

# --- спільні утиліти ---------------------------------------------------------
async def notify_manager(update: Update, context: ContextTypes.DEFAULT_TYPE, extra_text: str = ""):
    """Шле службове повідомлення менеджеру про користувача + довільний текст запиту."""
    user = update.effective_user
    base = (
        f"📬 Новий запит від користувача\n"
        f"• Name: {user.full_name}\n"
        f"• Username: @{user.username if user.username else '—'}\n"
        f"• User ID: {user.id}\n"
    )
    if extra_text:
        base += f"\n📝 Повідомлення:\n{extra_text}"
    await context.bot.send_message(chat_id=MANAGER_CHAT_ID, text=base)

# --- старт/меню --------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # скидаємо можливі незавершені стани
    context.user_data.pop("awaiting_custom", None)

    await update.message.reply_text(
        MESSAGES["ua"]["start"],
        reply_markup=ReplyKeyboardMarkup(LANGUAGE_KEYBOARD, resize_keyboard=True)
    )

async def handle_contact_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await notify_manager(update, context, extra_text="🔔 Кнопка: Зв’язатися з менеджером")
    await update.message.reply_text("Наш менеджер скоро з вами звʼяжеться 🙌")

# --- КАСТОМНА САУНА ----------------------------------------------------------
async def start_custom_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вмикаємо режим збору повідомлення для кастомної сауни."""
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
    await update.message.reply_text(prompts.get(lang, prompts["ua"]), parse_mode="Markdown")

async def handle_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробляємо введений текст у режимі кастомної сауни та пересилаємо менеджеру."""
    text = update.message.text.strip()

    # скасування
    if text in CANCEL_WORDS:
        context.user_data.pop("awaiting_custom", None)
        lang = context.user_data.get("lang", "ua")
        msg = {"ua": "Скасовано ✅", "en": "Cancelled ✅"}.get(lang, "Скасовано ✅")
        await update.message.reply_text(msg)
        return

    # надсилаємо менеджеру
    await notify_manager(update, context, extra_text=f"🧩 Кастомна сауна — заявка користувача:\n{text}")

    # підтвердження користувачу
    lang = context.user_data.get("lang", "ua")
    ok = {
        "ua": "Дякуємо! Ваше повідомлення надіслано менеджеру. Ми відповімо якнайшвидше 🙌",
        "en": "Thanks! Your message has been sent to the manager. We'll get back to you soon 🙌",
    }.get(lang, "Дякуємо! Ваше повідомлення надіслано менеджеру. Ми відповімо якнайшвидше 🙌")
    await update.message.reply_text(ok)

    # очищаємо стан
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

# --- головний хендлер тексту -------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    lang = context.user_data.get("lang")

    # якщо активний режим "кастомна сауна" — перехоплюємо будь-який текст
    if context.user_data.get("awaiting_custom"):
        await handle_custom_message(update, context)
        return

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
        # додамо кнопку скасування під час набору кастом-запиту
        menu = group_menu(raw_menu, n=2)
        await update.message.reply_text(
            MESSAGES[lang]["main"],
            reply_markup=ReplyKeyboardMarkup(menu, resize_keyboard=True)
        )
        return

    # Реакція на меню
    responses = {
        "ua": {
            "📦 Каталог саун": send_catalog,
            "🪵 Матеріали": (
                "🪵 *Матеріали, які ми використовуємо у наших сауна-бані:*\n\n"
                "Каркас з сосни 50×100 мм, утеплення — 10 см мінеральної вати.\n\n"
                "🔹 *Зовні:*\n"
                "— 2 стіни: металевий клік-фальц\n"
                "— 2 стіни: дерев’яний планкен або гонт\n\n"
                "🔹 *Пиріг стіни (зовні → всередину):*\n"
                "1. Металевий клік-фальц або дерев’яний фасад\n"
                "2. Монтажна дерев’яна рейка\n"
                "3. Вітрозахисна мембрана\n"
                "4. Мінеральна вата 100 мм\n"
                "5. Фольгований паробар’єр\n"
                "6. Вагонка з вільхи\n\n"
                "🔹 *Всередині парної:*\n"
                "— Лежаки з вільхи\n"
                "— Панорамне гартоване скло 6 мм"
            ),
            "🛠 Додаткові опції": "Дивіться всі доступні опції за посиланням:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Кастомна sauna": start_custom_request,  # <-- ТЕПЕР запускає режим збору повідомлення
            "📞 Зв’язатися з менеджером": handle_contact_request,
            "🌍 Змінити мову": start
        },
        "en": {
            "📦 Sauna catalog": send_catalog,
            "🪵 Materials": (
                "🪵 *Materials we use in our outdoor sauna cabins:*\n\n"
                "The frame is made of pine 50×100 mm with 100 mm mineral wool insulation.\n\n"
                "🔹 *Exterior cladding:*\n"
                "— 2 walls: metal click-lock panels\n"
                "— 2 walls: natural wood planks or shingles\n\n"
                "🔹 *Wall structure (outside → inside):*\n"
                "1. Metal click-lock or wooden facade\n"
                "2. Wooden battens\n"
                "3. Windproof membrane\n"
                "4. 100 mm mineral wool\n"
                "5. Foil vapor barrier\n"
                "6. Alder paneling\n\n"
                "🔹 *Inside the steam room:*\n"
                "— Alder benches\n"
                "— Tempered glass panel (6 mm)"
            ),
            "🛠 Extra features": "See all available features here:\nhttps://urist-github.github.io/sauna-price/",
            "✍️ Custom sauna": start_custom_request,  # <-- ТЕПЕР запускає режим збору повідомлення
            "📞 Contact a manager": handle_contact_request,
            "🌍 Change language": start
        }
    }

    reply = responses[lang].get(text)

    if callable(reply):
        await reply(update, context)
    elif isinstance(reply, str):
        await update.message.reply_text(reply, parse_mode="Markdown")
    else:
        await update.message.reply_text("Виберіть дію з меню 👇")

# --- main --------------------------------------------------------------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", handle_custom_message))  # щоб /cancel спрацьовував будь-коли
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
