here in# Real-Time Communication Patterns — Where Each One Applies in This App

Six patterns evaluated: **WebSockets, Webhooks, Long Polling, Short Polling,
Server-Sent Events (SSE), Cron Jobs.** This document maps each to the specific
module/file in this repo where it's already used, or where it should be added,
with the reasoning for the choice.

---

## 1. Quick definitions

| Pattern | Direction | Shape |
|---|---|---|
| **WebSocket** | Bidirectional, persistent | One open connection, either side can push anytime. Best for chat/live collaboration. |
| **Webhook** | Server → server, event-driven | External service calls *our* URL the instant something happens. No connection held open between events. |
| **Long Polling** | Client → server, held open | Client asks "anything new?"; server holds the request open until there's an answer (or timeout), then client immediately re-asks. Fallback when a websocket can't be established. |
| **Short Polling** | Client → server, fixed interval | Client asks "anything new?" every N seconds regardless of whether there's anything new. Simple, wasteful at scale, fine for low-frequency checks. |
| **SSE** | Server → client, persistent, one-way | Server streams events/text over a single HTTP connection as they happen. Simpler than websocket when the client never needs to send data back over the same channel. |
| **Cron Job** | Scheduled, no live connection | Runs on a timer regardless of whether anything changed. Right tool when "instant" isn't required. |

---

## 2. Module × Pattern matrix

✅ = already built · 🔶 = recommended, not yet built · — = not applicable

| Module / Feature | WebSocket | Webhook | Long Polling | Short Polling | SSE | Cron |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| `llm_sales_chat` — AI chat widget | — | — | — | — | 🔶 | — |
| `gmail_webhook_gateway` — inbound Gmail | — | ✅ | — | — | — | ✅ (renewal + fallback) |
| `marketing_mail_gateway` — mail classification | — | fed by ✅ | — | — | — | ✅ |
| `mail_inbox_classifier` | — | fed by ✅ | — | — | — | ✅ |
| `sms_twilio` — SMS send & status | 🔶 (via `bus.bus`) | ✅ (status callback) | — | — | — | 🔶 (optional reconciliation) |
| `payment_stripe_custom` — payment gateway | — | ✅ | — | 🔶 (checkout wait) | — | 🔶 (reconciliation) |
| `website_sale_affiliate*` — affiliate tracking | — | 🔶 (only if external network added) | — | 🔶 (portal dashboard) | — | 🔶 (commission/payout) |
| `sale_snailmail` — physical letters | — | — | — | — | — | ✅ |
| Mass mailing (`mass_mailing`) | — | 🔶 (future ESP events) | — | — | — | ✅ (queue) |
| Discuss / chatter / live notifications | ✅ (`bus.bus`) | — | ✅ (automatic fallback) | — | — | — |

---

## 3. Module-by-module mapping

### `llm_sales_chat` — AI sales chat widget
**File:** `addons/llm_sales_chat/controllers/main.py` (`/llm_chat/ask`, currently `type="json"`, plain request/response)

| Pattern | Verdict |
|---|---|
| **SSE** | **Recommended addition.** Stream the LLM's answer token-by-token (Groq supports streaming) instead of the current single blocking response — standard for AI chat UX, and one-directional so SSE is a better fit than a websocket. |
| WebSocket | Only worth it later if adding live typing indicators or human-agent takeover mid-conversation. Not needed for single-user Q&A today. |
| Short/Long Polling | Not applicable — the user explicitly triggers each question; nothing to poll for between messages. |
| Webhook | Not applicable — nothing external calls into this feature. |
| Cron | Not applicable to the chat itself (rate-limit bucket in `_RATE_LIMIT` is in-memory, no scheduled job needed). |

### `gmail_webhook_gateway` — real-time inbound Gmail
**Files:** `addons/gmail_webhook_gateway/controllers/main.py`, `models/gmail_webhook_account.py`

| Pattern | Verdict |
|---|---|
| **Webhook** | **Primary mechanism, already built.** Gmail API `watch()` + Google Cloud Pub/Sub push → `/gmail_webhook_gateway/webhook/<token>`. |
| **Cron** | **Two required jobs:** (1) renew the `watch()` registration before its 7-day expiry, (2) fallback IMAP poll (`fetchmail.server`, 15–30 min) in case a push notification is ever missed. |
| SSE/WebSocket/Polling | Not applicable — server-to-server, not a browser-facing live feed. |

### `marketing_mail_gateway` — inbound mail classification (bounce/unsubscribe/reply/order/support)
**Files:** `addons/marketing_mail_gateway/models/fetchmail_server.py`, `mailing.py`, `mail_thread.py`, `marketing_inbound_mail.py`

| Pattern | Verdict |
|---|---|
| **Cron** | Drives both the mail-queue processing and the fallback fetch cycle; classification logic itself is trigger-agnostic (runs the same whether fed by webhook or cron). |
| **Webhook** (indirect) | Benefits from `gmail_webhook_gateway`'s webhook — faster classification of support/order replies once push is the primary path (see Phase 2 of the webhook README). |

### `mail_inbox_classifier`
**File:** `addons/mail_inbox_classifier/models/mail_inbox_message.py`

| Pattern | Verdict |
|---|---|
| **Cron / Webhook-fed** | Same as `marketing_mail_gateway` — consumes whatever produced the `mail.message`, doesn't need its own trigger mechanism. |

### `sms_twilio` — SMS sending & delivery tracking
**Files:** `addons/sms_twilio/controllers/controllers.py` (`/sms_twilio/status/<uuid>`), `models/sms_tracker.py`, `sms_sms.py`

