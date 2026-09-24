"""RC5 commercial licensing — the thirteen cases, plus the two safety invariants.

The security target is COMMERCIAL-GRADE CONTROLLED ACCESS, not uncrackability.
An EX5 runs on the customer's machine; these tests verify the things that are
actually achievable — unguessable keys, central revocation, account binding,
and a failure mode that never harms a paying customer.

Two invariants outrank the rest and are tested against the MQL5 source itself:

1. **a licence failure must never abandon an open trade** — the gate is on the
   OPEN path only, and `CloseRC5Position` has no licence check at all;
2. **the tester bypass cannot activate on a live chart** — it requires
   `MQL_TESTER` *and* an input that defaults false.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from licensing.keys import (
    KEY_ENTROPY_BITS,
    KEY_PATTERN,
    hash_key,
    mask_key,
    new_license_key,
    verify_key,
)
from licensing.service import LicenseState, ValidationRequest, validate
from licensing.store import LicenseStatus, LicenseStore

_REPO = Path(__file__).resolve().parents[2]
_EA = _REPO / "mt5" / "Experts" / "RC5_EA.mq5"
PEPPER = b"test-pepper-never-shipped"

# A fictional login. The author's real account number is deliberately
# NOT committed; nothing here depends on its value.
LOGIN = "50000001"
SERVER = "Exness-MT5Real10"


def _ea() -> str:
    return _EA.read_text(encoding="utf-8-sig")


@pytest.fixture
def store(tmp_path: Path) -> LicenseStore:
    return LicenseStore(tmp_path / "licenses.db", pepper=PEPPER)


def _license(
    store: LicenseStore, *, days: int = 30, activations: int = 1, **kw: object
) -> tuple[str, object]:
    return store.create(
        customer="Event Customer",
        email="customer@example.com",
        expires_at=datetime.now(UTC) + timedelta(days=days),
        max_activations=activations,
        **kw,  # type: ignore[arg-type]
    )


def _request(key: str, **over: str) -> ValidationRequest:
    base = {
        "license_key": key,
        "product_id": "RC5-EA",
        "ea_version": "1.00",
        "account_login": LOGIN,
        "account_server": SERVER,
    }
    base.update(over)
    return ValidationRequest(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# key material
# ---------------------------------------------------------------------------


def test_keys_are_random_and_high_entropy() -> None:
    keys = {new_license_key() for _ in range(500)}
    assert len(keys) == 500, "collision in 500 draws — not random enough"
    assert KEY_ENTROPY_BITS == 100
    for key in list(keys)[:20]:
        assert KEY_PATTERN.match(key), key


def test_the_store_never_holds_a_usable_key(store: LicenseStore) -> None:
    """A copy of the database must not yield working licences."""
    key, record = _license(store)
    assert key not in record.key_hash
    assert verify_key(key, record.key_hash, pepper=PEPPER)
    # and the same key under a different pepper does not verify
    assert record.key_hash != hash_key(key, pepper=b"other")


# ---------------------------------------------------------------------------
# the thirteen cases
# ---------------------------------------------------------------------------


def test_01_valid_account_is_allowed(store: LicenseStore) -> None:
    key, _ = _license(store)
    response = validate(store, _request(key))
    assert response.valid
    assert response.state is LicenseState.VALID
    assert response.lease_until


def test_02_invalid_key_is_denied(store: LicenseStore) -> None:
    _license(store)
    response = validate(store, _request("RC5-00000-00000-00000-00000"))
    assert not response.valid
    assert response.state is LicenseState.INVALID


def test_an_unknown_key_is_indistinguishable_from_a_wrong_one(
    store: LicenseStore,
) -> None:
    """The endpoint must not be usable to discover which keys exist."""
    key, _ = _license(store)
    unknown = validate(store, _request("RC5-ZZZZZ-ZZZZZ-ZZZZZ-ZZZZZ"))
    wrong = validate(store, _request(key[:-1] + ("A" if key[-1] != "A" else "B")))
    assert unknown.message == wrong.message
    assert unknown.state is wrong.state


def test_03_expired_is_denied(store: LicenseStore) -> None:
    key, _ = _license(store, days=-1)
    response = validate(store, _request(key))
    assert not response.valid
    assert response.state is LicenseState.EXPIRED


def test_04_revoked_is_denied(store: LicenseStore) -> None:
    key, record = _license(store)
    assert store.set_status(record.license_id, LicenseStatus.REVOKED)
    response = validate(store, _request(key))
    assert not response.valid
    assert response.state is LicenseState.REVOKED


def test_05_wrong_mt5_login_is_denied(store: LicenseStore) -> None:
    """One activation, already bound to LOGIN. A different login is a second
    activation and exceeds the allowance."""
    key, _ = _license(store, activations=1)
    assert validate(store, _request(key)).valid
    response = validate(store, _request(key, account_login="99999999"))
    assert not response.valid
    assert response.state is LicenseState.ACTIVATION_LIMIT


def test_06_wrong_broker_server_is_denied(store: LicenseStore) -> None:
    """The binding is (LOGIN, SERVER) — the same login on another broker is a
    different activation."""
    key, _ = _license(store, activations=1)
    assert validate(store, _request(key)).valid
    response = validate(store, _request(key, account_server="Other-MT5"))
    assert not response.valid
    assert response.state is LicenseState.ACTIVATION_LIMIT


def test_07_activation_limit_exceeded_is_denied(store: LicenseStore) -> None:
    key, _ = _license(store, activations=2)
    assert validate(store, _request(key, account_login="1")).valid
    assert validate(store, _request(key, account_login="2")).valid
    third = validate(store, _request(key, account_login="3"))
    assert not third.valid
    assert third.state is LicenseState.ACTIVATION_LIMIT
    assert third.activation_status == "2/2"


def test_a_bound_account_keeps_working(store: LicenseStore) -> None:
    """Re-validation of an already-bound account must not consume a slot."""
    key, record = _license(store, activations=1)
    for _ in range(5):
        assert validate(store, _request(key)).valid
    assert store.activation_count(record.license_id) == 1


def test_version_below_minimum_is_blocked(store: LicenseStore) -> None:
    key, _ = _license(store, minimum_version="2.00")
    response = validate(store, _request(key, ea_version="1.00"))
    assert not response.valid
    assert response.state is LicenseState.VERSION_BLOCKED


def test_13_the_full_key_is_never_returned_or_logged(
    store: LicenseStore,
) -> None:
    key, _ = _license(store)
    response = validate(store, _request(key))
    blob = str(response.to_json())
    assert key not in blob
    assert mask_key(key) in response.message
    assert "***" in response.message


def test_masking_keeps_only_the_outer_groups() -> None:
    masked = mask_key("RC5-ABCDE-FGHJK-MNPQR-STVWX")
    assert masked == "RC5-ABCDE-***-STVWX"
    assert "FGHJK" not in masked and "MNPQR" not in masked


# ---------------------------------------------------------------------------
# 08 / 09 / 10 — the lease and the MANAGE_ONLY rule, in the MQL5 source
# ---------------------------------------------------------------------------


def test_08_and_09_lease_grace_and_expiry_are_implemented() -> None:
    """Server unreachable + valid lease -> GRACE; expired lease -> no entries."""
    src = _ea()
    assert "RC5_LIC_SERVER_UNREACHABLE" in src
    body = src.split("int RC5EvaluateLicense(", 1)[1][:1200]
    assert "RC5LoadLease(" in body
    assert "RC5_LIC_GRACE" in body
    # the grace branch is guarded by an unexpired lease, not by unreachability
    assert "until > TimeCurrent()" in body


def test_the_lease_is_bound_to_its_exact_context() -> None:
    """A lease must not be copyable to another account, server or version."""
    src = _ea()
    body = src.split("string RC5LeaseFingerprint(", 1)[1][:600]
    for bound in (
        "ACCOUNT_LOGIN",
        "ACCOUNT_SERVER",
        "RC5_PRODUCT_ID",
        "RC5_EA_VERSION",
    ):
        assert bound in body, bound
    # and a mismatched fingerprint is treated as NO lease
    load = src.split("datetime RC5LoadLease(", 1)[1][:800]
    assert "fingerprint != RC5LeaseFingerprint()" in load
    assert "return 0;" in load


def test_10_A_LICENCE_FAILURE_NEVER_ABANDONS_AN_OPEN_TRADE() -> None:
    """THE invariant. The licence gate is on the OPEN path only.

    `CloseRC5Position` must have NO licence check: a customer whose
    subscription lapses mid-trade keeps their stop, their target and their
    approved invalidation exits. An unmanaged live position would be a worse
    outcome than piracy.
    """
    src = _ea()

    submit = src.split("bool SubmitOrder(", 1)[1]
    submit = submit[: submit.index("bool CloseRC5Position(")]
    assert "RC5LicenseAllowsNewEntries()" in submit

    close = src.split("bool CloseRC5Position(", 1)[1]
    close = close[: close.index("void RC5OnTerminalEvent(")]
    assert "RC5LicenseAllowsNewEntries" not in close
    assert "g_licenseState" not in close
    assert "InpLicenseKey" not in close


def test_the_manage_only_state_is_reported_not_silent() -> None:
    src = _ea()
    assert "LICENSE_MANAGE_ONLY_" in src
    assert "open positions keep" in src


# ---------------------------------------------------------------------------
# 11 / 12 — the tester bypass, and its isolation from live
# ---------------------------------------------------------------------------


def test_11_and_12_the_bypass_requires_tester_AND_the_input() -> None:
    """On a live chart the input alone must do nothing."""
    src = _ea()
    assert "input bool   InpLicenseTesterBypass   = false;" in src
    body = src.split("int RC5EvaluateLicense(", 1)[1][:400]
    match = re.search(
        r"if\(MQLInfoInteger\(MQL_TESTER\)\s*&&\s*InpLicenseTesterBypass\)", body
    )
    assert match, "the bypass must require BOTH conditions"
    # and there is exactly ONE place that RETURNS the bypass state, so there
    # is no second, unguarded route into it
    returns = re.findall(r"return RC5_LIC_TESTER_BYPASS;", src)
    assert len(returns) == 1, returns


def test_no_secret_is_embedded_in_the_ea() -> None:
    """The EA is an untrusted client and is built like one."""
    code = " ".join(
        line.split("//", 1)[0] for line in _ea().splitlines()
    ).lower()
    for forbidden in ("pepper", "api_key", "apikey", "secret", "password", "token"):
        assert forbidden not in code, forbidden


# ---------------------------------------------------------------------------
# the two state vocabularies must not drift apart
# ---------------------------------------------------------------------------


def test_the_mql5_and_python_license_states_agree() -> None:
    """The two vocabularies must not drift apart.

    `LICENSE_UNKNOWN` is MQL5-only on purpose: it is the defensive default of
    the name switch, never a state the service can return. Asserted explicitly
    rather than excluded quietly.
    """
    src = _ea()
    in_ea = set(re.findall(r'return "(LICENSE_[A-Z_]+)";', src))
    in_python = {state.value for state in LicenseState}
    assert in_ea - in_python == {"LICENSE_UNKNOWN"}, in_ea - in_python
    assert in_python - in_ea == set(), in_python - in_ea
    # and it really is only the fallback
    assert 'return "LICENSE_UNKNOWN";' in src.split("switch(s)", 1)[1][:900]


def test_licensing_is_refreshed_on_a_timer_not_on_every_tick() -> None:
    """Trading decisions must not block on an HTTP round trip."""
    src = _ea()
    assert "void OnTimer()" in src
    assert "EventSetTimer(" in src and "EventKillTimer()" in src
    tick = src.split("void OnTick()", 1)[1]
    assert "RC5RefreshLicense" not in tick
    assert "WebRequest(" not in tick


# ---------------------------------------------------------------------------
# what the Strategy Tester actually does — measured, then locked
# ---------------------------------------------------------------------------


def test_the_tester_message_does_not_assert_a_cause_it_cannot_know() -> None:
    """err 4014 is ERR_FUNCTION_NOT_ALLOWED, which MetaTrader returns BOTH for
    a URL that is not allow-listed and for a context where WebRequest is
    unavailable. Observed in the tester AND on a normal chart, with the URL
    unlisted in both.

    An earlier version of this message told the tester user that MetaTrader
    forbids WebRequest there, stated as fact. The evidence never separated the
    two causes. The message must report what happened and give the action that
    resolves it, without claiming to know why.
    """
    src = _ea()
    online = src.split("int RC5ValidateLicenseOnline(", 1)[1]
    online = online[: online.index("int RC5EvaluateLicense(")]

    assert "MQLInfoInteger(MQL_TESTER)" in online, (
        "the unreachable message must distinguish the tester from a live chart"
    )
    tester_branch = online.split("MQLInfoInteger(MQL_TESTER)", 1)[1][:400]
    assert "InpLicenseTesterBypass" in tester_branch
    assert "Tools > Options" not in tester_branch, (
        "in the tester the actionable fix is the bypass, not the allow-list"
    )
    for asserted_cause in ("does not permit", "cannot be validated", "forbids"):
        assert asserted_cause not in tester_branch, (
            f"the message asserts a cause the error code cannot establish: "
            f"{asserted_cause}"
        )
    # and a live chart still gets the allow-list advice, because there it works
    assert "Tools > Options" in online


# ---------------------------------------------------------------------------
# the endpoint itself, over a real socket
# ---------------------------------------------------------------------------


@pytest.fixture
def endpoint(store: LicenseStore):  # type: ignore[no-untyped-def]
    """A real server on an ephemeral port. Worth the socket: the handler is
    where a public deployment actually fails."""
    import json as _json
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    from licensing.server import build_handler

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(store))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    def call(path: str, payload: dict[str, object] | None = None):  # type: ignore[no-untyped-def]
        data = _json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            base + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST" if data is not None else "GET",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as handle:
                return handle.status, _json.loads(handle.read())
        except urllib.error.HTTPError as exc:
            return exc.code, _json.loads(exc.read())

    try:
        yield call
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_the_health_endpoint_answers_and_reveals_nothing(endpoint) -> None:  # type: ignore[no-untyped-def]
    status, body = endpoint("/v1/health")
    assert status == 200
    assert body == {"status": "ok"}, "a health check is not a status page"


def test_unknown_paths_are_not_a_map_of_the_service(endpoint) -> None:  # type: ignore[no-untyped-def]
    assert endpoint("/")[0] == 404
    assert endpoint("/v1/licenses")[0] == 404
    assert endpoint("/admin", {})[0] == 404
    assert endpoint("/v1/licenses/create", {})[0] == 404


def test_a_real_validation_round_trip(endpoint, store: LicenseStore) -> None:  # type: ignore[no-untyped-def]
    key, record = _license(store)
    status, body = endpoint(
        "/v1/licenses/validate",
        {
            "license_key": key,
            "product_id": "RC5-EA",
            "ea_version": "1.00",
            "account_login": LOGIN,
            "account_server": SERVER,
        },
    )
    assert status == 200
    assert body["valid"] is True
    assert body["state"] == "LICENSE_VALID"
    assert body["license_id"] == record.license_id
    assert key not in _json_text(body), "the key came back over the wire"


def _json_text(body: object) -> str:
    import json as _json

    return _json.dumps(body)


def test_a_malformed_body_does_not_crash_the_endpoint(endpoint) -> None:  # type: ignore[no-untyped-def]
    """A public endpoint meets garbage on day one."""
    assert endpoint("/v1/licenses/validate", {})[0] == 200
    status, body = endpoint("/v1/licenses/validate", {"license_key": None})
    assert status == 200
    assert body["valid"] is False
    # and the service is still alive afterwards
    assert endpoint("/v1/health")[0] == 200


def test_the_server_is_threaded() -> None:
    """Single-threaded, one half-open client blocks every other customer."""
    src = Path(_REPO / "licensing" / "server.py").read_text(encoding="utf-8")
    assert "ThreadingHTTPServer" in src
    # "ThreadingHTTPServer(" CONTAINS "HTTPServer(", so match the word itself
    assert not re.search(r"(?<![A-Za-z])HTTPServer\(", src), (
        "a bare HTTPServer is single-threaded"
    )


def test_the_server_refuses_to_start_without_the_pepper() -> None:
    src = Path(_REPO / "licensing" / "server.py").read_text(encoding="utf-8")
    assert "RC5_LICENSE_PEPPER" in src
    assert "raise SystemExit" in src
    # and it binds localhost unless told otherwise
    assert 'host: str = "127.0.0.1"' in src
