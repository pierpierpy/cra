from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import os
import psycopg2
from datetime import datetime

load_dotenv()

conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT"),
)
conn.autocommit = True


def log_message_to_db(user_id, username, message):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO telegram_messages (user_id, username, message, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, username, message, datetime.utcnow()),
        )


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_message = update.message.text.lower()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"

    log_message_to_db(user_id, username, user_message)

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
