# RC5 LICENCE ADMIN — EVENT RUNBOOK

**ADMIN ONLY. This folder is never given to a customer.**

## 0. The one secret

`RC5_LICENSE_PEPPER` is a server-side secret. It is **not** in the repository,
**not** in the EX5, and must not be pasted into chat, a ticket or a slide.

```bash
export RC5_LICENSE_PEPPER='<long random string, generated once, backed up>'
```

If the pepper is lost, **every existing licence stops validating** — the stored
hashes become unverifiable. Back it up before the event.

## 1. Start the service

```bash
python -m licensing.server --db licensing/licenses.db --port 8713
```

Put TLS in front of it (nginx / Caddy / Cloudflare) so the public URL is
`https://license.bellforex.app/v1/licenses/validate` — the address the EA's
default input points at and that customers allow-list in MetaTrader.

It binds `127.0.0.1` by default so an accidental run is not world-reachable.

## 2. Create a licence

```bash
python -m licensing.admin create --customer "Jane Doe" --email jane@x.com --days 30
```

The key prints **once** and is never stored.

> **Copy it into the customer registry and give it to the customer
> immediately.** It cannot be recovered — that is deliberate, and it is why a
> stolen database yields no working keys.

Useful flags: `--activations N` (default 1), `--min-version`, `--notes`.

## 3. Day-to-day

```bash
python -m licensing.admin list
python -m licensing.admin show LIC-...
python -m licensing.admin activations LIC-...
python -m licensing.admin revoke LIC-...
python -m licensing.admin suspend LIC-...
python -m licensing.admin reactivate LIC-...
python -m licensing.admin expiry LIC-... --days 30
```

**Revoke is not instant on the customer's terminal.** The EA re-checks on a
timer (~45 min) and may hold a cached lease for up to 12 hours. Worst case a
revoked licence opens no new trades within about 12 hours. If you need it
faster, shorten `InpLicenseLeaseHours` in future builds — do not shorten it
below a conference wifi outage.

## 4. The event demo licence

Create a **separate short-lived** licence for the demonstration:

```bash
python -m licensing.admin create --customer "EVENT DEMO" --email demo@bellforex \
    --days 2 --notes "event demo only — revoke after"
```

**Never demo with a customer's production licence.** Revoke the demo licence
after the event.

## 5. When a customer changes broker or account

A licence binds to **login + server**. A different login *or* a different
broker is a new activation.

* raise `--activations`, or
* create a replacement licence and revoke the old one.

Check what is bound before deciding:

```bash
python -m licensing.admin activations LIC-...
```

## 6. What the customer gets, and what they never get

| give | never give |
| --- | --- |
| `RC5_EA.ex5` | `RC5_EA.mq5` or any source |
| their licence key, once | the pepper |
| `INSTALL.md` | the licence database |
| their licence **ID** for support | admin CLI or server |

## 7. Support triage

Ask for the **licence state from their Experts log** — not their key.

| state | meaning | action |
| --- | --- | --- |
| `LICENSE_VALID` | fine | — |
| `LICENSE_GRACE` | server unreachable, cached lease still valid | check the service |
| `LICENSE_SERVER_UNREACHABLE` | URL not allow-listed, or service down | INSTALL.md step 2 |
| `LICENSE_EXPIRED` | past expiry | `expiry --days N` |
| `LICENSE_REVOKED` | revoked centrally | intentional? |
| `LICENSE_ACTIVATION_LIMIT` | key already bound elsewhere | `activations`, then decide |
| `LICENSE_VERSION_BLOCKED` | EA older than the licence minimum | send the current EX5 |
| `LICENSE_INVALID` | key not recognised, or suspended | re-check transcription |

**In every case, an open trade of theirs is still being managed.** Say so — it
is the first thing a worried customer wants to know.
