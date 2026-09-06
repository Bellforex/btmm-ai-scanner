# TradingView / Browser Operational Notes

Non-semantic operational quirks of TradingView's web UI and this project's
browser-automation environment, discovered during P5–P10 development.
**None of these are Pine scanner defects.** They are platform/tooling
behavior; this document exists so a future session (or a human operator)
recognizes them immediately instead of re-diagnosing them as bugs.

## Account

- TradingView username/account: `bellcare1994`.
- Chart layout name: `bellforex` (a saved layout, not a username).
- Canonical chart: `/chart/6cu1b2O7/`.
- Plan: **Basic**. Hard limits that affect this project directly:
  - **2 indicators per chart maximum.** Adding a third requires removing
    one first.
  - **1 saved chart layout.**
  - **0 technical alerts available.** `alert()` calls in Pine execute and
    can be observed via Pine Logs, but creating an actual TradingView
    Alert object (the bell-icon "Create Alert" flow) is blocked by the
    plan, not by the scanner. See "P8 alert delivery" below.

## Background-tab / connection limits

The Basic plan caps **2 live data connections**, not just 2 indicators.
A background browser tab on this chart does not receive live updates —
work from exactly one active tab at a time; a second tab left open in the
background can silently go stale and should be closed rather than trusted.

## Renderer hang ("300x150 canvas hang")

The chart widget frequently boots (fresh navigation, or after certain
Object Tree / Settings-dialog interactions) with every canvas stuck at a
300×150 default — spinner clears, legend shows correct data, but the price
axis/candles never paint and appear blank. Not a Pine fault; the
containers are sized correctly but the widget's internal pane stays at a
stale width. Recovery, using TradingView's own API:

```js
const c = window._exposed_chartWidgetCollection;
const w = typeof c.activeChartWidget.value === 'function'
        ? c.activeChartWidget.value() : c.activeChartWidget;
const r = document.querySelector('.chart-widget').getBoundingClientRect();
c.resetLayoutSizes();
w.resize(Math.round(r.width), Math.round(r.height));
w._adjustSize();
w.paint();
```

If this alone doesn't restore correct candle rendering (price scale stuck
at an old/wrong range), the underlying model data is usually already
correct (`mainSeries().priceScale().priceRange()` reports the right
values) — the fix above just needs to be re-run once more, or the tab
needs a full reload (see next item).

## Viewport collapse / cross-session paint corruption

A tab that has accumulated many DOM interactions this session can develop
persistent paint corruption (e.g. a previously-hidden chart Text
annotation bleeding through as a translucent overlay across the candles).
This is NOT cross-tab GPU compositing — it reproduces even with only one
tab open. Recovery: a full page reload of the SAME tab (not a new tab)
clears it. If reloading trips a "Leave site?" unsaved-changes dialog,
save the chart layout first (so the state you want to keep survives the
reload) rather than discarding with `force: true`.

## Un-hidden legacy chart annotations

Several legacy dev-notes `Text`/`Rectangle`/`Trendline`/`Horizontal ray`
drawing objects exist on the canonical chart from early development. Most
are hidden (Object Tree eye-slash icon); occasionally one reverts to
visible (observed once, cause not isolated — possibly a save captured
before a Hide action fully committed) and reappears as large overlaid
text obscuring the chart. Fix: Object Tree → right-click the object →
**Hide** (reversible). Do not delete these; they are the same objects
across dev-history and their state should be treated as we found it.

## The Pine Editor panel and the automation viewport

This project's browser-automation pane sometimes renders at a fixed width
(observed 1558px) narrower than the actual page viewport (observed up to
1780px). When the Pine Editor is toggled open, its panel — and
occasionally the Editor-open toggle button itself — can render past the
edge of what the automation screenshot/click coordinate frame covers,
making it appear "not open" when it actually is. Diagnose via JS
(`document.body.scrollWidth` vs the screenshot's reported width) and, if
confirmed, drive the relevant element directly (`element.click()`) rather
than via coordinate-based clicking, since coordinates outside the visible
frame are rejected.

## Pine Editor script duplication ("Make a copy...")

The reliable way to create a new saved script from a closed DEV source
without re-pasting text (and risking a stale-clipboard mismatch) is Pine
Editor → title dropdown → **Make a copy...**, which prompts for a new
script name and duplicates the source exactly. The **saved script name**
this sets is independent of the **on-chart title** (the string literal
inside the source's `indicator(...)` call) — both must be updated if the
on-chart legend should show the new name.

## Object Tree "Remove" vs. the legend trash icon

**Permanent rule for this whole project.** Detaching an indicator from
the chart must always be done via Object Tree → right-click the
indicator row → **Remove**. The trash icon that appears on the chart
legend row (when an indicator is selected) does **not** just detach it
from the chart — in a past session it permanently deleted the saved
script from the TradingView script library. Recovery required re-pasting
the source from the local repository file and re-saving under the
auto-detected name. Never use the legend trash icon.

## Exact source transfer (clipboard round-trip)

To push a canonical local `.pine` file into a TradingView-saved script
byte-for-byte:

1. PowerShell: `Get-Content -Raw -Encoding UTF8 <path> | Set-Clipboard`.
2. In the Pine Editor: click into the code area, `Ctrl+A`, `Ctrl+V`.
3. **Verify by position, not by re-reading clipboard back** (`Get-Clipboard`
   has hung this project's PowerShell tool more than once): press
   `Ctrl+End` and confirm the reported cursor line equals
   `(file line count) + 1`, column 1 — this is a mechanical proof the
   full file landed, without a hash round-trip through a flaky clipboard
   read.
4. `Ctrl+S` to save.

## Synthetic pan/zoom does not reach the chart canvas

Mouse-wheel `scroll` and drag actions issued through this project's
browser-automation tool do not register on the TradingView chart canvas —
repeated scroll calls leave the visible bar range pixel-identical. This
is a tooling limitation, not a Pine or platform defect. Pan/zoom
acceptance in this project is instead verified via the chart's own
`timeScale()` API (`setBarSpacing`, `setRightOffset`,
`scrollToRealtime`), which is a legitimate equivalent: it exercises the
same rendering/anchoring code path a real drag would, and every
acceptance pass in this project's closure docs that mentions "pan/zoom"
means this programmatic method unless stated otherwise.

## Compile/runtime-error verification ground truth

Screenshots are not reliable evidence of compile status (a blank canvas
from the renderer hang above can look identical to a real compile
failure). The authoritative check is the JS API:

```js
const c = window._exposed_chartWidgetCollection;
const w = c.activeChartWidget.value();
const ds = w.model().dataSources();
ds.filter(s => typeof s.isFailed === 'function' && s.title().includes('Scanner'))
  .map(s => ({ title: s.title(), isFailed: s.isFailed(), status: s.status() }));
```

`isFailed: false` and `status.type: 2` together mean a clean, current
compile with zero runtime errors.

## P8 alert delivery (platform/plan limitation, not a scanner defect)

P8's event-generation engine (five V1 event types, `alert()` calls) is
fully implemented, tested, and live-verified via Pine Logs. Actual
TradingView **technical Alert object** creation (the kind that sends a
push/email/webhook notification) requires plan capacity this account's
Basic plan does not have (confirmed via TradingView's own "0 technical
alerts" upsell dialog and a real "Alert saving failed" error). This is a
platform/plan constraint to be resolved by the account holder choosing
whether to upgrade — it is explicitly out of scope for engineering work
to route around, per this project's standing authorization rules.
