import os
from datetime import datetime
import asyncio
import logging
from typing import Optional

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    filters,
    ContextTypes,
)

import psycopg2
import aiohttp

# ----------------------------
# Config / Env
# ----------------------------
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TOKEN") or os.getenv("token")  # accept either
LLM_BASE_URL = os.getenv(
    "LLM_BASE_URL", "https://728b4ad57c33.ngrok-free.app"
)  # your ngrok URL
LLM_MODEL = os.getenv("LLM_MODEL", "local")  # llama.cpp server expects "local"
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "30"))  # seconds

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

if not TELEGRAM_TOKEN:
    raise RuntimeError("Missing TELEGRAM TOKEN env var. Set TOKEN=...")

# Basic logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("bot")

# ----------------------------
# Database (sync, simple)
# ----------------------------
conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT
)
conn.autocommit = True


def log_message_to_db(user_id: int, username: str, message: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO telegram_messages (user_id, username, message, timestamp) VALUES (%s, %s, %s, %s)",
            (user_id, username, message, datetime.now()),
        )


# ----------------------------
# LLM client (async, uses aiohttp)
# ----------------------------
async def llm_chat(session: aiohttp.ClientSession, user_text: str) -> Optional[str]:
    """
    Calls llama.cpp OpenAI-style /v1/chat/completions and returns the assistant content.
    """
    url = f"{LLM_BASE_URL.rstrip('/')}/v1/chat/completions"
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "You are a concise, helpful assistant."},
            {"role": "user", "content": user_text},
        ],
        "max_tokens": 256,
        "temperature": 0.7,
        "stream": False,
    }
    try:
        async with session.post(url, json=payload, timeout=LLM_TIMEOUT) as resp:
            if resp.status != 200:
                text = await resp.text()
                log.warning("LLM HTTP %s: %s", resp.status, text[:500])
                return None
            data = await resp.json()
    except asyncio.TimeoutError:
        log.warning("LLM request timed out")
        return None
    except Exception as e:
        log.exception("LLM request error: %s", e)
        return None

    # Expected schema from llama.cpp (OpenAI-compatible)
    try:
        content = data["choices"][0]["message"]["content"]
        return content.strip()
    except Exception as e:
        log.exception("LLM parse error: %s; data=%s", e, str(data)[:500])
        return None


# ----------------------------
# Telegram handlers
# ----------------------------
async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    user_message_raw = update.message.text
    user_message = user_message_raw.strip().lower()
    user_id = update.message.from_user.id
    username = update.message.from_user.username or "Unknown"

    # log incoming message
    try:
        log_message_to_db(user_id, username, user_message_raw)
    except Exception as e:
        log.exception("DB log failed: %s", e)

    # hard-coded replies
    if user_message == "cra":
        await update.message.reply_text("cra")
        return
    if user_message == "quack":
        await update.message.reply_text("quack")
        return
    if user_message == "gabbibbo":
        try:
            with open("gbb.jpg", "rb") as photo:
                await update.message.reply_photo(photo=photo)
        except FileNotFoundError:
            await update.message.reply_text("Missing gbb.jpg on server.")
        return

    # default: call LLM
    session: aiohttp.ClientSession = context.bot_data["http_session"]
    reply = await llm_chat(session, user_message_raw)

    if reply:
        await update.message.reply_text(reply)
    else:
        await update.message.reply_text("Sorry, I couldn't get a response right now.")


async def on_startup(app):
    # one shared HTTP client
    app.bot_data["http_session"] = aiohttp.ClientSession()


async def on_shutdown(app):
    # clean HTTP client
    session: aiohttp.ClientSession = app.bot_data.get("http_session")
    if session and not session.closed:
        await session.close()


def main():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(on_startup)
        .post_shutdown(on_shutdown)
        .build()
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))
    app.run_polling()


if __name__ == "__main__":
    main()
