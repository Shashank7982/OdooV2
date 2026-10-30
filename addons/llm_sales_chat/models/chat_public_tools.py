from odoo import models

# ---------------------------------------------------------------------------
# PUBLIC TOOL SCHEMA — these are the ONLY tools reachable from the public
# website endpoint. Deliberately excludes anything from chat_tools.py
# (leads, sales totals, top customers) — that set stays internal-only.
# ---------------------------------------------------------------------------
PUBLIC_TOOL_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search published products/services on the website by "
                            "name or keyword. Returns name, price, and short description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "limit": {"type": "integer", "description": "Max results, default 5"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get full details (price, description) for a specific "
                            "published product by exact or close name match.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_product_categories",
            "description": "List the published product categories available on the website.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


class ChatPublicTools(models.AbstractModel):
    """Executes ONLY public-safe lookups. Every query below is explicitly
    filtered to website_published=True so nothing internal/unpublished can
    leak to anonymous visitors, regardless of what the LLM is asked."""

    _name = "llm.chat.public.tools"
    _description = "Public Website Chat Tools"

    def execute(self, name, arguments):
        handler = getattr(self, f"_tool_{name}", None)
        if not handler:
            return {"error": f"Unknown tool: {name}"}
        return handler(**(arguments or {}))

    def _published_products(self):
        # sudo() is required since anonymous visitors have no product read
        # access by default — but every query here is hard-filtered to
        # website_published=True, so only public catalog data is reachable.
        return self.env["product.template"].sudo().search(
            [("website_published", "=", True), ("sale_ok", "=", True)]
        )

    def _tool_search_products(self, query, limit=5):
        products = self._published_products().filtered(
            lambda p: query.lower() in (p.name or "").lower()
            or query.lower() in (p.description_sale or "").lower()
        )[: max(1, min(limit, 20))]
        return {
            "results": [
                {
                    "name": p.name,
                    "price": p.list_price,
                    "currency": p.currency_id.name,
                    "description": (p.description_sale or "")[:200],
                }
                for p in products
            ]
        }

    def _tool_get_product_details(self, name):
        product = self._published_products().filtered(
            lambda p: name.lower() in (p.name or "").lower()
        )[:1]
        if not product:
            return {"found": False}
        p = product[0]
        return {
            "found": True,
            "name": p.name,
            "price": p.list_price,
            "currency": p.currency_id.name,
            "description": p.description_sale or "",
        }

    def _tool_list_product_categories(self):
        categories = self._published_products().mapped("public_categ_ids.name")
        return {"categories": sorted(set(filter(None, categories)))}
