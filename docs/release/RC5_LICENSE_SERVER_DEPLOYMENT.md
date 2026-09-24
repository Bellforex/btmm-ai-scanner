# DEPLOYING THE RC5 LICENCE VALIDATOR

Everything the software needs is done and tested. What remains needs a machine,
a domain and a certificate — three things only the author can supply.

This is written so the deployment is about fifteen minutes, not an afternoon.

---

## WHAT YOU ARE DEPLOYING

```
   customer's MT5  --HTTPS-->  Caddy (TLS, path allow-list)
                                  |
                                  |  plain HTTP, LOOPBACK ONLY
                                  v
                          licensing.server on 127.0.0.1:8713
                                  |
                                  v
                          /var/lib/rc5/licenses.db
```

Two paths exist and nothing else:

| method | path | purpose |
| --- | --- | --- |
| `GET` | `/v1/health` | liveness. Returns `{"status":"ok"}` and nothing else |
| `POST` | `/v1/licenses/validate` | the only real endpoint |

**There is no admin endpoint.** Creating, revoking and extending licences is
done by `licensing/admin.py` on the server itself, over SSH. Nothing that
mutates a licence is reachable from the internet, which is why this is safe to
expose at all.

---

## 1. THE SECRET — get this right first

```bash
sudo mkdir -p /etc/rc5
python3 -c "import secrets; print('RC5_LICENSE_PEPPER=' + secrets.token_urlsafe(48))" \
  | sudo tee /etc/rc5/license.env > /dev/null
sudo chmod 600 /etc/rc5/license.env
sudo chown root:root /etc/rc5/license.env
```

**The pepper is what makes a stolen database useless.** It is never in the
repository, the EX5, the customer package, a log line or this document.

**If you change it, every existing licence stops validating** — the stored
hashes were computed with the old one. Set it once, back it up somewhere you
would back up a bank credential, and do not rotate it casually.

## 2. THE SERVICE

```bash
sudo useradd --system --home /opt/rc5 --shell /usr/sbin/nologin rc5
sudo mkdir -p /opt/rc5 /var/lib/rc5
# copy the repository's licensing/ package to /opt/rc5/licensing/
sudo python3 -m venv /opt/rc5/venv
sudo chown -R rc5:rc5 /opt/rc5 /var/lib/rc5

sudo cp deploy/license-server/rc5-license.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now rc5-license
sudo systemctl status rc5-license --no-pager
```

The unit binds `127.0.0.1` explicitly. **Do not change that to `0.0.0.0`.** The
validator speaks plain HTTP; the only thing that should ever reach it is the
reverse proxy on the same machine.

## 3. TLS AND THE FRONT DOOR

Point an A record for `license.bellforex.app` at the host, then:

```bash
sudo cp deploy/license-server/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Caddy obtains and renews the certificate itself. The path allow-list means a
scanner probing `/admin`, `/.env` or `/wp-login.php` is refused at the proxy and
never touches the application.

## 4. PROVE IT — five checks, in order

```bash
# 1. TLS is real and the chain validates (no -k, ever)
curl -sS -o /dev/null -w '%{http_code} %{ssl_verify_result}\n' \
  https://license.bellforex.app/v1/health
#    expect: 200 0

# 2. an unknown key is refused
curl -sS -X POST https://license.bellforex.app/v1/licenses/validate \
  -H 'Content-Type: application/json' \
  -d '{"license_key":"RC5-00000-00000-00000-00000","product_id":"RC5-EA","ea_version":"1.00","account_login":"1","account_server":"X"}'
#    expect: "valid": false, "state": "LICENSE_INVALID"

# 3. nothing else is reachable
curl -sS -o /dev/null -w '%{http_code}\n' https://license.bellforex.app/
curl -sS -o /dev/null -w '%{http_code}\n' https://license.bellforex.app/admin
#    expect: 404 and 404
```

Then, with a real licence, run **create → validate → revoke → validate →
reactivate → validate** using `licensing/admin.py` on the host. That exact cycle
has already passed locally; on the deployed host it proves the same code against
real TLS.

## 5. THE CUSTOMER'S SIDE — the step everyone forgets

MetaTrader will not make an HTTP request to a URL the user has not allow-listed.
Each customer must add the **origin** in:

> **Tools → Options → Expert Advisors → Allow WebRequest for listed URL**
>
> `https://license.bellforex.app`

If they skip it, the EA reports `LICENSE_SERVER_UNREACHABLE` and refuses new
entries. The installation guide must say this, with a screenshot, because
nothing else will tell them.

**And a limitation to state carefully.** MQL5's documentation says
`WebRequest` cannot be used in the Strategy Tester, and the tester bypass
exists for that reason. This project has **not** verified it: the tester run
returned `err=4014`, but so did a normal chart with the same unlisted URL, and
`4014` covers both "not allow-listed" and "not available here". Do not present
it as our measurement.

Either way, back-testing uses `InpLicenseTesterBypass=true`, and licensing
gates **live execution** — that part is true and is the claim to make.

---

## OPERATING IT

**Backups.** `/var/lib/rc5/licenses.db` and `/etc/rc5/license.env`, together,
in a place that is not this host. Either one alone is useless: the database
without the pepper validates nothing, and the pepper without the database is
just a random string.

**Logs.** The service prints one line per validation carrying the **masked**
key, the account and the resulting state. Keys never appear in full. Do not add
body logging to Caddy — the key travels in the body.

**Rate limiting** is the proxy's job, not the application's. The keyspace is 100
bits, so guessing is not a realistic attack; limiting is about protecting the
host, and Caddy or Cloudflare does it better than this process would.

**If the host dies**, customers with a current lease keep trading until it
expires (12 hours by default), and then stop opening new positions. Existing
positions are never abandoned. You have hours, not minutes — but not days.
