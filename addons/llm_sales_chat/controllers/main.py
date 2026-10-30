import json
import logging
import time

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

PUBLIC_SYSTEM_PROMPT = (
    "You are a helpful assistant on a company's public website. "
    "You can ONLY answer questions about published products/services using "
    "the tools provided. You must NEVER discuss internal business data such "
    "as sales figures, customers, leads, or revenue — you have no access to "
    "that and must say you can't help with that if asked. Keep answers short "
    "and friendly, in plain language, not raw JSON."
)

# Very small in-memory rate limit: max N requests per session per window.
# For production, replace with a proper rate-limiting layer (nginx, Redis, etc.)
_RATE_LIMIT = {}
_RATE_WINDOW = 60  # seconds
_RATE_MAX = 10  # requests per window per session


class LLMPublicChatController(http.Controller):

    def _rate_limited(self, key):
        now = time.time()
        bucket = _RATE_LIMIT.setdefault(key, [])
        # drop timestamps outside the window
        while bucket and bucket[0] < now - _RATE_WINDOW:
            bucket.pop(0)
        if len(bucket) >= _RATE_MAX:
            return True
        bucket.append(now)
        return False

    @http.route(
        "/llm_chat/ask",
        type="json",
        auth="public",
        methods=["POST"],
        csrf=True,
        website=True,
    )
    def ask(self, question=None, **kwargs):
        if not question or not question.strip():
            return {"answer": "Please type a question."}

        session_key = request.session.sid or request.httprequest.remote_addr
        if self._rate_limited(session_key):
            return {"answer": "You're asking a bit fast — please wait a moment and try again."}

        question = question.strip()[:500]  # hard cap input length

        env = request.env
        client = env["llm.groq.client"]
        tools_model = env["llm.chat.public.tools"]
        from odoo.addons.llm_sales_chat.models.chat_public_tools import PUBLIC_TOOL_SCHEMA

        messages = [
            {"role": "system", "content": PUBLIC_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]

        try:
            response = client.chat(messages, tools=PUBLIC_TOOL_SCHEMA)
            choice = response["choices"][0]["message"]
            messages.append(choice)

            tool_calls = choice.get("tool_calls") or []
            for call in tool_calls:
                fn_name = call["function"]["name"]
                try:
                    args = json.loads(call["function"]["arguments"] or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = tools_model.execute(fn_name, args)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps(result),
                    }
                )

            if tool_calls:
                final = client.chat(messages)
                answer = final["choices"][0]["message"]["content"]
            else:
                answer = choice.get("content") or "I'm not sure how to help with that."

        except Exception as e:  # noqa: BLE001 — never leak internals to public users
            _logger.exception("Public chat widget error: %s", e)
            answer = "Sorry, something went wrong. Please try again shortly."

        return {"answer": answer}
