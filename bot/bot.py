from __future__ import annotations

import argparse
import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import Message

from config import load_settings
from handlers import dispatch_text


def build_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Health", callback_data="cmd:/health"),
                InlineKeyboardButton(text="Labs", callback_data="cmd:/labs"),
            ],
            [
                InlineKeyboardButton(
                    text="Lab 4 Scores", callback_data="cmd:/scores lab-04"
                )
            ],
        ]
    )


async def _reply_with_handler_result(message: Message) -> None:
    response = await dispatch_text(message.text or "", load_settings())
    reply_markup = (
        build_start_keyboard() if (message.text or "").startswith("/start") else None
    )
    await message.answer(response, reply_markup=reply_markup)


async def _handle_callback(callback: CallbackQuery) -> None:
    data = callback.data or ""
    if not data.startswith("cmd:") or callback.message is None:
        await callback.answer()
        return

    response = await dispatch_text(data.removeprefix("cmd:"), load_settings())
    await callback.message.answer(response)
    await callback.answer()


async def run_test_mode(text: str) -> int:
    response = await dispatch_text(text, load_settings())
    print(response)
    return 0


async def run_telegram_mode() -> int:
    settings = load_settings()
    if not settings.bot_token:
        print("BOT_TOKEN is required for Telegram mode.", file=sys.stderr)
        return 1

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.message.register(_reply_with_handler_result, Command("start"))
    dispatcher.message.register(_reply_with_handler_result, Command("help"))
    dispatcher.message.register(_reply_with_handler_result, Command("health"))
    dispatcher.message.register(_reply_with_handler_result, Command("labs"))
    dispatcher.message.register(_reply_with_handler_result, Command("scores"))
    dispatcher.message.register(_reply_with_handler_result)
    dispatcher.callback_query.register(_handle_callback)

    await dispatcher.start_polling(bot)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LMS Telegram bot")
    parser.add_argument("--test", metavar="TEXT", help="Run a single test request")
    return parser.parse_args()


async def main() -> int:
    args = parse_args()
    if args.test is not None:
        return await run_test_mode(args.test)
    return await run_telegram_mode()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
