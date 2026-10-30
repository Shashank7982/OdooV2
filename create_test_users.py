"""Create or update the RBAC users used by the accounting acceptance tests.

Usage::

    python create_test_users.py
    python create_test_users.py --admin-password <master-user-password>

The script talks to Odoo's XML-RPC endpoint and is intentionally idempotent:
running it again updates the existing users instead of creating duplicates.
The administrator password can also be supplied through ODOO_ADMIN_PASSWORD.
"""

from __future__ import annotations

import argparse
import os
import sys
import xmlrpc.client


DEFAULT_URL = "http://localhost:3000"
DEFAULT_DB = "odoov2db"
DEFAULT_ADMIN_LOGIN = "admin"
DEFAULT_ADMIN_PASSWORD = "admin"
TEST_PASSWORD = "Test@1234"

USERS = (
    ("test_acct_user", "Test Accounting User", "custom_accounting_security.group_accounting_user"),
    ("test_finance_ctrl", "Test Finance Controller", "custom_accounting_security.group_accounting_finance_controller"),
    ("test_acct_mgr", "Test Accounting Manager", "custom_accounting_security.group_accounting_manager"),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=os.getenv("ODOO_URL", DEFAULT_URL))
    parser.add_argument("--database", default=os.getenv("ODOO_DATABASE", DEFAULT_DB))
    parser.add_argument("--admin-login", default=os.getenv("ODOO_ADMIN_LOGIN", DEFAULT_ADMIN_LOGIN))
    parser.add_argument(
        "--admin-password",
        default=os.getenv("ODOO_ADMIN_PASSWORD", DEFAULT_ADMIN_PASSWORD),
        help="Password for the Odoo administrator user (or ODOO_ADMIN_PASSWORD).",
    )
    return parser.parse_args()


def execute(models, database, uid, password, model, method, *method_args, **kwargs):
    return models.execute_kw(
        database,
        uid,
        password,
        model,
        method,
        list(method_args),
        kwargs,
    )


def xmlid_to_res_id(models, database, uid, password, xmlid: str) -> int:
    """Resolve an XML ID using public ORM methods (XML-RPC blocks private ones)."""
    module, name = xmlid.split(".", 1)
    records = execute(
        models,
        database,
        uid,
        password,
        "ir.model.data",
        "search_read",
        [("module", "=", module), ("name", "=", name)],
        fields=["res_id"],
        limit=1,
    )
    if not records:
        raise RuntimeError(f"XML ID not found: {xmlid}")
    return records[0]["res_id"]


def main() -> int:
    args = parse_args()
    common = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/common", allow_none=True)
    models = xmlrpc.client.ServerProxy(f"{args.url}/xmlrpc/2/object", allow_none=True)

    try:
        uid = common.authenticate(args.database, args.admin_login, args.admin_password, {})
    except Exception as exc:  # pragma: no cover - network errors are environment-specific
        print(f"Could not connect to Odoo at {args.url}: {exc}", file=sys.stderr)
        return 2
    if not uid:
        print("Odoo authentication failed. Check database, admin login, and password.", file=sys.stderr)
        return 2

    group_ids = {}
    for _, _, group_xmlid in USERS:
        group_ids[group_xmlid] = xmlid_to_res_id(
            models, args.database, uid, args.admin_password, group_xmlid
        )

    base_user_id = xmlid_to_res_id(
        models, args.database, uid, args.admin_password, "base.group_user"
    )

    for login, name, group_xmlid in USERS:
        existing = execute(
            models,
            args.database,
            uid,
            args.admin_password,
            "res.users",
            "search",
            [("login", "=", login)],
            limit=1,
        )
        values = {
            "name": name,
            "login": login,
            "password": TEST_PASSWORD,
            "active": True,
            "groups_id": [(6, 0, [base_user_id, group_ids[group_xmlid]])],
        }
        if existing:
            execute(models, args.database, uid, args.admin_password, "res.users", "write", existing, values)
            action = "updated"
        else:
            execute(models, args.database, uid, args.admin_password, "res.users", "create", values)
            action = "created"
        print(f"{action}: {login} ({name})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
