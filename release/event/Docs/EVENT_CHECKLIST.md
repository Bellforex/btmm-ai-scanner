# EVENT DAY — OPERATING CHECKLIST

## Before the doors open

- [ ] `RC5_LICENSE_PEPPER` exported, and **backed up somewhere else**
- [ ] licensing service running behind TLS; hit `/v1/licenses/validate` once
- [ ] event demo licence created (short expiry, marked as demo)
- [ ] scanner publication prepared — **not published** until the author says so
- [ ] access registry open and writable
- [ ] `release/event/` copied to the machine you will actually use
- [ ] demo journal/screenshots captured locally so nothing depends on wifi

## Per customer — scanner

1. payment recorded
2. **exact TradingView username** taken
3. **read it back and confirm the spelling**
4. Manage Access → add user → set expiry
5. confirm the user appears in the access list
6. registry → `TV_GRANTED`

## Per customer — EA

1. take **MT5 login and broker server**
2. `python -m licensing.admin create --customer "..." --email ... --days N`
3. give the key to the customer **and record the licence ID** in the registry
4. send `RC5_EA.ex5` + `INSTALL.md`
5. remind them of the WebRequest allow-list step — it is the single most common
   support call
6. registry → `EA_GRANTED`

## Say this, not that

| say | not |
| --- | --- |
| commercial-grade controlled access | uncrackable |
| it marks where structure was decided | it predicts price |
| we have not measured profitability | it is profitable |
| verified in the Strategy Tester | live-tested |
| access is per TradingView account | here is a shared link |

## If asked for source

No. Not the Pine, not the MQ5. Invite-only publication and EX5-only
distribution are the product's protection, and one exception undoes both.

## After the event

- [ ] revoke the demo licence
- [ ] reconcile the registry against Manage Access and `admin list`
- [ ] back up `licenses.db` **and** the pepper, separately
