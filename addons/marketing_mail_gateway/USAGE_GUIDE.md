# Marketing Mail Gateway — Full Usage Guide

This guide walks through setting up **sending (SMTP)** and **receiving (IMAP)**
mail on the same mailbox, sending a campaign, and watching replies /
bounces / unsubscribes show up automatically in Odoo's log.

---

## 0. Before you start

You need **one real mailbox** that will act as both the "From" address for
campaigns and the inbox this addon watches for replies. Using two different
addresses will break reply detection — see [Why one mailbox?](#why-one-mailbox)
below.

This guide uses **Gmail** as the example provider since it's the most common,
but the same steps apply to Outlook/Office365 or any provider that offers
SMTP + IMAP (just swap the hostnames).

| | Gmail | Outlook / Office365 |
|---|---|---|
| SMTP host | `smtp.gmail.com` | `smtp.office365.com` |
| SMTP port | `587` (TLS) | `587` (TLS) |
| IMAP host | `imap.gmail.com` | `outlook.office365.com` |
| IMAP port | `993` (SSL) | `993` (SSL) |

**Gmail-specific prerequisite:** Google no longer accepts your normal account
password for SMTP/IMAP logins. You must create an **App Password**:

1. Go to your Google Account → **Security**.
2. Turn on **2-Step Verification** if it isn't already on (required).
3. Go to https://myaccount.google.com/apppasswords → create one (e.g. name it "Odoo").
4. Copy the 16-character code Google shows you (it displays it as 4 blocks
   of 4 with spaces, e.g. `abcd efgh ijkl mnop`).
5. **Remove the spaces** before using it anywhere in Odoo:
   `abcd efgh ijkl mnop` → `abcdefghijklmnop`. This is the #1 cause of
   "invalid credentials" errors.
6. Also make sure IMAP is turned on in Gmail: ⚙️ **Settings** → **See all
   settings** → **Forwarding and POP/IMAP** tab → **Enable IMAP** → Save.

⚠️ **Never paste a real password/app-password into a chat, ticket, or
screenshot.** Treat it like any other credential — if you ever do
accidentally expose one, revoke it and generate a new one immediately.

---

## 1. Set up sending (SMTP — Outgoing Mail Server)

1. Go to **Settings → Technical → Email → Outgoing Mail Servers**.
2. Click **New**.
3. Fill in:
   | Field | Value |
   |---|---|
   | Description | e.g. "Marketing Gmail" |
   | Priority | leave default |
   | SMTP Server | `smtp.gmail.com` |
   | SMTP Port | `587` |
   | Connection Security | `TLS (STARTTLS)` |
   | Username | your full email address, e.g. `marketing@yourdomain.com` |
   | Password | the App Password (no spaces) |
4. Click **Test Connection**. It should say the connection succeeded.
5. Save.

## 2. Set up receiving (IMAP — Incoming Mail Server)

1. Go to **Settings → Technical → Email → Incoming Mail Servers**.
2. Click **New**.
3. Fill in:
   | Field | Value |
   |---|---|
   | Name | e.g. "Marketing Inbox" |
   | Server Type | `IMAP Server` |
   | Server Name | `imap.gmail.com` (**a real hostname, not a label**) |
   | SSL/TLS | ✅ ticked |
   | Port | `993` (auto-fills when SSL is ticked) |
   | Username | the **same** email address as step 1 |
   | Password | the **same** App Password as step 1 |
4. Scroll to **Actions to Perform on Incoming Mails**:
   - **Create a New Record** → select **Marketing Inbound Mail**.
     (This is where unmatched emails — e.g. a fresh unsubscribe request
     that isn't a reply to anything — get saved instead of being dropped.)
5. Tick **Marketing Mailbox** (this addon's field). A warning line appears
   below it — **"Outgoing Mail Server Match"** — confirming it found a
   matching Outgoing Mail Server using the same login. If it warns instead
   of confirming, double check the username matches exactly what you put
   in step 1.
6. Click **Test & Confirm**.
   - ✅ Success → the record's status changes to **Confirmed**, and two new
     buttons appear: **Fetch Now** and **Reset Confirmation**.
   - ❌ "No response received" → wrong hostname or port (see table above).
   - ❌ "Invalid credentials" → password issue (spaces, wrong account,
     IMAP disabled) — see [App Password prerequisite](#0-before-you-start).
7. Save.

### Why one mailbox?

Sending and receiving must be the **same address** because that's how
"replies" are detected at all: when you send a campaign, Odoo puts a unique
tracking ID in the email's headers. When someone replies, their email client
copies that ID back into the reply (`References` / `In-Reply-To` headers).
This addon reads those headers to match the reply back to the original
campaign — but only if the reply *arrives* in the mailbox being watched. If
campaigns go out from `noreply@company.com` but you watch
`marketing@company.com`, replies never reach the inbox this addon reads, and
nothing gets linked. This addon actively defaults new campaigns' Reply-To to
the confirmed Marketing Mailbox address for exactly this reason.

---

## 3. Automatic fetching (how often it checks for new mail)

Once a mail server is Confirmed, Odoo automatically checks it **every 5
minutes** in the background — no extra setup needed. This is a stock Odoo
scheduled job (not something this addon adds), defined in
`addons/mail/data/ir_cron_data.xml`:

```xml
<record id="ir_cron_mail_gateway_action" model="ir.cron">
    <field name="name">Mail: Fetchmail Service</field>
    <field name="interval_number">5</field>
    <field name="interval_type">minutes</field>
</record>
```

You can view/edit this at **Settings → Technical → Automation → Scheduled
Actions** → search "Mail: Fetchmail Service". Lowering the interval makes
testing faster, but avoid going too low on a real Gmail account — you can
hit Google's rate limits.

To check *right now* instead of waiting: open the Incoming Mail Server
record and click **Fetch Now**.

---

## 4. Sending a marketing email

1. Go to **Email Marketing → Mailings**.
2. Click **New**, fill in Subject, Recipients (a mailing list, or any model
   with email addresses — e.g. CRM leads), and the email body.
3. Under the **Reply-To** field: if you've confirmed a Marketing Mailbox
   (step 2 above), this now defaults automatically to that mailbox's
   address — you shouldn't need to touch it.
4. Click **Send** (or **Test** first, to send yourself a preview).

Odoo records a `mailing.trace` for every recipient, containing that unique
tracking Message-ID mentioned above. This is what makes reply/bounce/
unsubscribe matching possible later.

---

## 5. Receiving mail — what happens automatically

Every 5 minutes (or when you click **Fetch Now**), for each new email in the
inbox, this addon:

1. **Reads it** via Odoo's standard mail gateway (`message_process`) — no
   custom email parsing, fully reusing Odoo's built-in IMAP/POP3 handling.
2. **Classifies it** into one of four categories:
   | Category | Detected by |
   |---|---|
   | **Bounce** | Delivery-failure signals (e.g. sender is `mailer-daemon`, or the email is a `multipart/report` delivery status message) |
   | **Unsubscribe Request** | A `List-Unsubscribe` email header, or keywords like "unsubscribe", "opt out", "remove me" in the subject/body (configurable per mailbox) |
   | **Reply** | The email's `References`/`In-Reply-To` header matches a campaign this addon sent, and it wasn't a bounce/unsubscribe |
   | **Other** | Anything that doesn't match the above (e.g. a brand new inbound email, not tied to any campaign) |
3. **Links it** to the originating Campaign, Mass Mailing, Contact, and/or
   CRM Lead, when it can trace the connection.
4. **Takes action**:
   - Bounce → marks that recipient's send attempt as "Bounced" in the
     campaign's own statistics (via Odoo's `mailing.trace`).
   - Unsubscribe → removes the contact from the relevant mailing list, and
     adds their email to Odoo's global "do not email" blocklist
     (**Settings → Technical → Email → Blacklisted Email Addresses**).
   - Reply → posts a note on the linked CRM Lead's chatter so the
     salesperson sees it.
5. **Logs it** — every single message, regardless of category, is saved so
   nothing is silently lost.

---

## 6. Viewing the logs

Go to **Email Marketing → Inbound Mail Log**.

This list shows every email this addon has processed, with columns for:
`From`, `Subject`, `Category` (colored badge), `Status`, `Campaign`,
`Contact`, `Lead`, `Mail Server`.

**Useful filters** (top-right search bar):
- **Replies** / **Bounces** / **Unsubscribe Requests** — filter by category.
- **Errors** — anything that failed to process (see below).
- **Group By → Campaign** — see all inbound mail per campaign at a glance.

**Opening a record** (click any row) shows:
- The full message body (Message Body tab).
- Everything it was linked to (Campaign, Mailing, Trace, Contact, Lead).
- Technical details: Message-Id, In-Reply-To, related document (Technical tab).
- The chatter at the bottom, where any automatic notes (e.g. "reply
  received") are visible.

### Status meanings

| Status | Meaning |
|---|---|
| **New** | Logged but not yet processed (should flip to Processed almost immediately) |
| **Processed** | Classified and any automatic action (blacklist, trace update, lead note) completed successfully |
| **Error** | Something failed while processing (see the Error field on the record for details) |
| **Duplicate** | Same Message-Id already logged — ignored to avoid double-processing |

**Errors auto-retry.** A background job runs every hour and retries any
record stuck in **Error** state — you don't need to do anything manually
unless the same record keeps failing (in which case, check the Error field
for the real cause, e.g. a deleted campaign it tried to reference).

You can also manually force a retry: open the record → click **Retry
Processing** in the header.

---

## 7. End-to-end test checklist

1. ✅ Outgoing Mail Server: Test Connection succeeds.
2. ✅ Incoming Mail Server: Test & Confirm succeeds, Marketing Mailbox
   ticked, "Outgoing Mail Server Match: OK" shown.
3. Send a mailing to a real address you control (e.g. your personal email).
4. From that personal address, **reply** to the campaign email you received.
5. Click **Fetch Now** on the Incoming Mail Server (or wait up to 5 minutes).
6. Open **Email Marketing → Inbound Mail Log** — you should see your reply
   logged, Category = **Reply**, linked to the Campaign and Contact/Lead.
7. Separately, send a plain email to the marketing mailbox with the word
   "unsubscribe" in the subject — after fetching, it should appear with
   Category = **Unsubscribe Request**, and that email should now appear in
   **Settings → Technical → Email → Blacklisted Email Addresses**.