| Pattern | Verdict |
|---|---|
| **Webhook** | **Already built.** Twilio POSTs delivery status changes (queued → sent → delivered/failed) to `/sms_twilio/status/<uuid>`. |
| **WebSocket** (via Odoo's `bus.bus`) | Recommended if an agent-facing SMS composer/tracker view should show delivery status update live instead of requiring a manual refresh — push the status change through `bus.bus` the moment the webhook lands. |
| **Cron** (optional) | Low-priority reconciliation job comparing Twilio's message list against local `sms.sms`/`sms.tracker` records, to catch anything a missed webhook call left stale. |
| Short/Long Polling | Not needed — webhook + bus push covers it. |

### `payment_stripe_custom` — payment gateway
**Files:** `addons/payment_stripe_custom/controllers/main.py`, `models/payment_stripe_settings.py`

| Pattern | Verdict |
|---|---|
| **Webhook** | **Required, primary.** Stripe events (`payment_intent.succeeded`, `charge.refunded`, `charge.dispute.created`, etc.) must drive order confirmation — never trust the browser redirect alone, since a customer can close the tab mid-flow. |
| **Short Polling** | Client-side, bounded (e.g. every 2s, capped ~15s) on the checkout success page while waiting for the webhook to confirm — bridges the redirect-to-webhook lag. |
| **Cron** | Reconciliation job: periodically diff Stripe's transaction list against local `payment.transaction` records to catch any webhook that never arrived (endpoint downtime, network blip). Standard defensive pattern for payment integrations. |
| WebSocket/SSE/Long Polling | Not needed — payment confirmation is infrequent, doesn't justify a persistent connection. |

### `website_sale_affiliate` / `website_sale_affiliate_custom` — affiliate/referral tracking
**Files:** `addons/website_sale_affiliate/controllers/main.py`, `ir_http.py`; `website_sale_affiliate_custom/models/affiliate_click.py`, `affiliate_commission.py`, `affiliate_withdrawal.py`, `controllers/portal.py`

| Pattern | Verdict |
|---|---|
| **Cron** | Recommended for commission calculation and payout-eligibility (e.g. nightly job computing commissions from confirmed/paid orders, flagging withdrawals ready for payout) — doesn't need to be real-time. |
| **Short Polling** | The affiliate's portal earnings dashboard (`portal.py`) can refresh every 30–60s — earnings don't change second-to-second, so this is enough. |
| Webhook | Only relevant if integrating an external affiliate network later (their conversion postbacks would arrive as a webhook). |
| Click capture itself (`affiliate_click.py`) | Plain synchronous HTTP request/redirect — not a fit for any of these six patterns. |

### `sale_snailmail` — physical letter sending
**Files:** `addons/sale_snailmail/models/sale_order.py`, `controllers/portal.py`

| Pattern | Verdict |
|---|---|
| **Cron only.** | Uses Odoo's built-in `snailmail` module's scheduled job to queue/send letters. No real-time component. |

### Mass mailing (`mass_mailing`, stock Odoo)

| Pattern | Verdict |
|---|---|
| **Cron** | "Mail Marketing: Process queue" job — keep its interval sane (1 minute, not the 1/day misconfiguration that caused the incident in `MASS_MAILING_INCIDENT_LOG.md`). |
| **Webhook** (future) | If marketing volume moves to Brevo/SES (per `EMAIL_DOMAIN_MIGRATION_README.md`), their delivery/open/click/bounce events should arrive as webhooks instead of relying solely on Odoo's own tracking pixel (per `EMAIL_OPEN_CLICK_TRACKING_README.md` Option B). |

### Discuss / chatter / live UI notifications — stock Odoo, already running

| Pattern | Verdict |
|---|---|
| **WebSocket (primary), Long Polling (automatic fallback)** | Odoo's `bus.bus` already does this — a persistent websocket pushes new chatter messages, Discuss chat, and live view updates to open browser sessions, transparently falling back to long polling if a websocket can't be established (proxy/firewall issues). Any module that creates a `mail.message` or wants to push a live update should route through `bus.bus` rather than building a new channel — this is why inbound mail from `gmail_webhook_gateway` already shows up live in Discuss with zero extra work. |
| **Production note** | Once deployed off the local machine, confirm the reverse proxy (nginx or equivalent) is configured to pass through websocket `Upgrade`/`Connection` headers — otherwise every session silently degrades to long polling. |

---

## 4. Summary table (with build status detail)

| Module / Feature | Pattern(s) | Status |
|---|---|---|
| `llm_sales_chat` | SSE | Recommended, not yet built |
| `gmail_webhook_gateway` | Webhook (primary) + Cron (renewal + fallback) | Built |
| `marketing_mail_gateway` / `mail_inbox_classifier` | Cron (queue/fetch), fed by webhook | Built |
| `sms_twilio` | Webhook (status callback) + WebSocket via `bus.bus` (recommended) + Cron (optional reconciliation) | Webhook built; live UI push not yet done |
| `payment_stripe_custom` | Webhook (primary) + Short Polling (checkout wait) + Cron (reconciliation) | Webhook scaffolded; polling/reconciliation not yet done |
| `website_sale_affiliate*` | Cron (commission/payout) + Short Polling (dashboard) | Not yet built |
| `sale_snailmail` | Cron only | Built (via stock `snailmail`) |
| Mass mailing | Cron (queue) + Webhook (future ESP events) | Cron built; webhook is future work |
| Discuss / chatter / live notifications | WebSocket + Long Polling fallback | Built into Odoo core |

**Not needed anywhere as a primary mechanism:** long polling — it only belongs as
`bus.bus`'s automatic fallback when a websocket can't be established, never as a
deliberate first choice; anything that looks like it needs long polling is
better served by a webhook (event exists externally) or SSE (event exists
server-side and needs streaming to the browser).
