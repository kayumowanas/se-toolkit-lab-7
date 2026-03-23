from __future__ import annotations


async def handle_start() -> str:
    return (
        "Welcome to the LMS bot.\n"
        "Use /help to see available commands or send a question in plain text."
    )


async def handle_help() -> str:
    return (
        "Available commands:\n"
        "/start - welcome message\n"
        "/help - list commands\n"
        "/health - backend health check\n"
        "/labs - list labs\n"
        "/scores <lab> - show lab scores"
    )


async def handle_health() -> str:
    return "Health check is not implemented yet."


async def handle_labs() -> str:
    return "Labs listing is not implemented yet."


async def handle_scores(lab: str | None) -> str:
    if not lab:
        return "Usage: /scores <lab>. Example: /scores lab-04"
    return f"Scores for {lab} are not implemented yet."


async def handle_plain_text(text: str) -> str:
    return (
        "Natural language routing is not implemented yet. "
        f"You sent: {text}"
    )


async def handle_unknown(command: str) -> str:
    return f"Unknown command: {command}. Use /help."
