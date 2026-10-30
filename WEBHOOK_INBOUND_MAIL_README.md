# Real-Time Inbound Mail via Gmail Push (Webhook) — Problem, Solution & Roadmap

**Mailbox provider: Gmail (regular @gmail.com account — not Google Workspace).**
Outgoing mail and incoming replies use the **same Gmail mailbox** (currently
accessed via IMAP), which rules out the classic "inbound-parse" webhook model
(SendGrid/Mailgun/Postmark) since that model requires pointing the domain's MX
records at the provider — incompatible with keeping everything inside one
Gmail account. Instead, real-time delivery is achieved via the **Gmail API +
Google Cloud Pub/Sub push notifications**, which is Gmail's native equivalent
of a webhook. This document has been updated to reflect that.

## 1. The Problem

Today, all inbound mail (customer support replies, order-status replies, logistics
queries, marketing bounces, unsubscribe requests) is picked up by Odoo's standard
`fetchmail.server` mechanism, which works like this:

```
IMAP/POP3 mailbox  <---(poll every 5-15 min, cron)---  Odoo (fetch_mail())
```

Key characteristics of this mechanism:

- It is **pull-based**: Odoo has to ask "is there anything new?" on a timer. It
  never finds out about a new email until the next scheduled cron run.
- The poll fetches the **entire mailbox as one batch** — there is no way to
  single out "urgent" messages and fetch only those sooner. Everything in the
  inbox waits for the same cron tick.
- Classification of a message (is this a bounce? an unsubscribe? a reply to an
  order? a support question?) only happens **after** the batch has been
  fetched — it cannot influence *when* the message is retrieved, only what
  happens to it afterward.
- Odoo's fetchmail cron has a practical floor of ~1 minute. Pushing it lower is
  possible but risks IMAP rate-limiting/throttling from providers (Gmail,
  Outlook, etc. flag aggressive polling as abuse).

### Why this matters for us

A customer who replies to a Christmas marketing campaign with "I need to know
about this product" or "where is my order" is functionally indistinguishable,
at the transport level, from a bounce notification or an unsubscribe request —
all of them land in the same inbox and all of them wait for the same cron
cycle. There is currently no way to make support/order/logistics replies
arrive in Odoo faster than bounce/unsubscribe replies, because the bottleneck
(cron-driven IMAP polling) is shared and batch-oriented, not per-message.

We evaluated a "two-tier cron" workaround (fast cron for support/order mailbox,
slow cron for marketing mailbox) and concluded it only helps when order/support
and marketing/bounce mail arrive at genuinely **different mailbox addresses**.
In our case, replies to bulk campaigns go wherever the campaign's `Reply-To`
header points — a single address — so all message types converge on one inbox
regardless. Two crons on the same mailbox is redundant; one fast cron is
equivalent to one webhook in terms of what gets fetched, just slower.

**Conclusion:** the only way to get true real-time (sub-second) inbound mail
processing, independent of any polling interval, is to stop polling and switch
to a **push-based delivery model**. For Gmail specifically, that means the
**Gmail API + Google Cloud Pub/Sub push notifications**, not a classic
inbound-parse webhook.

## 2. The Solution: Gmail API + Cloud Pub/Sub Push

### 2.1 How it works

Gmail has no concept of "POST the email to a URL" the way SendGrid/Mailgun do.
Instead, Gmail lets you **subscribe to mailbox change events** via its API,
and have those events delivered through Google Cloud Pub/Sub, which then
pushes to an HTTP endpoint we control — the net effect is the same as a
webhook, achieved differently:

```
Sender replies ---> Gmail mailbox (new message arrives)
                         |
                         v
             Gmail API "watch" (registered on this mailbox)
                         |  (mailbox change detected)
                         v
             Google Cloud Pub/Sub topic  ---(HTTP push, instant)--->  Odoo webhook controller
                                                                              |
                                                        Gmail API history.list / messages.get
                                                        (fetch the actual new message content)
                                                                              |
                                                                       message_process()
```

Step by step:
1. Odoo calls Gmail API `users.watch()` on the mailbox once, telling Google:
   "notify this Pub/Sub topic whenever this mailbox changes." Google returns a
   starting `historyId` (a checkpoint marker).
2. When a new email arrives, Google detects the mailbox change and publishes a
   tiny notification message to the Pub/Sub topic — **this notification does
   NOT contain the email itself**, only the mailbox's new `historyId`.
3. Pub/Sub immediately delivers that notification via HTTP POST to Odoo's
   webhook controller (this is the "push subscription" — the actual webhook
   endpoint).
4. Odoo's controller receives the POST, decodes the Pub/Sub envelope, and
   calls Gmail API `history.list(startHistoryId=<last known id>)` to find out
   exactly what changed, then `messages.get()` to fetch the new message's
   full content.
