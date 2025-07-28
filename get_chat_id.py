from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

BOT_TOKEN = "8457085922:AAFGfVe46NiAldpVXPIx_-tMLcfmqc2t_b0"

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"chat_id: {update.effective_chat.id}")
    await update.message.reply_text("Ваш chat_id: " + str(update.effective_chat.id))

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
app.run_polling()
