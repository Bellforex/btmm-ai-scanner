# BTRC V1 — RC1 Installation Guide

This is a technical release candidate of an analytical TradingView
indicator. It contains no order execution, no entries/SL/TP, no strategy
calls, and makes no trading recommendation. Follow these steps to install
and run it.

## 1. Open TradingView

Open the chart for the symbol you want to analyze. This release is
release-validated on **FX:XAUUSD** (the FXCM gold feed — the ticker is
`FX:XAUUSD`, not `FXCM:XAUUSD`, which does not exist). Other symbols and
providers are architecturally supported by the engine but have not been
release-validated this cycle — treat results on them as unverified.

## 2. Add the script

- Click **Indicators, metrics, and strategies** in the chart toolbar.
- Go to **My scripts** (requires the script to already be saved to your
  account — see "Obtaining the script" below if it isn't).
- Select **BTMM + POI + BTRC Scanner [RC1]**.

### Obtaining the script

If the script is not yet in your account's My Scripts library, open Pine
Editor, paste the contents of
`tradingview/btmm_poi_btrc_scanner_rc1.pine` from this repository, and
save it under the name `BTMM + POI + BTRC Scanner [RC1]`. Then add it to
the chart per step 2.

## 3. Use a supported host timeframe

Set the chart's timeframe to one of the release-validated host
timeframes:

- **M5**
- **M15**
- **H1**

Other timeframes are not release-validated; the engine does not
architecturally forbid them, but no acceptance evidence exists for them
in this release.

## 4. Keep zones enabled

The release ships with **Show POI zones** and **Show POI labels** both
ON by default, with a visible-zone cap of 12. This is the intended
default presentation — the feature the scanner exists to show. If you
have changed these in Settings, re-enable them to see the release's
intended behavior.

## 5. Alerts

The scanner's internal event engine (five informational event types:
POI activation, BTMM validation, permission entered/lost actionable,
POI terminal) is fully functional and observable via **Pine Logs** if
you enable the debug toggles in Settings. Creating an actual TradingView
**technical Alert** (the kind that sends a notification) additionally
requires your TradingView account to have available technical-alert
capacity on your plan — this is a TradingView plan limitation, not
something the script controls. Check your plan's alert quota before
expecting alert notifications to fire.

## 6. What you should see

- Candles for your chosen symbol/timeframe.
- A BTRC summary panel (top-left).
- An active-POI table (bottom-right by default).
- Colored POI zone rectangles with readable labels (e.g. "15 • SELL
  FVG") on the chart, anchored to their price/time origin.

## Not included

- No trading recommendations, no entries, no stop-loss/take-profit, no
  position sizing, no automated execution of any kind.
- No profitability claim of any kind.

See `docs/release/BTRC_V1_RC1_MANIFEST.md` for the full feature
inventory and known limitations before relying on this tool.
