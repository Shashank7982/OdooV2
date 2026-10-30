# Third-Party Integration Feasibility Report for Odoo 18

Research date: 2026-08-18

This report evaluates the feasibility of integrating 11 third-party platforms into
Odoo (via custom addons and/or existing Odoo Apps Store modules): lead-gen portals,
social platforms, GST billing/compliance, logistics, VOIP/video, WhatsApp, and
affiliate/coupon platforms.

## Summary ranking

| Feasibility | Platforms |
|---|---|
| **Easy** — ready-made Odoo modules or well-documented, self-serve APIs | Indiamart, GST e-Invoice/e-Way Bill, Shiprocket, Zoom, WhatsApp Cloud API |
| **Medium** — custom build needed, doable, some gatekeeping | Justdial, Facebook Lead Ads, Google Meet, Porter, Impact.com, GoAffPro, Cuelinks |
| **Hard** — real approval/access barriers | Instagram (outbound messaging), LinkedIn Lead Sync |
| **Not feasible directly** | Vyapar (no public API), CashKaro / Wishlink / Coupon Dunia / INRDeals / Kiffo (no public merchant API — feed-based only) |

---

## 1. Indiamart (lead generation)

- **API**: Official Lead Manager CRM API — **Pull API** (poll every 5 min, JSON) and **Push API** (real-time webhook).
  Docs: [dev-help.indiamart.com](https://dev-help.indiamart.com/knowledge-base/lms-crm-integration/), [help.indiamart.com v2](https://help.indiamart.com/knowledge-base/lms-crm-integration-v2/)
- **Auth**: CRM API key generated from the Indiamart seller panel.
- **Restriction**: Only available to **paid sellers**; self-serve, no vendor hand-holding.
- **Existing Odoo modules**: `dev_indiamart_integration`, `fetch_leads_indiamart`, `wb_indiamart_integration`, `indiamart_api`, `sh_indiamart_integration` (v18), `wt_indiamart_connector`. Reference implementation (ERPNext, portable logic): [indiamart_erpnext_integration](https://github.com/ashish-greycube/indiamart_erpnext_integration).
- **Feasibility: Easy.** A scheduled `ir.cron` hitting the Pull API and mapping JSON leads into `crm.lead` is roughly a half-day build.

## 2. Justdial (lead generation)

- **API**: No fully open public API. Leads are accessed via Justdial's lead-download portal, or a webhook granted to registered/paid listings — similar mechanism to Indiamart but far less standardized. Third-party CRMs (LeadSquared, Kylas, VSCRM, NeoDove) integrate through this same channel.
- **Existing Odoo module**: `crm_justdial_integration_odoo_app` (Odoo Apps Store) — supports manual CSV download plus automated daily fetch.
- **Feasibility: Medium.** Confirm API/webhook access with the Justdial account manager first; fall back to scheduled CSV import if no programmatic access is granted.

## 3. Facebook (leads / ads / messaging)

- **API**: Meta Graph API (Marketing API) — Lead Ads webhooks for real-time delivery.
  Docs: [Lead Ads guide](https://developers.facebook.com/documentation/ads-commerce/marketing-api/guides/lead-ads), [Leadgen webhooks](https://developers.facebook.com/docs/graph-api/webhooks/getting-started/webhooks-for-leadgen/)
- **Auth**: OAuth 2.0 + Page access token; requires **Meta App Review** for `leads_retrieval`, `pages_manage_metadata`, `pages_show_list`, `pages_read_engagement`, `ads_management`.
- **Caveat**: Meta retains lead data only **90 days** — automated retrieval is mandatory, not optional.
- **Existing Odoo modules**: `rcs_facebook_leads_generate`, `eb_facebook_integration`, `dev_facebook_crm_leads`, `pragtech_crm_facebook_leads`.
- **Feasibility: Medium.** The API itself is solid; Meta's App Review process (business verification, use-case justification, review turnaround) is the real bottleneck.

## 4. Instagram (DMs / leads)

- **API**: Instagram Graph API + Messaging API, same Meta ecosystem as Facebook, Business/Creator accounts only. The old Basic Display API is fully retired.
- **Constraints**: Can only message users who messaged first (24-hour free-reply window, 7-day support follow-up window); ~200 automated DMs/hour rate limit as of 2026.
- **Feasibility: Hard for outbound lead-gen, Medium for inbound support/DM sync.** No dedicated Odoo app found — would require extending a Meta OAuth connector with `instagram_manage_messages` scope and syncing into `mail.message` / `discuss.channel`. Custom build only.

## 5. LinkedIn (leads / ads)

- **API**: LinkedIn Lead Sync API — part of the Marketing Developer Platform but gated behind a **separate access program**.
  Docs: [Getting Access to Lead Sync API](https://learn.microsoft.com/en-us/linkedin/marketing/lead-sync/getting-access-leadsync)
- **Auth**: OAuth 2.0; key scope `r_marketing_leadgen_automation`.
- **Restriction**: Marketing Developer Platform access does not auto-grant Lead Sync access — typically reserved for agencies/ad-spend partners.
- **Feasibility: Hard.** No ready-made Odoo module found; the approval gate, not the coding, is the obstacle.

## 6. GST billing software — Vyapar

- **API**: **No public API.** Vyapar is not listed on API/integration registries (e.g. Apideck's accounting software list) and does not expose a developer API. Its e-invoicing works through its own internal GSP integration, not externally.
- **Feasibility: Not feasible directly.** No route for an Odoo↔Vyapar addon unless Vyapar opens a partner API. Practical alternative: skip Vyapar and connect Odoo directly to the government e-Invoice/e-Way Bill system (item 7) — Odoo's India localization already covers this well.

## 7. Official GST government portal (e-Invoice / e-Way Bill)

- **API**: Government-mandated APIs, accessed only through licensed **GSP/ASP** intermediaries (e.g. Alankit, ClearTax, IRIS IRP) — not directly from GSTN to arbitrary applications.
- **2026 change**: Ship-to GSTIN becomes mandatory and a Voluntary Closure facility is added to the e-Way Bill API, effective **1 Aug 2026**. ([compliance checklist](https://www.caclubindia.com/articles/gstns-einvoice-api-and-eway-bill-by-irn-changes-from-1st-august-2026-a-stepbystep-compliance-checklist-for-businesses-55804.asp))
- **Existing Odoo modules**: `gts_einvoicing_and_ewaybill`, `zb_gst_einvoice_irn`, `rcs_alankit_eway_bill` (v18), `eway_bill_india`, `einvoice_india`. Odoo also ships an [official India fiscal localization](https://www.odoo.com/documentation/18.0/applications/finance/fiscal_localizations/india.html) with bundled GSP e-invoicing/e-way bill support.
- **Feasibility: Easy** — use an existing GSP connector module or Odoo's built-in India localization rather than building from scratch.

## 8. Logistics — Porter & Shiprocket

- **Shiprocket**: Full REST API (`apiv2.shiprocket.in`) — order creation, courier assignment/AWB, tracking, labels, returns; API-key auth.
  Docs: [apidocs.shiprocket.in](https://apidocs.shiprocket.in/), [developer portal](https://www.shiprocket.in/developers/)
  Multiple ready Odoo modules: `do_shiprocket_shipping_integration`, `shiprocket_shipping_integration`, `ur_delivery_shiprocket` (v19). Odoo even documents it officially as a delivery carrier: [Shiprocket setup doc](https://www.odoo.com/documentation/19.0/applications/inventory_and_mrp/inventory/shipping_receiving/setup_configuration/shiprocket.html).
  **Feasibility: Easy.**
- **Porter**: Business/Enterprise API exists ([porter.in/api-integrations](https://porter.in/api-integrations)) for intracity dispatch (bike/truck), but it is enterprise-onboarding gated, not self-serve. No existing Odoo connector found.
  **Feasibility: Medium** — custom build against Porter's enterprise API once commercial access is granted; model as a new `delivery.carrier` provider, following the pattern of the Shiprocket modules.

## 9. VOIP / video — Zoom, Google Meet

- **Zoom**: OAuth 2.0 app via Zoom Marketplace, REST API to create/update/cancel meetings. Multiple existing Odoo modules: `az_zoom_meetings`, `zoom_meeting`, `zoom_enterprise_management` (v19, two-way sync). **Feasibility: Easy.**
- **Google Meet**: No standalone "create meeting" endpoint — meetings are created as a side effect of a **Google Calendar API** event with `conferenceData` set, via OAuth or a service account with domain-wide delegation. Odoo already has native Google Calendar sync (Enterprise) that could be extended to surface Meet links. **Feasibility: Easy–Medium.**
- *(Note: the user's list mentioned "Zoom, Google Meet, Zoom" — treated as Zoom + Google Meet; Microsoft Teams follows the same Graph-API pattern as Google Meet if needed later.)*

## 10. WhatsApp

- **API**: Official **WhatsApp Business Cloud API** (Meta-hosted). 2026 pricing changes: new "Meta Business Agent" AI-reply billing from Aug 1, and utility/service messages become chargeable within the service window from Oct 1. Docs: [pricing](https://developers.facebook.com/documentation/business-messaging/whatsapp/pricing)
- **Odoo**: WhatsApp is a **native Enterprise app**, Enterprise-license only. For Community, third-party Cloud API connector modules exist: `tus_meta_whatsapp_base` (v16/17/18), `ur_whatsapp` (v19), `whatsapp_meta_connector`.
- **Feasibility: Easy** — module install + Meta Business verification + phone number registration; no custom coding needed unless deep template/flow customization is wanted.

## 11. Affiliate & coupon platforms

| Platform | API | Notes |
|---|---|---|
| **Impact.com** | Full REST API (brand/partner/solution-provider variants), OpenAPI spec — [integrations.impact.com](https://integrations.impact.com/) | Enterprise-grade, docs behind client access. **Medium** effort. |
| **GoAffPro** | REST + SDK, API keys via admin panel — [docs.goaffpro.com](https://docs.goaffpro.com/), [admin API](https://api.goaffpro.com/docs/admin/) | Built for Shopify/WooCommerce-style stores; needs a custom Odoo eCommerce bridge for tracking/conversions. **Medium.** |
| **Cuelinks** | Public developer API — campaign discovery, link conversion, real-time reports — [developers.cuelinks.com](https://developers.cuelinks.com/) | Aggregates 1000+ merchants incl. Impact/CJ/Awin/Admitad; useful for Odoo-as-merchant feeding Cuelinks. **Medium.** |
| **CashKaro** | No public self-serve API found; only a packaged [Shopify app](https://apps.shopify.com/cashkaro-affiliate-partner). Non-Shopify merchants integrate manually via account team. | **Hard/Not feasible** directly — use a CSV/XML product feed instead. |
| **Wishlink, Coupon Dunia, INRDeals, Kiffo** | No public developer API documentation found. | Consumer-facing coupon/cashback aggregators that typically pull merchant data via **affiliate-network product feeds** rather than a direct merchant API. **Not feasible** as 1:1 integrations — reachable only indirectly via a shared network (e.g. publishing through Impact or Cuelinks). |

**Practical approach for #11**: instead of 8 separate connectors, build one **product/price feed generator module** (CSV/XML per platform's feed spec) plus direct API integrations for the two platforms that actually expose one — **Impact.com** and **Cuelinks** — for order/commission reconciliation.

---

## Recommended build order

1. **Shiprocket** + **GST e-Invoice/e-Way Bill** (via existing GSP connector module) — highest ROI, least friction, mature modules already exist.
2. **Indiamart** — simple cron+API pull into `crm.lead`.
3. **WhatsApp Cloud API** — install a Community connector module (if not on Enterprise) for order/support notifications.
4. **Zoom** — install existing module for meeting-linked CRM/sales activities.
5. **Facebook Lead Ads** — start the Meta App Review process early since it's the long pole (business verification can take weeks).
6. **Justdial**, **Porter**, **Google Meet**, **Impact.com/Cuelinks** — custom builds, scoped one at a time once account/API access is confirmed with each vendor.
7. **Instagram**, **LinkedIn Lead Sync** — deprioritize; revisit if/when partner-level access becomes available.
8. **Vyapar**, **CashKaro/Wishlink/Coupon Dunia/INRDeals/Kiffo** — no direct integration path exists today; use feed-based/manual alternatives.

## Architecture notes for custom addons

- Each integration should be its own addon (`<platform>_connector`), following the existing repo pattern (see `addons/sms_twilio`, `addons/marketing_mail_gateway`, `addons/gmail_webhook_gateway`) — external API client in a `tools/` module, credentials on a `res.config.settings`/dedicated settings model, sync logic behind `ir.cron` or a webhook `http.Controller` route.
- Lead-sourcing integrations (Indiamart, Justdial, Facebook, LinkedIn) should all funnel into `crm.lead` with a `source_id` tag per platform, so CRM reporting stays unified.
- Logistics integrations (Shiprocket, Porter) should implement Odoo's `delivery.carrier` provider interface so they show up natively in Sales/Inventory shipping method selection.
- GST integrations should build on Odoo's existing India fiscal localization rather than reimplementing IRN/e-way bill logic from scratch.