5. That content is converted into the same internal email-dictionary format
   Odoo's fetchmail already produces, and passed into `message_process()` —
   the exact same function fetchmail calls, just triggered by a push event
   instead of a cron tick.
6. From that point on, **all existing classification logic is reused
   unchanged** (bounce/unsubscribe/reply/order/support detection in
   `marketing_mail_gateway`'s `_mmg_classify()` and related overrides in
   `mail_thread.py`). This mechanism only changes *how fast the message gets
   into Odoo* — not what happens to it once it's there.

### 2.2 Why Gmail needs this extra step (unlike a typical webhook)

With SendGrid/Mailgun-style inbound-parse, the provider hands you the full
email content directly in the webhook POST — one step. With Gmail, the push
notification is deliberately lightweight (just a change marker) for privacy
and security reasons, so Odoo must make a follow-up API call to actually
retrieve the message. This means the webhook controller depends on the Gmail
API being reachable at push time, not just on receiving the POST.

### 2.3 Authentication note (regular Gmail, not Workspace)

Because this is a personal **@gmail.com** account rather than a Google
Workspace domain, there is no domain-wide delegation / service-account
shortcut available. Access must go through **OAuth2** with the mailbox
owner's one-time consent:
- Create OAuth2 credentials (Client ID/Secret) in the Google Cloud project.
- The mailbox owner authorizes Odoo once via Google's consent screen.
- Odoo stores and auto-refreshes the resulting access/refresh token pair to
  keep making Gmail API calls (`watch()`, `history.list`, `messages.get`)
  without repeated manual logins.

### 2.2 What does NOT need to change

- **UI live-update behavior is already solved.** Once a `mail.message` record
  is created in Odoo — whether by cron fetch or webhook — Odoo's existing
  `bus.bus` real-time notification system pushes it to open browser sessions
  automatically (same mechanism behind Discuss and live chatter updates). The
  webhook does not need to "tell the UI" anything directly; it only needs to
  get the message into the database as fast as possible, and Odoo's bus
  system does the rest.
- **Message classification logic** (bounce/unsubscribe/reply detection,
  keyword matching, thread/reference matching against existing
  orders/tickets) is provider-agnostic and reusable as-is.

### 2.4 What DOES need to be built

**Manual setup (Google Cloud Console — one-time, done by a human, not code):**
1. Create a Google Cloud project.
2. Enable the **Gmail API** and **Cloud Pub/Sub API**.
3. Create a Pub/Sub topic (e.g. `gmail-inbound-notify`) and a **push
   subscription** on it pointing at Odoo's public webhook URL.
4. Grant the special Gmail push service account
   (`gmail-api-push@system.gserviceaccount.com`) publish rights on that
   topic — this is Google's documented requirement for Gmail to be allowed to
   publish to it.
5. Create OAuth2 Client ID/Secret credentials and complete the one-time
   consent flow as the mailbox owner.
6. Ensure Odoo is reachable via a public HTTPS URL (Pub/Sub push cannot
   deliver to `localhost` or an internal-only address).

**Code to build (Odoo side):**
1. **OAuth2 token storage/refresh** for the Gmail account (store access +
   refresh token securely, auto-refresh before expiry).
2. **`watch()` registration call** — run once at setup and re-run on a
   renewal cron (see below), storing the returned `historyId`.
3. **Renewal cron** — Gmail's `watch()` registration expires after **7 days
   maximum**; a lightweight scheduled job must re-call `watch()` before
   expiry. This cron does no mail-fetching itself, only keeps the
   subscription alive.
4. **Webhook controller** (`/gmail/webhook` or similar) to receive Pub/Sub's
   push POST:
   - Verify the request is genuinely from Pub/Sub (e.g. verifying the OIDC
     token Pub/Sub push subscriptions can be configured to attach, or an
     endpoint secret/token in the URL) to prevent spoofed calls.
   - Decode the base64-encoded Pub/Sub message envelope to get the new
     `historyId`.
5. **History-diff + fetch logic** — call `history.list(startHistoryId=...)`
   to find new message IDs, then `messages.get()` to retrieve full content,
   converting Gmail API's message format into Odoo's internal email
   dictionary format (same shape fetchmail already produces).
6. **Hand off to `message_process()`** — same entry point fetchmail uses
   today, so all existing classification is reused unchanged.
7. **Routing rules** to determine which model/thread a new message belongs to
   (reused from existing classification, extended if needed):
   - Match `References`/`In-Reply-To` headers → routes replies to the
     existing `sale.order` / `helpdesk.ticket` / campaign thread they belong
     to.
   - Keyword/subject fallback → for messages that don't match a thread,
     classify by content ("order", "invoice", "refund" → sales; "issue",
     "broken", "help" → support).
   - (Multi-mailbox `To`-address routing is not applicable here since
     everything shares one Gmail address — see Future Scope if that changes.)

## 3. Migration Plan

