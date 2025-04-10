from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os

load_dotenv()


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text.lower()

    match user_message:
        case "cra":
            await update.message.reply_text("cra")
        case "quack":
            await update.message.reply_text("miao")
        case _:
            pass


def main():
    app = ApplicationBuilder().token(os.environ.get("token")).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    app.run_polling()


if __name__ == "__main__":
    main()
