# Marketing Mail Gateway — Explained Simply

## What problem does this solve?

When you send marketing emails (newsletters, campaigns), people reply to them,
their emails bounce back, or they ask to be unsubscribed. Normally, all of
that just lands in an inbox and nobody in Odoo knows about it.

This addon connects a real mailbox (like `marketing@yourcompany.com`) to Odoo
so that every reply, bounce, or unsubscribe request is automatically read,
understood, and linked to the right campaign, contact, or CRM lead — without
touching any of Odoo's original code.

## What did I actually build?

A new custom app folder: `addons/marketing_mail_gateway/`. Nothing inside
Odoo's own `mail`, `mass_mailing`, or `crm` apps was changed — this addon
just "plugs into" them the way Odoo is designed to be extended.

In plain terms, it does 4 things:

1. **Lets you mark a mailbox as "Marketing"**
   Odoo already has a screen (Settings → Technical → Incoming Mail Servers)
   where you type in your IMAP/POP3 email and password so Odoo can fetch
   mail from it. I added one checkbox there: **"Marketing Mailbox"**. Ticking
   it tells this addon "watch this inbox closely."

2. **Reads and understands every incoming email**
   Every time Odoo checks that mailbox (it already does this automatically,
   on a timer), each email is sorted into one of 4 buckets:
   - **Reply** — a real person replied to a campaign
   - **Bounce** — the email address didn't exist / delivery failed
   - **Unsubscribe request** — someone asked to stop receiving emails
   - **Other** — anything else

   It figures this out by checking things like: does the email look like a
   delivery-failure message, does it contain an "unsubscribe" style header
   or the word "unsubscribe" in the text, and can it be traced back (via the
   email's own internal reference numbers) to a campaign Odoo actually sent.

3. **Connects it to the right person and campaign automatically**
   If the email is a reply to a campaign, this addon traces it back to:
   - the **Campaign** it belongs to
   - the **Contact** (or **CRM Lead**) who replied
   - the specific **Mailing** that was sent

   So instead of a message sitting in a random inbox, you can see in Odoo:
   "This lead replied to this campaign."

4. **Takes action automatically**
   - Bounce → marks that send attempt as "Bounced" on the campaign stats
   - Unsubscribe → removes that person from the mailing list, and adds their
     email to Odoo's global "do not email" blocklist
   - Reply → posts a note on the related CRM lead so the salesperson sees it

Every single email processed is also saved into a new logbook you can browse
in Odoo: **Email Marketing → Inbound Mail Log**. Nothing is silently dropped;
if something can't be classified or linked, it's saved with an "Error" status
and an hourly background job automatically retries it.

## Where do I find it in Odoo?

- **Settings → Technical → Incoming Mail Servers** — set up your mailbox here
  (same screen Odoo has always had), and tick "Marketing Mailbox".
- **Email Marketing → Inbound Mail Log** (new menu) — see every email that
  came in, what it was classified as, and what it got linked to.

## What happens after this is installed? Step by step.

1. **You install the app.** In Odoo: Apps → search "Marketing Mail Gateway" →
   Install. (Or from command line with `-i marketing_mail_gateway` — this is
   what I'd run for you next, if you want.)

2. **A new checkbox and a new menu appear.** Nothing else changes in the
   interface — no existing screens are altered, no data is deleted.

3. **You configure a mailbox.** You'll need real IMAP login details for a
   mailbox (e.g. Gmail with an app password, or your company mail server) —
   host, port, username, password. Tick "Marketing Mailbox". Save, then click
   "Test & Confirm" to make sure Odoo can log in.

4. **Odoo starts checking that mailbox automatically**, using its existing
   built-in scheduler (this already runs periodically for any confirmed mail
   server — I didn't need to add a separate one).

5. **From then on, every new email in that mailbox gets processed**: read,
   classified, linked, and logged — with no manual work needed. You'll see
   entries pile up in **Inbound Mail Log** as replies/bounces/unsubscribes
   come in.

6. **You can review results anytime**: filter the log by "Bounces",
   "Unsubscribe Requests", or "Replies"; click into one to see who it's
   linked to and the original email content.

## What do YOU need to do before this works for real?

- Give it a real mailbox to watch (IMAP username/password). Nothing works
  until this is configured — right now it's just code sitting ready.
- Decide whether you want a dedicated "Create a New Record" target — I set
  it up so unmatched emails (not clearly tied to any existing lead/campaign)
  get saved as a new "Inbound Mail" record instead of vanishing, but you
  need to select that model on the mail server form the first time.
- Optionally review/adjust the unsubscribe keyword list (I set sensible
  defaults like "unsubscribe", "opt out", "remove me", etc. in English and
  French) to match your audience's language.

## What did I NOT do (so there's no surprise later)?

- I did not send a test email or connect to a real mailbox — I don't have
  live email credentials, so this hasn't been tested against a real inbox.
- I could not run Odoo's automated test suite in this environment because
  the local database here has an unrelated technical problem (a Postgres
  configuration issue, nothing to do with this addon). I wrote 5 automated
  tests covering replies, bounces, unsubscribes, duplicates, and non-marketing
  mailboxes being ignored — they should be run once you have a working
  database, before trusting this in production.
- I did not touch any existing Odoo files — this is a fully separate,
  removable addon. Uninstalling it won't affect your existing mail, CRM, or
  mass mailing data.

## Bottom line

Before: replies/bounces/unsubscribes to marketing emails just sit in an
inbox, invisible to Odoo.

After: Odoo watches that inbox, reads every message, works out what kind of
message it is, connects it to the right campaign/contact/lead, takes the
correct automatic action (bounce logging, unsubscribing, notifying sales),
and keeps a full audit trail — all without any manual sorting.
