import json
import logging

import requests

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient(models.AbstractModel):
    """Thin wrapper around Groq's OpenAI-compatible chat completions API."""

    _name = "llm.groq.client"
    _description = "Groq API Client"

    def _get_api_key(self):
        key = self.env["ir.config_parameter"].sudo().get_param(
            "llm_sales_chat.groq_api_key"
        )
        if not key:
            raise UserError(
                "No Groq API key configured. Go to Settings > General Settings "
                "and add your Groq API key."
            )
        return key

    def _get_model(self):
        return (
            self.env["ir.config_parameter"].sudo().get_param(
                "llm_sales_chat.groq_model"
            )
            or "llama-3.3-70b-versatile"
        )

    def chat(self, messages, tools=None, tool_choice="auto"):
        """Call Groq's chat completions endpoint.

        :param messages: list of {"role": ..., "content": ...} dicts
        :param tools: optional list of tool schemas (OpenAI function-calling format)
        :return: the raw API response dict
        """
        headers = {
            "Authorization": f"Bearer {self._get_api_key()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._get_model(),
            "messages": messages,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        try:
            resp = requests.post(
                GROQ_URL, headers=headers, json=payload, timeout=30
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            _logger.error("Groq API call failed: %s", e)
            raise UserError(f"Could not reach Groq API: {e}") from e

        return resp.json()
