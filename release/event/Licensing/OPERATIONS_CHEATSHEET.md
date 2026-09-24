# RC5 LICENCE DESK — ONE PAGE

For whoever is running the licence desk. Everything on this card is a command
you can type; nothing here needs a developer.

**Before the first customer**, open one terminal and set the pepper once:

```
set RC5_LICENSE_PEPPER=<the event pepper>
```

The pepper is the secret that makes stored hashes unusable to anyone who copies
the database. **It is never written down in this repository and never given to a
customer.** If it is lost, every licence must be reissued.

---

## THE FOUR THINGS YOU WILL ACTUALLY DO

### 1. Sell a licence

```
rc5-license create --customer "Jane Doe" --email jane@example.com --days 30
```

Prints the key **once**:

```
KEY (shown once, not recoverable): RC5-XXXXX-XXXXX-XXXXX-XXXXX
LICENSE ID: LIC-20260924-XXXXX
```

* give the **key** to the customer — WhatsApp, paper slip, whatever;
* write the **LICENSE ID** in the registry;
* **never write the key in the registry.** If it is lost, reissue — that is
  cheaper than a leaked key.

### 2. Look someone up

```
rc5-license list
rc5-license show LIC-20260924-XXXXX
rc5-license activations LIC-20260924-XXXXX
```

`activations` tells you which MT5 login and broker server the key is bound to.
That is the answer to *"my key says activation limit"*.

### 3. Turn a licence off

```
rc5-license revoke LIC-20260924-XXXXX        stops it permanently
rc5-license suspend LIC-20260924-XXXXX       stops it, reversible
rc5-license reactivate LIC-20260924-XXXXX    turns a suspended one back on
```

Takes effect on the customer's **next check**, which is within
`InpLicenseRecheckMinutes` (45 by default) — and within the lease window if
their connection is down. It is not instantaneous, and it is not meant to be.

### 4. Extend

```
rc5-license expiry LIC-20260924-XXXXX --days 30
```

---

## THE THREE QUESTIONS YOU WILL BE ASKED

**"It says LICENSE_ACTIVATION_LIMIT."**
The key is already bound to a different MT5 login or a different broker server.
Run `activations`. Either they are on the wrong account, or they are trying to
share. One licence is one (login, server) pair.

**"It says LICENSE_SERVER_UNREACHABLE."**
The terminal cannot reach the licence endpoint. Tools → Options → Expert
Advisors → **Allow WebRequest for listed URL** must contain the endpoint host.
If they had a good check earlier today, they keep trading on the lease until it
runs out.

**"It doesn't work in the Strategy Tester."**
Correct — for back-testing, set `InpLicenseTesterBypass = true`. It has no
effect on a live chart, so it cannot be used to dodge a licence on a real
account.

MetaTrader's own documentation says `WebRequest` is unavailable in the Strategy
Tester. **Do not tell a customer we proved that** — we have not. What we
observed is `err=4014`, which MetaTrader also returns for a URL that is not
allow-listed. Say "back-testing uses the bypass" and leave the cause alone.

---

## WHAT YOU MUST NEVER DO

* never ask for, write down, or accept an **MT5 password** — the licence binds
  to the account NUMBER and the server name, and needs nothing else;
* never put a licence **key** in the registry, a message log or a screenshot;
* never send anyone the `.mq5` source or the Pine source;
* never share the **pepper** or the licence database.

---

## THE ONE PROMISE TO THE CUSTOMER

A licence problem never touches an open trade. An expired, revoked or
unreachable licence blocks **new** entries only; positions already open keep
their stop, their target and their exits.

That is in the code, and it is tested. You may say it plainly.
