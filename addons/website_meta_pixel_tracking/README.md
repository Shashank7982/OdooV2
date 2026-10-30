pixel id is a code that meta gives
# Meta Pixel Tracking — Odoo 18 Addon

Custom addon that installs the **Meta (Facebook) Pixel** on Odoo's own
Website/eCommerce pages and mirrors key events into Odoo for reporting.

## Status
Installed and running in `odoo18db`. **Only remaining step is entering your
Meta Pixel ID** in Website Settings — everything else is wired up.

## What it actually does

### 1. Base Pixel code on every page
A template hook on `website.layout` injects the standard Meta Pixel snippet
into the `<head>` of every frontend page, but **only if a Pixel ID is set** —
otherwise nothing is injected (no dead code running on your site by default).
This fires the base `fbq('init', ...)` + `fbq('track', 'PageView')` calls,
exactly like pasting the code Meta gives you when you create a Pixel.

### 2. Purchase event
On the eCommerce order confirmation page (`/shop/confirmation`), an extra
script block fires `fbq('track', 'Purchase', {value, currency})` using the
real order total — the standard event Meta uses for ROAS/conversion
reporting on ads. The same moment is also logged server-side (see below).

### 3. Lead event
Any website form that creates a CRM lead (e.g. the built-in "Contact Us"
form) is hooked at the generic form-submission controller level. When a
`crm.lead` record is created via a website form, a `Lead` event is logged
server-side. (Note: this one is server-side only for now — see Caveats.)

### 4. In-Odoo event log (for your own reporting)
Independent of what Meta's own Events Manager shows you, this addon keeps
its own log inside Odoo:
- A JS beacon (`/meta_pixel/track_pageview`) fires on every page load and
  logs a **Page View** row
- Order confirmation logs a **Purchase** row (value, currency, order, contact)
- Website form submissions to `crm.lead` log a **Lead** row (contact, URL)

You can browse/filter/graph these under **Website → Configuration → Meta
Pixel Events** without needing access to Meta's dashboard.

## How to use it

1. **Get a Pixel ID** from Meta Events Manager (business.facebook.com/events_manager
   → Connect Data Sources → Web → Meta Pixel). It's a 15–16 digit number.
2. In Odoo: **Website → Configuration → Settings** → find the **"Meta Pixel
   Tracking"** section → paste the ID into **Meta Pixel ID** → Save.
3. Visit any page on your Odoo-hosted website — the Pixel now fires
   automatically. Verify it's working with the free **Meta Pixel Helper**
   Chrome extension (should show a green check + list PageView events).
4. Place a test order through the Odoo eCommerce checkout — on the
   confirmation page you should see a `Purchase` event fire (Pixel Helper)
   and a corresponding row appear under **Website → Configuration → Meta
   Pixel Events**.
5. Submit the website Contact form — a `Lead` row should appear in the same
   log (this one won't show in Pixel Helper since it's server-side only).

## Where things live

| Location | What's there |
|---|---|
| Website → Configuration → Settings → Meta Pixel Tracking | Pixel ID field |
| Website → Configuration → Meta Pixel Events | List/graph of logged page views, purchases, leads |

## Files

```
website_meta_pixel_tracking/
├── __manifest__.py
├── controllers/
│   └── main.py                  # Lead logging (form controller override),
│                                 # Purchase logging (checkout controller override),
│                                 # /meta_pixel/track_pageview JSON route
├── models/
│   ├── website.py                # meta_pixel_id field on website
│   ├── res_config_settings.py    # exposes it in Website Settings
│   └── meta_pixel_event.py       # the in-Odoo event log model
├── views/
│   ├── website_templates.xml     # Pixel base code + pageview beacon (website.layout),
│   │                              # Purchase fbq call (website_sale.confirmation)
│   ├── res_config_settings_views.xml
│   └── meta_pixel_event_views.xml
└── security/
    └── ir.model.access.csv
```

## Dependencies
`website`, `website_sale`, `website_crm` (all core Odoo modules).

## Known caveats / not yet done
- **Only tracks Odoo's own Website/eCommerce pages.** If your real storefront
  is on Shopify, WordPress, or elsewhere, this addon sees nothing — the
  Pixel would need to be installed directly on that platform instead.
- **Lead event has no client-side `fbq('track', 'Lead')` call yet** — website
  forms submit via AJAX without a full page reload, so there's no natural
  point to inject a client-side Pixel call without extra JS listening for
  the form's success state. Right now Leads are only logged server-side into
  Odoo's own event log, not sent to Meta's Pixel/Events Manager. If you need
  Leads to show up in Meta's ad reporting too, this needs either: (a) a small
  JS snippet watching for the website form's success class, or (b) switching
  to server-side events via the Meta **Conversions API** instead of the
  client Pixel for this event type.
- **No deduplication/event ID matching** between the client-side Pixel events
  and a future server-side Conversions API — if both were added later for
  the same event, Meta could double-count without an `event_id` tying them
  together.
- **Not tested against a live Pixel** — the snippet follows Meta's standard
  documented format, but you should verify with Pixel Helper on first use.
- **No ad-attribution capture** (fbclid/UTM tracking to tie a purchase back
  to a specific ad/campaign) — out of scope per current requirements, would
  be a separate addition if needed later.