| Phase | Action | Cron/Push state |
|---|---|---|
| 0 (current) | All mail via `fetchmail.server` IMAP polling, single 5-15 min cron | Cron only |
| 1 | Set up GCP project, Gmail API, Pub/Sub topic/subscription, OAuth2 consent; build & test webhook controller against a staging Pub/Sub subscription | Cron (prod) + Push (staging) |
| 2 | Register `watch()` on the live mailbox, cut inbound processing over to the Pub/Sub push path; keep `fetchmail.server` cron running as a fallback/safety net at a longer interval (e.g. 15-30 min) in case push notifications are ever missed | Push (primary) + Cron (fallback) |
| 3 | Deploy the 7-day `watch()` renewal cron; monitor for missed messages, expired watches, OAuth token refresh failures | — |
| 4 | Once stable, decide whether the fallback IMAP cron is still needed or can be lengthened further | Push (primary), Cron (optional) |

We are **not** removing the cron/fetchmail mechanism outright at first — it
becomes a low-frequency safety net so that a push-notification outage or an
expired `watch()` registration doesn't mean lost mail, only delayed mail
(falls back to old behavior).

## 4. Risks & Considerations

- **Security:** the webhook endpoint is a public HTTP endpoint. It must
  verify the request genuinely comes from our Pub/Sub subscription (e.g. an
  OIDC token check or a secret token embedded in the endpoint URL),
  otherwise anyone could POST a fake notification and trigger Odoo to pull
  from the Gmail API unexpectedly.
- **OAuth2 token lifecycle:** since this is a regular Gmail account (not
  Workspace), there's no service-account shortcut — the refresh token must be
  stored securely and monitored; if the mailbox owner revokes access or the
  refresh token becomes invalid, push notifications silently stop working
  until re-authorized.
- **7-day `watch()` expiry:** Gmail's push subscription is not permanent —
  it must be renewed at least every 7 days via a scheduled job, or the
  mailbox silently reverts to receiving no push notifications at all (with no
  error surfaced unless the renewal cron itself is monitored).
- **Public HTTPS requirement:** Pub/Sub push requires a real internet-facing
  HTTPS endpoint for Odoo — if Odoo is currently only reachable internally,
  this requires exposing it (reverse proxy, domain, SSL cert) before this can
  work at all.
- **Notification-only payload:** the Pub/Sub push message itself contains no
  email content, only a history marker — every notification triggers at
  least one additional Gmail API round-trip (`history.list` then
  `messages.get`), so a webhook failure at that follow-up step still means a
  missed message even though the push arrived successfully.
- **Duplicate processing:** if both the fallback cron and the push path could
  process the same message, dedup logic (matching Message-Id) must ensure a
  message isn't processed twice.

## 5. Future Scope

- **Priority queuing:** once push-driven ingestion is in place, introduce a
  lightweight priority queue so a burst of inbound mail (e.g. right after a
  bulk campaign send) doesn't process order/support messages in strict
  arrival order but rather by classified urgency.
- **Move to Google Workspace:** if the business later migrates this mailbox
  to a Google Workspace domain, domain-wide delegation becomes available,
  removing the need for manual OAuth2 re-consent and simplifying the
  service-account auth story.
- **Multi-mailbox routing:** if the business later adopts separate addresses
  instead of one shared Gmail inbox, extend the setup with a `watch()` +
  webhook pairing per mailbox, routed based on the `To` address.
- **SLA-based escalation:** combine real-time ingestion with automatic
  escalation (e.g. if a support-classified message isn't acknowledged within
  X minutes, escalate to a manager or trigger a notification).
- **Analytics on response latency:** since ingestion is now event-timestamped
  precisely (push receipt time vs. old cron-batch time), build a dashboard
  measuring actual time-to-first-response for support/order replies —
  something the old cron-batch model couldn't measure meaningfully.
- **Watch-health monitoring:** add alerting if the 7-day renewal cron fails
  or if Pub/Sub push notifications stop arriving unexpectedly, so a silent
  outage doesn't quietly degrade back to zero real-time updates.

## 6. Summary

| | Cron (current) | Gmail Push (target) |
|---|---|---|
| Trigger | Odoo polls IMAP on a timer | Gmail notifies Pub/Sub on mailbox change |
| Latency | Up to cron interval (5-15 min, or ~1 min if tightened) | Near-instant (plus one Gmail API round-trip) |
| Batch vs per-message | Whole mailbox fetched together | Each change delivered as it happens |
| Classification logic | Unchanged — runs after fetch | Unchanged — runs after receipt |
| UI live update | Already automatic via `bus.bus` | Already automatic via `bus.bus` |
| Infra changes needed | None (already running) | GCP project, Pub/Sub, OAuth2, public HTTPS endpoint, new controller |
| Maintenance overhead | None beyond existing cron | 7-day `watch()` renewal cron, OAuth token refresh monitoring |
| Failure mode | Delayed mail until next cron | Needs cron fallback for safety; silent failure risk if renewal/token lapses |
