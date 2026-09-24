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

## 2. WHAT WAS MEASURED ABOUT WebRequest -- AND A CORRECTION

**An earlier version of this document claimed MetaTrader forbids `WebRequest`
inside the Strategy Tester, and said that claim was measured. It was not.**

What was actually observed, in both environments, with the URL **not** added to
Tools -> Options -> Expert Advisors -> Allow WebRequest:

| environment | result |
| --- | --- |
| Strategy Tester (`tester=1`) | `http=-1 err=4014`, server never saw the request |
| **normal terminal** (`tester=0`) | `http=-1 err=4014`, server never saw the request |

`4014` is `ERR_FUNCTION_NOT_ALLOWED`, and MetaTrader returns it both when a URL
is not allow-listed and when `WebRequest` is unavailable in the calling
context. **The two causes cannot be told apart from the error code**, and since
the URL was unlisted in both runs, the tester result is fully explained by the
allow-list alone. It never isolated a tester prohibition.

MQL5's own documentation does state that `WebRequest` cannot be used in the
Strategy Tester, so the tester bypass remains necessary. But that is a
documented platform statement, **not something this project has verified**, and
it must not be presented as our measurement.

The distinguishing experiment -- allow-list the URL, then compare a tester run
with a normal-chart run -- has **not been performed**, because the allow-list
lives in the terminal's encrypted settings and can only be set through the
Options dialog. See section 4.

What the runs *do* establish, and this part is unchanged: with no reachable
endpoint the EA **fails closed** in both environments -- `SERVER_UNREACHABLE`,
new entries BLOCKED, `openPositionsUnaffected=TRUE`. It never failed open.

The EA's tester message was rewritten accordingly. It no longer asserts a
cause; it reports what happened and gives the one action that resolves it.

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

**The allow-list is also what blocks the last unrun experiment.** It lives in
the terminal's encrypted `settings.ini` and can only be set through the Options
dialog -- there is no config-file or command-line route, so an agent cannot set
it and I did not try to drive the dialog of a terminal logged into a real-money
account. Once one checkbox is ticked by hand, a normal-chart run should reach
the server and return `LICENSE_VALID`, and the same URL in the tester then
answers whether the tester prohibition is real.

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
