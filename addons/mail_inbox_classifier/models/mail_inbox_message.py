from odoo import api, fields, models

CATEGORY_KEYWORDS = {
    "customer_support": [
        "support", "help", "issue", "problem", "complaint", "not working",
        "broken", "error", "trouble", "assistance",
    ],
    "order_history": [
        "order", "invoice", "shipment", "shipping", "delivery", "tracking",
        "refund", "return", "payment", "receipt",
    ],
    "query": [
        "question", "query", "inquiry", "enquiry", "info", "information",
        "price", "quote", "quotation", "availability",
    ],
}


class MailInboxMessage(models.Model):
    _name = "mail.inbox.message"
    _inherit = ["mail.thread"]
    _description = "Categorized Inbox Message"
    _order = "create_date desc"

    name = fields.Char(string="Subject", required=True)
    email_from = fields.Char(string="From")
    category = fields.Selection(
        [
            ("customer_support", "Customer Support"),
            ("order_history", "Order History"),
            ("query", "General Query"),
            ("other", "Other"),
        ],
        string="Category",
        default="other",
        tracking=True,
    )
    body_preview = fields.Html(string="Body")
    received_date = fields.Datetime(string="Received On", default=fields.Datetime.now)

    @api.model
    def message_new(self, msg_dict, custom_values=None):
        custom_values = dict(custom_values or {})
        subject = msg_dict.get("subject") or ""
        body = msg_dict.get("body") or ""
        custom_values.setdefault("name", subject or "(No subject)")
        custom_values.setdefault("email_from", msg_dict.get("email_from"))
        custom_values.setdefault("body_preview", body)
        custom_values.setdefault("category", self._classify(subject, body))
        return super().message_new(msg_dict, custom_values)

    def _classify(self, subject, body):
        text = f"{subject} {body}".lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in text for keyword in keywords):
                return category
        return "other"
