{
    "name": "LLM Sales & CRM Chat (Groq)",
    "version": "18.0.1.0.0",
    "summary": "Ask natural-language questions about your Sales & CRM data, "
                "answered by a Groq-hosted LLM with safe ORM-backed tools.",
    "category": "Sales",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": ["base", "sale", "crm"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/chat_wizard_views.xml",
    ],
    "installable": True,
    "application": True,
}
