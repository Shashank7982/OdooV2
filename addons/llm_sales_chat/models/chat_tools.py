from odoo import models

# ---------------------------------------------------------------------------
# TOOL SCHEMA — sent to Groq so the model knows what functions exist.
# Keep this list small and explicit. Never expose a generic "run any domain
# on any model" tool to the LLM directly from user input — that reintroduces
# the raw-query risk we're trying to avoid.
# ---------------------------------------------------------------------------
TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "count_open_leads",
            "description": "Count CRM leads/opportunities that are still open "
                            "(not won, not lost).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_won_opportunities_this_month",
            "description": "Count CRM opportunities marked as Won this calendar month.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sales_total_this_month",
            "description": "Total confirmed sales order amount (untaxed) for the "
                            "current calendar month.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "top_customers_by_sales",
            "description": "List the top N customers by total confirmed sales order amount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many customers to return (default 5).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "count_orders_by_stage",
            "description": "Count sales orders grouped by their state "
                            "(draft, sent, sale, done, cancel).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ChatTools(models.AbstractModel):
    """Executes the fixed set of tools above, always scoped to the
    requesting user via sudo()-free ORM calls so access rights and
    record rules are respected automatically."""

    _name = "llm.chat.tools"
    _description = "Sales & CRM Chat Tools"

    def execute(self, name, arguments):
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        return handler(**(arguments or {}))

    # -- CRM ----------------------------------------------------------

    def _tool_count_open_leads(self):
        count = self.env["crm.lead"].search_count(
            [("type", "=", "opportunity"), ("active", "=", True),
             ("probability", "<", 100), ("probability", ">", 0)]
        )
        return {"open_leads": count}

    def _tool_count_won_opportunities_this_month(self):
        from datetime import date
        today = date.today()
        first_of_month = today.replace(day=1)
        count = self.env["crm.lead"].search_count(
            [
                ("type", "=", "opportunity"),
                ("stage_id.is_won", "=", True),
                ("date_closed", ">=", first_of_month.strftime("%Y-%m-%d")),
            ]
        )
        return {"won_this_month": count}

    # -- Sales ----------------------------------------------------------

    def _tool_sales_total_this_month(self):
        from datetime import date
        today = date.today()
        first_of_month = today.replace(day=1)
        orders = self.env["sale.order"].search(
            [
                ("state", "in", ["sale", "done"]),
                ("date_order", ">=", first_of_month.strftime("%Y-%m-%d")),
            ]
        )
        total = sum(orders.mapped("amount_untaxed"))
        return {"total_untaxed": round(total, 2), "currency": self.env.company.currency_id.name}

    def _tool_top_customers_by_sales(self, limit=5):
        orders = self.env["sale.order"].search([("state", "in", ["sale", "done"])])
        totals = {}
        for order in orders:
            partner = order.partner_id.name
            totals[partner] = totals.get(partner, 0) + order.amount_untaxed
        ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[:limit]
        return {"top_customers": [{"customer": n, "total": round(t, 2)} for n, t in ranked]}

    def _tool_count_orders_by_stage(self):
        result = {}
        for state, label in self.env["sale.order"]._fields["state"].selection:
            result[label] = self.env["sale.order"].search_count([("state", "=", state)])
        return {"orders_by_stage": result}
