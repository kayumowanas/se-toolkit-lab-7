from __future__ import annotations

from config import Settings

from .commands import (
    handle_health,
    handle_help,
    handle_labs,
    handle_plain_text,
    handle_scores,
    handle_start,
    handle_unknown,
)


async def dispatch_text(text: str, settings: Settings) -> str:
    stripped = text.strip()
    if not stripped:
        return "Please enter a command or a question."

    if not stripped.startswith("/"):
        return await handle_plain_text(stripped)

    parts = stripped.split()
    command = parts[0].lower()

    if command == "/start":
        return await handle_start()
    if command == "/help":
        return await handle_help()
    if command == "/health":
        return await handle_health(settings)
    if command == "/labs":
        return await handle_labs(settings)
    if command == "/scores":
        lab = parts[1] if len(parts) > 1 else None
        return await handle_scores(lab, settings)
    return await handle_unknown(command)
