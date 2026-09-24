"""RC5 licence administration. CLI, because an event needs reliable, not fancy.

    python -m licensing.admin create --customer "Jane" --email j@x.com --days 30
    python -m licensing.admin list
    python -m licensing.admin show LIC-...
    python -m licensing.admin revoke LIC-...
    python -m licensing.admin suspend LIC-...
    python -m licensing.admin reactivate LIC-...
    python -m licensing.admin expiry LIC-... --days 30
    python -m licensing.admin activations LIC-...

The plaintext key is printed EXACTLY ONCE, by `create`, and is never stored.
Every other command shows the masked form, so a shared terminal, a screenshot
or a scrollback never leaks a working key.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from licensing.store import LicenseStatus, LicenseStore

__all__ = ["main"]

DEFAULT_DB = Path("licensing/licenses.db")


def _store(args: argparse.Namespace) -> LicenseStore:
    secret = os.environ.get("RC5_LICENSE_PEPPER")
    if not secret:
        raise SystemExit(
            "RC5_LICENSE_PEPPER is not set. It is a server-side secret: it "
            "must never be committed, and never embedded in the EX5."
        )
    return LicenseStore(args.db, pepper=secret.encode("utf-8"))


def _cmd_create(args: argparse.Namespace) -> int:
    store = _store(args)
    expires = datetime.now(UTC) + timedelta(days=args.days)
    key, record = store.create(
        customer=args.customer,
        email=args.email,
        expires_at=expires,
        product_id=args.product,
        minimum_version=args.min_version,
        max_activations=args.activations,
        notes=args.notes,
    )
    print(store.describe(record))
    print()
    print("  LICENSE KEY (shown ONCE, never stored, give this to the customer):")
    print(f"      {key}")
    print()
    print("  Record it in the customer registry now -- it cannot be recovered.")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    store = _store(args)
    records = store.all_licenses()
    if not records:
        print("no licenses")
        return 0
    for record in records:
        print(store.describe(record))
    return 0


def _cmd_show(args: argparse.Namespace) -> int:
    store = _store(args)
    record = store.by_id(args.license_id)
    if record is None:
        print(f"no such license: {args.license_id}", file=sys.stderr)
        return 1
    print(store.describe(record))
    for activation in store.activations(record.license_id):
        print(
            f"    {activation['account_login']}@{activation['account_server']}"
            f"  first {activation['first_seen']}  last {activation['last_seen']}"
            f"  v{activation['ea_version']}"
        )
    return 0


def _set_status(args: argparse.Namespace, status: LicenseStatus) -> int:
    store = _store(args)
    if not store.set_status(args.license_id, status):
        print(f"no such license: {args.license_id}", file=sys.stderr)
        return 1
    print(f"{args.license_id} -> {status.value}")
    return 0


def _cmd_expiry(args: argparse.Namespace) -> int:
    store = _store(args)
    when = datetime.now(UTC) + timedelta(days=args.days)
    if not store.set_expiry(args.license_id, when):
        print(f"no such license: {args.license_id}", file=sys.stderr)
        return 1
    print(f"{args.license_id} expires {when:%Y-%m-%d %H:%M}Z")
    return 0


def _cmd_activations(args: argparse.Namespace) -> int:
    store = _store(args)
    rows = store.activations(args.license_id)
    if not rows:
        print("no activations")
        return 0
    for row in rows:
        print(f"    {row['account_login']}@{row['account_server']}  "
              f"first {row['first_seen']}  last {row['last_seen']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="mint a new license")
    create.add_argument("--customer", required=True)
    create.add_argument("--email", required=True)
    create.add_argument("--days", type=int, required=True)
    create.add_argument("--activations", type=int, default=1)
    create.add_argument("--product", default="RC5-EA")
    create.add_argument("--min-version", default="1.00")
    create.add_argument("--notes", default="")
    create.set_defaults(func=_cmd_create)

    sub.add_parser("list", help="list licenses").set_defaults(func=_cmd_list)

    for name, fn in (
        ("show", _cmd_show),
        ("activations", _cmd_activations),
    ):
        p = sub.add_parser(name)
        p.add_argument("license_id")
        p.set_defaults(func=fn)

    for name, status in (
        ("revoke", LicenseStatus.REVOKED),
        ("suspend", LicenseStatus.SUSPENDED),
        ("reactivate", LicenseStatus.ACTIVE),
    ):
        p = sub.add_parser(name)
        p.add_argument("license_id")
        p.set_defaults(func=lambda a, s=status: _set_status(a, s))

    expiry = sub.add_parser("expiry", help="change expiry, in days from now")
    expiry.add_argument("license_id")
    expiry.add_argument("--days", type=int, required=True)
    expiry.set_defaults(func=_cmd_expiry)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover - operator entry point
    raise SystemExit(main())
