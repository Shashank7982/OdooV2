# Manual Testing Guide

Server: `http://localhost:3000` (db: `odoo18db`)

This file tracks manual test workflows for features implemented on this branch.
Add a new dated section per feature as it's built.

---

## 1. Multi-Currency (INR / USD)

**What changed:**
- `custom_accounting_core`: added `res.users.preferred_currency_id` ("Preferred Currency"), exposed in My Profile → Preferences. Ensured INR and USD are both active currencies. Added an "India (INR)" product pricelist. Added a current INR/USD exchange rate.
- `custom_accounting_dashboard`: dashboard wizard has a "Display Currency" selector (defaults to the user's Preferred Currency), and all KPIs are converted to it on Refresh.
- `custom_accounting_affiliate`: affiliate commission KPIs on the dashboard also convert to Display Currency.
- Statutory financial reports (Trial Balance, P&L, Balance Sheet, General Ledger) intentionally stay in company currency only — not user-convertible, since these must report in the functional currency.
- Native Odoo multi-currency (per-document `currency_id` on invoices, pricelist-driven currency on sale orders) was verified working, not custom-built.

**Test steps:**

1. **Active currencies**: Settings → Technical → Currencies. Confirm INR and USD both show as active.
2. **Preferred Currency setting**: Avatar (top right) → My Profile → Preferences. Confirm a "Preferred Currency" field appears (own row, below Timezone). Set it to USD (or INR) and save.
3. **Accounting Dashboard**: Accounting → Dashboard. Open the wizard — "Display Currency" should default to your Preferred Currency. Click Refresh.
   - Confirm every KPI (Receivables, Payables, Bank/Cash, Revenue/Expense/Profit, GST figures if installed, Budget figures if installed, Affiliate commissions if installed) shows the correct symbol ($ or ₹) for the Display Currency.
   - Spot-check one value against the rate in Settings → Currencies to confirm it's actually converted, not just re-labelled.
   - Change Display Currency directly on the wizard (override your saved preference) → Refresh → confirm everything updates together.
4. **Statutory reports stay in company currency**: Accounting → Reports → generate Trial Balance / P&L / Balance Sheet. Confirm there is no currency selector and amounts are in the company's currency only.
5. **Per-document currency on invoices**: Accounting → Customer Invoices → New. In the header, while in draft, set Currency to INR on one invoice and USD on another. Confirm both post and coexist permanently, each in its own currency.
6. **Per-document currency on sale orders**: Sales → Quotations → New. Set Pricelist = "India (INR)" on one quotation → totals switch to ₹. Create another with Pricelist = "Default" (USD) → totals in $. Confirm both save side by side.
7. **Aged Partner report with foreign-currency invoices**: if you have invoices in a foreign currency, run the Aged Partner report and confirm residual balances are correct (uses `amount_residual_currency`, not raw company-currency balance).
8. **Per-user isolation**: log in as a second user (or incognito), set their Preferred Currency differently from the first user. Refresh dashboards independently for each — confirm each sees their own currency, proving it's per-user, not global.

---

## 2. Date Format (DD/MM/YYYY)

**What changed:**
- `res.lang.date_format` set to `%d/%m/%Y` for every installed language (drives all form/list/filter date widgets and every QWeb PDF report's `format_date()` calls). Baked into `custom_accounting_core`'s `post_init_hook` so it applies automatically on fresh installs too.
- `custom_bank_reconciliation`'s CSV/XLSX bank statement import wizard: `date_format` selection field default changed from `YYYY-MM-DD` to `DD/MM/YYYY` (all three formats remain selectable, since bank export formats vary). Downloadable templates already generate their sample date dynamically from this field.
- No other hardcoded date formats found in custom modules.

**Test steps:**

1. **Hard refresh** the browser (Ctrl+Shift+R) or log out/in — the running session may have cached the old locale format client-side.
2. **Forms**: open any Invoice or Sale Order. Confirm date fields (Invoice Date, Due Date, etc.) display and accept `DD/MM/YYYY` (e.g. `26/08/2026`, not `08/26/2026`).
3. **List views**: open Accounting → Customer Invoices list. Confirm the Date column shows DD/MM/YYYY.
4. **Filters**: in any list view, open Filters → Add Custom Filter on a date field. Confirm the date picker/input uses DD/MM/YYYY.
5. **PDF reports**: print a Customer Invoice and the custom Financial Report (Trial Balance/P&L). Confirm all printed dates are DD/MM/YYYY.
6. **CSV/XLSX templates**: Accounting → Bank Reconciliation → CSV Import wizard → Download Template (both CSV and XLSX buttons). Confirm the sample row's date column is DD/MM/YYYY and the wizard's "Date Format" field defaults to DD/MM/YYYY.
7. **Dashboards**: refresh the Accounting Dashboard and check any date range / "as of" labels are DD/MM/YYYY.

If any screen still shows MM/DD/YYYY after a hard refresh, note which screen — something there is likely overriding the locale format explicitly.

---

## 3. Contact Classification (Contacts ↔ Accounting)

**What changed (new module `contact_classification`):**
- New `res.partner` fields: `contact_type` (Employee / Vendor / Customer / Affiliate-Commission Partner / Consultant / Other) and `customer_classification` (D2C / Retailer / Distributor / Manufacturer / Wholesaler, shown only when Contact Type = Customer).
- A **"New Contact" wizard** ("Select Contact Type") is now the entry point for creating contacts: it asks for Name + Contact Type (+ Customer Category if Customer) first, then creates the partner and opens its form.
- The native "New" button on the Contacts app's kanban/list browse views is disabled, so contact creation from the Contacts app always goes through the wizard. Quick-create dropdowns elsewhere in Odoo (e.g. picking a customer on a sale order and typing a new name) are untouched.
- The Contact form now shows/hides fields and smart buttons by `contact_type`:
  - **Employee**: smart button linking to (or creating) the linked `hr.employee` record — department, job, manager, attendance, expenses all live there natively.
  - **Vendor**: native Purchases and Vendor Bills (payable) smart buttons shown; GST fields, payment terms, bank details remain in their existing tabs.
  - **Customer**: native Sales and Invoiced (receivables) smart buttons shown; Customer Category, GST fields, credit limit, payment terms available.
  - **Affiliate**: smart button linking to (or creating) the linked `sale.affiliate` record — commission rate, history, and payouts live there.
  - **Consultant**: new "Consultant Details" tab (service description, contract start/end) plus the same Purchases/Vendor Bills buttons as a vendor, since consultants are paid the same way.
  - **Other**: only common fields (name, phone, email, address, tax info, bank details) — no type-specific button/tab.
- Nothing was duplicated: purchase/sales history, receivables/payable, GST fields, payment terms, and credit limit all reuse Odoo's existing native fields — only visibility was made conditional on `contact_type`.

**Test steps:**

1. **Hard refresh** the browser, go to the **Contacts** app.
2. Confirm there is **no "New" button** on the kanban or list view of the main Contacts screen.
3. In the top app menu bar, click **"New Contact"** (next to "Contacts" / "Configuration"). Confirm a dialog opens asking for Name and Contact Type (radio buttons: Employee, Vendor, Customer, Affiliate/Commission Partner, Consultant, Other).
4. Select **Customer** — confirm a "Customer Category" radio group appears (D2C, Retailer, Distributor, Manufacturer, Wholesaler). Fill in a name, pick D2C, click **Continue**.
5. Confirm the full contact form opens with **Contact Type = Customer** and **Customer Category = D2C** already set near the top (next to Tags).
   - Confirm the **Sales** and **Invoiced** smart buttons are visible.
   - Confirm there is **no** Purchases, Vendor Bills, Employee, or Affiliate button.
   - Confirm there is **no** "Consultant Details" tab.
6. Repeat the wizard for **Vendor** — confirm the form shows **Purchases** and **Vendor Bills** buttons, no Sales/Invoiced/Employee/Affiliate buttons, no Customer Category field.
7. Repeat for **Employee** — confirm an **"Employee"** (or "Create Employee" if unlinked) smart button appears. Click it — should open/create an `hr.employee` record pre-filled with the contact's name, where department, job position, manager, attendance, and expenses are managed.
8. Repeat for **Affiliate / Commission Partner** — confirm an **"Affiliate Profile"** (or "Create Affiliate Profile") smart button appears. Click it — should open/create a `sale.affiliate` record where commission rate/history/payout live.
9. Repeat for **Consultant** — confirm the **"Consultant Details"** tab appears (Service Details text box, Contract Start/End dates), and Purchases/Vendor Bills buttons are visible (consultants paid like vendors), but no Sales/Invoiced/Employee/Affiliate buttons.
10. Repeat for **Other** — confirm no type-specific button or tab appears, only common fields.
11. **Common fields sanity check**: on any of the above, confirm Name, Phone, Email, Address, Tax ID (VAT/GST), and the Sales & Purchase / Accounting tab (bank details, payment terms) are present regardless of type.
12. **Non-Contacts-app creation still works**: go to Sales → Quotations → New, click into the Customer field, type a brand-new name, and use "Create" (not "Create and Edit") — confirm this still works without the wizard interrupting (this path is intentionally left alone).
