# LLM Sales & CRM Chat (Groq)

A minimal custom Odoo 18 addon: ask natural-language questions about your
Sales & CRM data, answered by a Groq-hosted LLM using a small, safe set of
ORM-backed tools (no raw SQL, no arbitrary queries from the model).

## Install

1. Copy this folder into your Odoo addons path:
   ```
   cp -r llm_sales_chat /path/to/your/odoo/addons/
   ```
2. Restart Odoo.
3. Go to **Apps**, remove the "Apps" filter, search "LLM Sales & CRM Chat", click Install.

## Configure

1. Get a free API key at https://console.groq.com
2. In Odoo: **Settings > General Settings**, scroll to **LLM Sales Chat**.
3. Paste your Groq API key. Default model is `llama-3.3-70b-versatile`
   (good balance of speed and tool-calling accuracy) — change if you like.
4. Save.

## Use

Go to **Sales > AI Chat Assistant**, type a question, click Ask. Examples:
- "How many open leads do we have?"
- "What's our total sales this month?"
- "Who are our top 5 customers?"
- "How many orders are in each stage?"

## Extending

All data access goes through `models/chat_tools.py`. To add a new capability:

1. Add an entry to `TOOL_SCHEMA` describing the tool (name, description, parameters)
   in OpenAI function-calling format — this is what the LLM reads to decide when
   to call it.
2. Add a matching `_tool_<name>(self, **kwargs)` method on `ChatTools` that runs
   a safe ORM query (`search_count`, `search_read`, aggregates, etc.) and returns
   a small JSON-serializable dict.

Never let the LLM construct the domain/filter itself from free text — always
give it a small number of specific, named tools like the examples here. This
keeps a wrong or hallucinated tool call harmless (worst case: wrong tool run,
not a destructive query).

## Public website chat widget

A floating chat bubble appears on every website page (bottom-right). It calls
a separate, public-safe endpoint (`/llm_chat/ask`) that ONLY has access to
**published product/catalog data** — it cannot see leads, sales totals,
customers, or any other internal figures. That separation is enforced in
code (`models/chat_public_tools.py`, `PUBLIC_TOOL_SCHEMA`), not just by
prompting — even if someone tries to trick the LLM into asking for internal
numbers, the tools simply don't exist on that endpoint.

Notes on the public endpoint:
- `auth="public"` — reachable by anonymous visitors, no login required.
- A basic in-memory rate limiter caps requests per session (10 / 60s) to
  reduce abuse and API cost. For real production traffic, put a proper
  rate limiter in front (nginx, Cloudflare, etc.) — the in-memory one won't
  survive multiple workers/restarts.
- Every tool query is hard-filtered to `website_published = True`, so
  unpublished/draft products can't leak even via `sudo()`.
- Errors are caught and never shown to the visitor — logs go server-side only.

If you later want the widget to also help **logged-in employees** with
internal data, that needs a second, separate endpoint with `auth="user"`
(not the public one) — ask and I'll add it as its own route so the two
never share a code path by accident.

## Notes

- Uses Groq's OpenAI-compatible `/chat/completions` endpoint, so swapping
  `models/groq_client.py` to point at Ollama or any other OpenAI-compatible
  API later is a small, isolated change — nothing else in the module needs
  to change.
- Access to `llm.chat.wizard` is currently open to `base.group_user`
  (all internal users). Restrict via `security/ir.model.access.csv` and/or
  record rules if you want to limit who can query.
- The `requests` Python package is required — Odoo ships with it by default,
  but if missing: `pip install requests`.
