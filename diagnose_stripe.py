"""Diagnostic script to check why Stripe payment is not showing at checkout."""
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo18db'
username = 'admin'
password = 'admin'

# Connect
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
try:
    uid = common.authenticate(db, username, password, {})
except Exception as e:
    print(f"ERROR: Could not connect to Odoo at {url}: {e}")
    print("Make sure Odoo is running.")
    exit(1)

if not uid:
    print("ERROR: Authentication failed. Check username/password.")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 60)
print("STRIPE PAYMENT DIAGNOSTIC REPORT")
print("=" * 60)

# 1. Check if payment_stripe module is installed
print("\n--- 1. Module Status ---")
module_ids = models.execute_kw(db, uid, password, 'ir.module.module', 'search_read',
    [[('name', 'in', ['payment_stripe', 'payment_stripe_custom', 'website_sale', 'website_payment', 'payment'])]],
    {'fields': ['name', 'state']})
for m in module_ids:
    print(f"  {m['name']}: {m['state']}")

# 2. Check payment providers
print("\n--- 2. Payment Providers ---")
providers = models.execute_kw(db, uid, password, 'payment.provider', 'search_read',
    [[]],
    {'fields': ['name', 'code', 'state', 'is_published', 'company_id', 'website_id',
                'stripe_publishable_key', 'stripe_secret_key', 'stripe_webhook_secret',
                'payment_method_ids', 'available_country_ids', 'available_currency_ids',
                'maximum_amount']})
for p in providers:
    print(f"\n  Provider: {p['name']} (code={p['code']})")
    print(f"    State: {p['state']}")
    print(f"    Published: {p['is_published']}")
    print(f"    Company: {p['company_id']}")
    print(f"    Website: {p['website_id']}")
    if p['code'] == 'stripe':
        print(f"    Publishable Key set: {bool(p.get('stripe_publishable_key'))}")
        print(f"    Secret Key set: {bool(p.get('stripe_secret_key'))}")
        print(f"    Webhook Secret set: {bool(p.get('stripe_webhook_secret'))}")
    print(f"    Payment Methods: {p['payment_method_ids']}")
    print(f"    Country restrictions: {p['available_country_ids']}")
    print(f"    Currency restrictions: {p['available_currency_ids']}")
    print(f"    Max amount: {p['maximum_amount']}")

# 3. Check payment methods linked to stripe
print("\n--- 3. Payment Methods ---")
all_methods = models.execute_kw(db, uid, password, 'payment.method', 'search_read',
    [[]],
    {'fields': ['name', 'code', 'active', 'provider_ids', 'support_tokenization']})
for m in all_methods:
    print(f"  {m['name']} (code={m['code']}, active={m['active']}, providers={m['provider_ids']})")

# 4. Check websites
print("\n--- 4. Websites ---")
websites = models.execute_kw(db, uid, password, 'website', 'search_read',
    [[]],
    {'fields': ['name', 'company_id']})
for w in websites:
    print(f"  Website: {w['name']} (id={w['id']}, company={w['company_id']})")

# 5. Check company
print("\n--- 5. Current Company ---")
companies = models.execute_kw(db, uid, password, 'res.company', 'search_read',
    [[]],
    {'fields': ['name', 'currency_id', 'country_id']})
for c in companies:
    print(f"  Company: {c['name']} (currency={c['currency_id']}, country={c['country_id']})")

print("\n" + "=" * 60)
print("DIAGNOSIS SUMMARY")
print("=" * 60)

# Check common issues
stripe_providers = [p for p in providers if p['code'] == 'stripe']
if not stripe_providers:
    print("  ❌ No Stripe payment provider found!")
    print("     -> Install payment_stripe module and create provider")
else:
    sp = stripe_providers[0]
    issues = []
    if sp['state'] == 'disabled':
        issues.append("❌ Stripe provider is DISABLED. Set state to 'enabled' or 'test'.")
    if not sp['is_published']:
        issues.append("❌ Stripe provider is NOT PUBLISHED. It won't show on the website.")
    if not sp.get('stripe_publishable_key'):
        issues.append("❌ Stripe publishable key is NOT SET.")
    if not sp.get('stripe_secret_key'):
        issues.append("❌ Stripe secret key is NOT SET.")
    if not sp['payment_method_ids']:
        issues.append("❌ No payment methods linked to the Stripe provider.")
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ Stripe provider configuration looks correct.")
        print("     If it's still not showing, check:")
        print("     - Country/currency restrictions")
        print("     - Website-specific assignment")
        print("     - Browser console for JS errors")

# Check module status
stripe_module = [m for m in module_ids if m['name'] == 'payment_stripe']
if stripe_module and stripe_module[0]['state'] != 'installed':
    print(f"  ❌ payment_stripe module is {stripe_module[0]['state']}, not installed!")
ws_module = [m for m in module_ids if m['name'] == 'website_sale']
if ws_module and ws_module[0]['state'] != 'installed':
    print(f"  ❌ website_sale module is {ws_module[0]['state']}, not installed!")
wp_module = [m for m in module_ids if m['name'] == 'website_payment']
if wp_module and wp_module[0]['state'] != 'installed':
    print(f"  ❌ website_payment module is {wp_module[0]['state']}, not installed!")
