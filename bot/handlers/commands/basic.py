from __future__ import annotations

from config import Settings
from services import BackendError, LMSApiClient


def _build_api_client(settings: Settings) -> LMSApiClient:
    return LMSApiClient(
        base_url=settings.lms_api_base_url,
        api_key=settings.lms_api_key,
    )


def _extract_labs(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [item for item in items if item.get("type") == "lab"]


def _format_backend_error(message: str) -> str:
    return f"Backend error: {message}"


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


async def handle_health(settings: Settings) -> str:
    client = _build_api_client(settings)
    try:
        items = await client.get_items()
    except BackendError as exc:
        return _format_backend_error(str(exc))

    return f"Backend is healthy. {len(items)} items available."


async def handle_labs(settings: Settings) -> str:
    client = _build_api_client(settings)
    try:
        labs = _extract_labs(await client.get_items())
    except BackendError as exc:
        return _format_backend_error(str(exc))

    if not labs:
        return "No labs found."

    lines = ["Available labs:"]
    for lab in labs:
        title = str(lab.get("title", "Untitled lab"))
        lines.append(f"- {title}")
    return "\n".join(lines)


async def handle_scores(lab: str | None, settings: Settings) -> str:
    if not lab:
        return "Usage: /scores <lab>. Example: /scores lab-04"

    client = _build_api_client(settings)
    try:
        pass_rates = await client.get_pass_rates(lab)
    except BackendError as exc:
        return _format_backend_error(str(exc))

    if not pass_rates:
        return f"No score data found for {lab}."

    lines = [f"Pass rates for {lab}:"]
    for entry in pass_rates:
        task = str(entry.get("task", "Unknown task"))
        avg_score = float(entry.get("avg_score", 0.0))
        attempts = int(entry.get("attempts", 0))
        lines.append(f"- {task}: {avg_score:.1f}% ({attempts} attempts)")
    return "\n".join(lines)


async def handle_plain_text(text: str) -> str:
    return (
        "Natural language routing is not implemented yet. "
        f"You sent: {text}"
    )


async def handle_unknown(command: str) -> str:
    return f"Unknown command: {command}. Use /help."
