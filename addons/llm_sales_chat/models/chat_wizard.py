import json
import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a helpful assistant embedded in an Odoo ERP system. "
    "You answer questions about Sales and CRM data ONLY by calling the "
    "tools provided — never guess or invent numbers. "
    "If a question can't be answered with the available tools, say so "
    "plainly and suggest what info would help. Keep answers short and "
    "in plain business language, not raw JSON."
)


class ChatWizard(models.TransientModel):
    _name = "llm.chat.wizard"
    _description = "Ask the Sales & CRM Chatbot"

    question = fields.Text(string="Your question")
    answer = fields.Html(string="Answer", readonly=True)

    def action_ask(self):
        self.ensure_one()
        if not self.question:
            self.answer = "<p>Please type a question first.</p>"
            return self._reopen()

        from .chat_tools import TOOL_SCHEMA

        client = self.env["llm.groq.client"]
        tools_model = self.env["llm.chat.tools"]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self.question},
        ]

        # First call: let the model decide which tool(s) to use
        response = client.chat(messages, tools=TOOL_SCHEMA)
        choice = response["choices"][0]["message"]
        messages.append(choice)

        tool_calls = choice.get("tool_calls") or []

        # Execute any requested tools and feed results back
        for call in tool_calls:
            fn_name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            _logger.info("LLM requested tool: %s(%s)", fn_name, args)
            result = tools_model.execute(fn_name, args)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                }
            )

        # Second call: get the final natural-language answer
        if tool_calls:
            final = client.chat(messages)
            final_text = final["choices"][0]["message"]["content"]
        else:
            final_text = choice.get("content") or "I couldn't find an answer."

        self.answer = f"<p>{final_text}</p>"
        return self._reopen()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "llm.chat.wizard",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }
