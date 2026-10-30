from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    groq_api_key = fields.Char(
        string="Groq API Key",
        config_parameter="llm_sales_chat.groq_api_key",
        help="API key from console.groq.com. Stored as a system parameter, "
             "never exposed in views once saved.",
    )
    groq_model = fields.Char(
        string="Groq Model",
        config_parameter="llm_sales_chat.groq_model",
        default="llama-3.3-70b-versatile",
        help="Groq model name to use for chat completions.",
    )
