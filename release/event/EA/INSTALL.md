# RC5 EA — Installation

You received **one file**: `RC5_EA.ex5`. That is the whole product; there is no
source file and none will be supplied.

## 1. Install

1. In MetaTrader 5: **File → Open Data Folder**
2. go to `MQL5\Experts`
3. create a folder `RC5` and copy `RC5_EA.ex5` into it
4. in MetaTrader: **right-click Navigator → Refresh**

`RC5 EA` now appears under **Expert Advisors → RC5**.

## 2. Allow the licence check

The EA validates your licence over HTTPS. MetaTrader blocks web requests until
you allow the address:

1. **Tools → Options → Expert Advisors**
2. tick **Allow WebRequest for listed URL**
3. add: `https://license.bellforex.app`
4. **OK**

Without this the EA reports `LICENSE_SERVER_UNREACHABLE` and will not open new
positions.

## 3. Attach and enter your key

1. drag **RC5 EA** onto a chart
2. on the **Inputs** tab, paste your key into **InpLicenseKey**
   (format `RC5-XXXXX-XXXXX-XXXXX-XXXXX`)
3. **OK**

The Experts log shows the licence state on start:

```
RC5LIC RC5-ABCDE-***-PQRST LICENSE_VALID | newEntries=ALLOWED
```

## 4. Your licence is bound to your account

A licence binds to your **MT5 login AND your broker server**. Moving computers
is fine. Changing account or broker needs a new activation — contact support.

## 5. What happens if your licence lapses

**Your open trades are never abandoned.** If the licence expires, is revoked,
or the server is unreachable beyond the grace window, the EA stops opening
**new** positions and keeps managing existing ones — stop loss, take profit and
its normal invalidation exits all continue.

The log says so explicitly:

```
RC5LIC ... new entry BLOCKED (LICENSE_EXPIRED); open positions keep their
SL, TP and approved invalidation exits
```

## 6. Offline grace

If the licence server is briefly unreachable, a cached authorization keeps the
EA trading for up to **12 hours**. Beyond that, no new positions until it can
validate again. The cache is tied to your key, account, server and EA version,
so it cannot be copied elsewhere.

## 7. Trading is OFF until you turn it on

`InpExecutionEnabled` defaults to **false**, and live trading additionally
requires `InpAllowLiveExecution`. Both are deliberate: the EA will not trade
until you decide it should.

## Support

Quote your **licence ID** (not your key) and the licence state from your log.
Never send your full key to anyone, including support — the masked form is
enough.
