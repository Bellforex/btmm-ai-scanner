"""The smallest reliable validation endpoint. Stdlib only.

POST /v1/licenses/validate

A thin transport over `service.validate` — all decisions live there, so the
thirteen licence cases are unit-tested without a socket.

TLS is terminated in front of this (nginx/Caddy/Cloudflare). The service binds
localhost by default so an accidental run is not world-reachable.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from licensing.keys import mask_key
from licensing.service import ValidationRequest, validate
from licensing.store import LicenseStore

__all__ = ["build_handler", "serve"]

MAX_BODY = 8 * 1024


def build_handler(store: LicenseStore) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "RC5License/1.0"

        def log_message(self, fmt: str, *args: object) -> None:
            # Default logging would echo the request line. Ours never can,
            # because the key travels in the BODY and is masked below.
            return

        def _json(self, code: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            """Liveness only. It answers whether the process is up and can
            reach its store — and deliberately reveals nothing else: no
            counts, no licence ids, no version of anything customer-visible.
            An unauthenticated endpoint is not a status page."""
            if self.path != "/v1/health":
                self._json(404, {"status": "not found"})
                return
            try:
                store.all_licenses()
            except Exception:  # the answer is "not ok", never why
                self._json(503, {"status": "unavailable"})
                return
            self._json(200, {"status": "ok"})

        def do_POST(self) -> None:
            if self.path != "/v1/licenses/validate":
                self._json(404, {"valid": False, "message": "Not found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = 0
            if length <= 0 or length > MAX_BODY:
                self._json(400, {"valid": False, "message": "Bad request"})
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._json(400, {"valid": False, "message": "Bad request"})
                return

            request = ValidationRequest(
                license_key=str(payload.get("license_key", "")),
                product_id=str(payload.get("product_id", "")),
                ea_version=str(payload.get("ea_version", "")),
                account_login=str(payload.get("account_login", "")),
                account_server=str(payload.get("account_server", "")),
                nonce=str(payload.get("nonce", "")),
            )
            response = validate(store, request, now=datetime.now(UTC))
            print(
                f"[{datetime.now(UTC):%Y-%m-%dT%H:%M:%SZ}] "
                f"{mask_key(request.license_key)} "
                f"{request.account_login}@{request.account_server} "
                f"-> {response.state.value}",
                flush=True,
            )
            self._json(200, response.to_json())

    return Handler


def serve(
    db: Path, *, pepper: bytes, host: str = "127.0.0.1", port: int = 8713
) -> None:
    store = LicenseStore(db, pepper=pepper)
    # THREADING, not HTTPServer: a single-threaded validator lets one slow
    # or half-open client block every other customer's check. Behind a
    # public reverse proxy that is an availability defect, not a nicety.
    httpd = ThreadingHTTPServer((host, port), build_handler(store))
    print(f"RC5 licensing on http://{host}:{port}/v1/licenses/validate")
    httpd.serve_forever()


if __name__ == "__main__":  # pragma: no cover - operator entry point
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("licensing/licenses.db"))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8713)
    args = parser.parse_args()

    secret = os.environ.get("RC5_LICENSE_PEPPER")
    if not secret:
        raise SystemExit(
            "RC5_LICENSE_PEPPER is not set. The pepper is a server secret and "
            "must never be committed or embedded in the EX5."
        )
    serve(args.db, pepper=secret.encode("utf-8"), host=args.host, port=args.port)
