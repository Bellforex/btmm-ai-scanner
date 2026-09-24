# RC5 LICENSING — WHAT WAS ACTUALLY EXERCISED, AND WHAT IS NOT DONE

Measured on 2026-09-24 against the real HTTP server and the real MetaTrader
terminal. Nothing in this file is inferred from reading code.

---

## 1. THE OPERATIONAL CYCLE — PASSED, OVER REAL HTTP

`licensing.server` on `127.0.0.1:8713`, a real SQLite store, a real demo
licence, bound to the author's real MT5 account identity on `Exness-MT5Real10`
(account number deliberately not recorded here). Every step below was an HTTP request, not a function call:

| step | result |
| --- | --- |
| create licence | `LIC-20260924-2BR03`, key shown once, masked thereafter |
| validate | `valid=true` `LICENSE_VALID` activations `1/1` |
| **revoke** | status → `REVOKED` |
| validate again | `valid=false` **`LICENSE_REVOKED`** |
| **reactivate** | status → `ACTIVE` |
| validate again | `valid=true` `LICENSE_VALID` activations `1/1` — slot not double-consumed |

The revoke took effect on the very next validation. The reactivate restored the
existing binding rather than burning a second activation, which is the
behaviour a support desk needs when it un-suspends someone by mistake.

**The server logged the masked key only.** No plaintext key appears in any log
line, any response body, or the database.

---

## 2. THE FINDING THAT CHANGES A COMMERCIAL CLAIM

> **MetaTrader does not permit `WebRequest` inside the Strategy Tester.**

Measured, not assumed. With a real reachable server, a real key and a correct
URL, the tester run produced:

```
RC5LIC RC5-HYQVJ-***-2BR03 server unreachable (http=-1 err=4014)
RC5LIC ... state LICENSE_INVALID -> LICENSE_SERVER_UNREACHABLE
       | newEntries=BLOCKED | openPositionsUnaffected=TRUE
```

`4014` is `ERR_FUNCTION_NOT_ALLOWED`, and the server's own access log confirms
**it never received a request from MetaTrader** — while receiving the
command-line requests made seconds earlier from the same machine. The call does
not leave the terminal.

Three consequences, stated plainly:

1. **A licence cannot be validated in the Strategy Tester. Ever.** No
   allow-list entry, no URL, no setting changes this. It is a platform rule.
2. **Therefore back-testing is effectively unlicensed.** A customer who sets
   `InpLicenseTesterBypass = true` can back-test without a valid licence. This
   is not a defect that can be fixed; it is the reason the bypass exists.
   Licensing controls **live execution**, which is where the value is, and that
   is the honest claim to make.
3. The EA's behaviour under the failure was correct: `SERVER_UNREACHABLE`, no
   usable lease, **new entries BLOCKED**, and `openPositionsUnaffected=TRUE`.
   It did not fail open.

The error message was changed after this measurement. Previously it told a
tester user to allow-list the URL — advice that cannot work there and would
have generated support calls. It now names the platform limitation and points
at the bypass input.

---

## 3. LICENSING IS NON-INVASIVE — PROVEN BY REPETITION

The acceptance run was repeated after the licensing block was added and after
the error-message change:

* final balance **9,907.70 USD** — identical to the pre-licensing baseline;
* both golden setups **EXECUTED**;
* all four deny reasons fired exactly as before
  (`CONFIRMATION_PROXIMITY_INVALID`, `SPREAD_TO_RISK_INVALID`,
  `SIGNAL_ALREADY_EXECUTED`, `SYMBOL_POSITION_ACTIVE`);
* the only new journal output is two `RC5LIC` lines carrying a masked key.

Licensing did not move a single trading decision.

---

## 4. NOT DONE — AND IT NEEDS THE AUTHOR, NOT MORE CODE

> **There is no public licence endpoint deployed.**

`https://license.bellforex.app/v1/licenses/validate` is the **default value of
an input**. It is a placeholder. Nothing is hosted there.

Everything verified above ran against `127.0.0.1`. That proves the software;
it does not give a customer on another machine anything to reach.

To go live, three things are needed that only the author can supply:

| | |
| --- | --- |
| **domain** | a hostname you control, with a DNS record |
| **TLS** | a valid HTTPS certificate — MT5 `WebRequest` over plain HTTP to a public host is not acceptable for a commercial product |
| **host** | somewhere the process runs continuously, and an `RC5_LICENSE_PEPPER` set in that environment |

And one operational step at the customer's end: the endpoint host must be added
to **Tools → Options → Expert Advisors → Allow WebRequest for listed URL**. The
installation guide must say this, because nothing else will.

Until that endpoint exists, every live licence check returns
`LICENSE_SERVER_UNREACHABLE`, and — with no prior lease — **the EA will not open
new positions**. That is the designed failure direction, but it means the
endpoint is a hard prerequisite for selling the EA, not a nicety.

---

## 5. THE SECURITY CLAIM, IN THE WORDS THAT ARE TRUE

The target is **commercial-grade controlled access**, not uncrackability.

What is genuinely bought: keys cannot be guessed (100 bits); a stolen database
yields no working keys (peppered HMAC-SHA256); a licence can be revoked
centrally and stops on the next check; one key cannot quietly run on many
accounts (bound to MT5 login **and** broker server); no secret of any kind is
embedded in the EX5 — a decompiler yields the endpoint URL and nothing else.

What is not: an EX5 runs on the customer's machine, and a determined party can
patch a binary they possess. Nothing in this design pretends otherwise.

And the rule that outranks all of it — **a licence failure never abandons an
open trade** — is enforced structurally: the gate exists only on the open path,
and a test asserts `CloseRC5Position` contains no licence reference at all.
