"""Fix Stripe payment provider to show at website checkout.

Issues found:
1. State is 'disabled' -> needs to be 'test' (for test keys) or 'enabled'
2. is_published is False -> must be True to show on website
3. Publishable/Secret keys are NOT set -> must be configured
4. No payment methods linked -> need to activate default payment methods
"""
import xmlrpc.client

url = 'http://localhost:8069'
db = 'odoo18db'
username = 'admin'
password = 'admin'

# Stripe test keys from stripe_setup.py
PUBLISHABLE_KEY = 'pk_test_51TpD0l15MX0FtmA0puECO21QMPX9u61Vg35mH4K4x06PC0PdSMi324XDxVL9hbLcG7CpazjODQzzmButcfw13hOZ00mudJYZQX'
SECRET_KEY = 'sk_test_51TpD0l15MX0FtmA07GJEpgZ67J1vTEehl8bAaMxhelkGLw0oRm852gkKZlD2ASLWTdG9mdZVGclhJf5huLJYHOud00zBenAAJo'

# Connect
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
if not uid:
    print("ERROR: Authentication failed")
    exit(1)

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# Find stripe provider
provider_ids = models.execute_kw(db, uid, password, 'payment.provider', 'search',
    [[('code', '=', 'stripe')]])

if not provider_ids:
    print("ERROR: No Stripe provider found. The payment_stripe module may not be installed.")
    exit(1)

provider_id = provider_ids[0]
print(f"Found Stripe provider (id={provider_id})")

# Fix 1: Set the API keys
print("\n[FIX 1] Setting Stripe API keys...")
models.execute_kw(db, uid, password, 'payment.provider', 'write',
    [[provider_id], {
        'stripe_publishable_key': PUBLISHABLE_KEY,
        'stripe_secret_key': SECRET_KEY,
    }])
print("  Done - API keys configured")

# Fix 2: Set state to 'test' (since we're using test keys)
print("\n[FIX 2] Setting state to 'test' mode...")
models.execute_kw(db, uid, password, 'payment.provider', 'write',
    [[provider_id], {
        'state': 'test',
    }])
print("  Done - State set to 'test'")

# Fix 3: Publish the provider
print("\n[FIX 3] Publishing the provider (is_published=True)...")
models.execute_kw(db, uid, password, 'payment.provider', 'write',
    [[provider_id], {
        'is_published': True,
    }])
print("  Done - Provider is now published")

# Fix 4: Activate default payment methods for stripe
# In Odoo 18, payment methods need to be linked to the provider
print("\n[FIX 4] Activating payment methods...")

# First check if there are any payment methods at all
all_methods = models.execute_kw(db, uid, password, 'payment.method', 'search_read',
    [[]],
    {'fields': ['name', 'code', 'active', 'provider_ids']})

if not all_methods:
    print("  No payment methods found in database.")
    print("  Looking for inactive ones...")
    all_methods = models.execute_kw(db, uid, password, 'payment.method', 'search_read',
        [[('active', '=', False)]],
        {'fields': ['name', 'code', 'active', 'provider_ids']})

if all_methods:
    # Link card payment method to stripe provider
    card_methods = [m for m in all_methods if m['code'] in ('card', 'visa', 'mastercard')]
    if card_methods:
        for m in card_methods:
            models.execute_kw(db, uid, password, 'payment.method', 'write',
                [[m['id']], {
                    'active': True,
                    'provider_ids': [(4, provider_id)],
                }])
            print(f"  Linked method '{m['name']}' (code={m['code']}) to Stripe")
    else:
        # Link all available methods
        for m in all_methods:
            models.execute_kw(db, uid, password, 'payment.method', 'write',
                [[m['id']], {
                    'active': True,
                    'provider_ids': [(4, provider_id)],
                }])
            print(f"  Linked method '{m['name']}' (code={m['code']}) to Stripe")
else:
    print("  WARNING: No payment methods found at all. You may need to reset default payment methods.")
    print("  Try: Settings -> Payment Providers -> Stripe -> Payment Methods tab")

# Verify the fix
print("\n" + "=" * 60)
print("VERIFICATION")
print("=" * 60)
provider = models.execute_kw(db, uid, password, 'payment.provider', 'read',
    [[provider_id]],
    {'fields': ['name', 'code', 'state', 'is_published', 'stripe_publishable_key',
                'stripe_secret_key', 'payment_method_ids']})[0]

print(f"  Provider: {provider['name']}")
print(f"  State: {provider['state']}")
print(f"  Published: {provider['is_published']}")
print(f"  Publishable Key set: {bool(provider.get('stripe_publishable_key'))}")
print(f"  Secret Key set: {bool(provider.get('stripe_secret_key'))}")
print(f"  Payment Methods count: {len(provider['payment_method_ids'])}")

all_good = (
    provider['state'] in ('enabled', 'test') and
    provider['is_published'] and
    bool(provider.get('stripe_publishable_key')) and
    bool(provider.get('stripe_secret_key'))
)

if all_good:
    print("\n  [OK] Stripe should now appear at checkout!")
    print("  Visit your shop and try checking out.")
else:
    print("\n  [WARNING] Some issues may remain. Check the values above.")
