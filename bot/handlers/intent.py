from __future__ import annotations

import json
import sys

from config import Settings
from services import BackendError, LLMClient, LLMError, LMSApiClient


SYSTEM_PROMPT = """
You are an LMS analytics assistant inside a Telegram bot.
Use tools for factual questions about labs, learners, scores, groups, timelines, and completion.
When the user greets you, replies with nonsense, or asks something ambiguous, answer directly without tools.
If the user asks about analytics or LMS data, prefer tools over guessing.
When you use tools, summarize the returned data clearly and concretely.
For comparison questions, keep calling tools until you can name the specific lab, group, learner, or metric the user asked about.
Never stop with an intermediate progress update such as "I will continue checking" or "let me check the rest".
If tool results are already sufficient, give the final answer immediately with the relevant number or ranking.
""".strip()


def _build_api_client(settings: Settings) -> LMSApiClient:
    return LMSApiClient(
        base_url=settings.lms_api_base_url,
        api_key=settings.lms_api_key,
    )


def _build_llm_client(settings: Settings) -> LLMClient:
    return LLMClient(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_api_model,
    )


def _tool_schemas() -> list[dict[str, object]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "get_items",
                "description": "List LMS items such as labs and tasks.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_learners",
                "description": "Get enrolled students and their groups.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_scores",
                "description": "Get score distribution buckets for a specific lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_pass_rates",
                "description": "Get per-task average scores and attempt counts for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_timeline",
                "description": "Get submission timeline by day for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_groups",
                "description": "Get per-group performance for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_top_learners",
                "description": "Get top learners for a lab or leaderboard questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        },
                        "limit": {
                            "type": "integer",
                            "description": "How many learners to return.",
                        },
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_completion_rate",
                "description": "Get overall completion percentage for a lab.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lab": {
                            "type": "string",
                            "description": "Lab identifier, for example lab-04.",
                        }
                    },
                    "required": ["lab"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "trigger_sync",
                "description": "Refresh LMS data from autochecker.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
    ]


async def _run_tool(
    client: LMSApiClient, tool_name: str, arguments: dict[str, object]
) -> dict[str, object] | list[dict[str, object]]:
    if tool_name == "get_items":
        return await client.get_items()
    if tool_name == "get_learners":
        return await client.get_learners()
    if tool_name == "get_scores":
        return await client.get_scores(str(arguments["lab"]))
    if tool_name == "get_pass_rates":
        return await client.get_pass_rates(str(arguments["lab"]))
    if tool_name == "get_timeline":
        return await client.get_timeline(str(arguments["lab"]))
    if tool_name == "get_groups":
        return await client.get_groups(str(arguments["lab"]))
    if tool_name == "get_top_learners":
        limit = int(arguments.get("limit", 10))
        return await client.get_top_learners(str(arguments["lab"]), limit=limit)
    if tool_name == "get_completion_rate":
        return await client.get_completion_rate(str(arguments["lab"]))
    if tool_name == "trigger_sync":
        return await client.trigger_sync()
    raise BackendError(f"Unsupported tool: {tool_name}")


def _preview_result(result: dict[str, object] | list[dict[str, object]]) -> str:
    if isinstance(result, list):
        return f"{len(result)} records"
    return ", ".join(f"{key}={value}" for key, value in list(result.items())[:3])


def _looks_incomplete(content: str) -> bool:
    lowered = content.lower()
    markers = [
        "let me check",
        "let me continue",
        "i will continue",
        "checking the remaining",
        "continue checking",
        "i'll check",
        "i need to check",
    ]
    return any(marker in lowered for marker in markers)


async def handle_plain_text(text: str, settings: Settings) -> str:
    llm_client = _build_llm_client(settings)
    api_client = _build_api_client(settings)
    tools = _tool_schemas()
    messages: list[dict[str, object]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    used_tools = False

    try:
        for _ in range(16):
            response = await llm_client.create_chat_completion(messages, tools=tools)
            assistant_message = llm_client.extract_message(response)
            messages.append(assistant_message)

            tool_calls = assistant_message.get("tool_calls")
            if not isinstance(tool_calls, list) or not tool_calls:
                content = assistant_message.get("content")
                if isinstance(content, str) and content.strip():
                    if used_tools and _looks_incomplete(content):
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "Your previous answer was only a progress update. "
                                    "Do not send progress updates to the user. Continue calling "
                                    "tools for the remaining data you need, then give one final "
                                    "answer with a specific lab, group, learner, or metric."
                                ),
                            }
                        )
                        continue
                    if used_tools:
                        messages.append(
                            {
                                "role": "system",
                                "content": (
                                    "You already have tool results. If more data is needed, "
                                    "call more tools. Otherwise answer finally now with a "
                                    "specific result, not a progress update."
                                ),
                            }
                        )
                        final_response = await llm_client.create_chat_completion(
                            messages, tools=tools
                        )
                        final_message = llm_client.extract_message(final_response)
                        final_tool_calls = final_message.get("tool_calls")
                        if isinstance(final_tool_calls, list) and final_tool_calls:
                            messages.append(final_message)
                            for tool_call in final_tool_calls:
                                used_tools = True
                                if not isinstance(tool_call, dict):
                                    continue
                                function_payload = tool_call.get("function")
                                if not isinstance(function_payload, dict):
                                    continue

                                tool_name = str(function_payload.get("name", ""))
                                arguments = llm_client.tool_call_arguments(tool_call)
                                print(
                                    f"[tool] LLM called: {tool_name}({json.dumps(arguments)})",
                                    file=sys.stderr,
                                )
                                result = await _run_tool(api_client, tool_name, arguments)
                                print(
                                    f"[tool] Result: {_preview_result(result)}",
                                    file=sys.stderr,
                                )
                                messages.append(
                                    {
                                        "role": "tool",
                                        "tool_call_id": tool_call.get("id", ""),
                                        "name": tool_name,
                                        "content": json.dumps(result),
                                    }
                                )
                            continue
                        final_content = final_message.get("content")
                        if isinstance(final_content, str) and final_content.strip():
                            return final_content.strip()
                    return content.strip()
                return "I could not produce a useful answer. Try /help."

            for tool_call in tool_calls:
                used_tools = True
                if not isinstance(tool_call, dict):
                    continue
                function_payload = tool_call.get("function")
                if not isinstance(function_payload, dict):
                    continue

                tool_name = str(function_payload.get("name", ""))
                arguments = llm_client.tool_call_arguments(tool_call)
                print(
                    f"[tool] LLM called: {tool_name}({json.dumps(arguments)})",
                    file=sys.stderr,
                )
                result = await _run_tool(api_client, tool_name, arguments)
                print(f"[tool] Result: {_preview_result(result)}", file=sys.stderr)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "name": tool_name,
                        "content": json.dumps(result),
                    }
                )

        if used_tools:
            messages.append(
                {
                    "role": "system",
                    "content": (
                        "You already have all collected tool results in the conversation. "
                        "Do not call more tools. Give a final concise answer based only on "
                        "the available tool results."
                    ),
                }
            )
            final_response = await llm_client.create_chat_completion(messages, tools=None)
            final_message = llm_client.extract_message(final_response)
            final_content = final_message.get("content")
            if isinstance(final_content, str) and final_content.strip():
                return final_content.strip()

        return "I could not finish the reasoning loop. Try a more specific question."
    except BackendError as exc:
        return f"Backend error: {exc}"
    except LLMError as exc:
        return f"LLM error: {exc}"
