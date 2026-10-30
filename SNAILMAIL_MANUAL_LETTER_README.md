# Snailmail Letters (Technical Settings) — What to Fill In and How to Find It

This covers the manual "New" form under **Settings → Technical → Email → Snailmail
Letters**, the one that shows Recipient / Model / Document ID / etc. This is the raw,
backend version of the "Send by Post" button — normally Odoo fills every one of these
fields in for you automatically when you click that button on a real document (an
invoice, for example). Filling this form in by hand only makes sense for testing, and
it will only actually work if every field points at something real.

---

## Field by field

### Recipient
The customer (`res.partner`) the letter is physically addressed to. In the
screenshot this is "Acme Corporation, Douglas Fletcher."

**Requirement:** this partner must have a complete postal address — street, city,
zip, and country. If any of those are missing, the send will fail with
`MISSING_REQUIRED_FIELDS` (this is enforced in code by `_is_valid_address()`, which
checks exactly those four fields).

**How to check/fix:** open **Contacts**, find the partner, and make sure the address
block is fully filled in.

### Sent by
Read-only. Whoever is logged in and creating the record — filled in automatically,
nothing to type here.

### Information
A free-text/HTML field Odoo uses to show status messages back to you (e.g. "sent
successfully," or an error like "not enough credits"). It's not an input for you to
write a message into for the letter — the "Hello Maam" text currently in it isn't
part of the actual letter content, it's just been typed into a status field. Leave
this blank when creating a new one; Odoo will populate it after a send attempt.

### Model
The **technical name** of the record type this letter is about — not the model's
display label. `test` (as in the screenshot) isn't a real model, which is exactly why
this record can't work: Odoo has nothing to load from `res_id = 1` under a model that
doesn't exist.

**How to find the correct value:**
1. Turn on developer mode (**Settings → General Settings → scroll to bottom →
   Activate the developer mode**).
2. Open the actual record you want to send by post (e.g. a specific customer
   invoice, under **Accounting → Customers → Invoices**).
3. Click the **bug icon** in the top right (developer tools menu) → **View Fields**
   or **Edit Action** — either shows the technical model name at the top (for an
   invoice this is `account.move`).

Common examples: customer invoice → `account.move`, sales order → `sale.order`,
contact → `res.partner`.

### Document ID
The **numeric database ID** of that one specific record — not a name, not a
reference number you see on screen (like "INV/2026/0001"), the literal internal ID.

**How to find it:** with developer mode on, open the record, then either:
- Look at the browser URL — it contains something like `...&id=42`, that number is it.
- Or click the bug icon → **View Fields**, the ID is shown there too.

### Color / Both side
These are just print options (color vs. black-and-white, single-sided vs.
double-sided). Safe to leave at whatever default, no lookup needed.

### Document (attachment)
Empty until you actually attempt the send — Odoo generates the PDF itself at send
time from the Model + Document ID you gave it (via the report template tied to that
model). You don't upload anything here manually.

---

## Why "Send Now" will fail as currently filled

With `Model = test` and `Document ID = 1`, there is no real record for Odoo to pull
data from or generate a report for — clicking **Send Now** will error out (most
likely `ATTACHMENT_ERROR` or `MISSING_REQUIRED_FIELDS`), because step one of the
whole process (generating the PDF from a real document) has nothing valid to work
from.

## Recommended way to actually test this

Skip this manual form entirely and use the real flow instead:
1. Open a posted customer invoice with a complete address on the customer.
2. In its chatter, use **Send** → **Send by Post**.
3. Odoo creates the exact same kind of record you're looking at now, but with every
   field — Model, Document ID, Recipient, Report Template — filled in correctly for
   you automatically.

This manual Technical Settings form is really meant for developers debugging the
snailmail flow with known-good values, not a data-entry screen for everyday use.
