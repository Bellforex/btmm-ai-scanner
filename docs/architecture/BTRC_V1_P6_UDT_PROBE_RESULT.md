# BTRC-V1 — P6 UDT transport probe: RESULT

Status: **UDT_TRANSPORT_FEASIBLE = TRUE**
Script: `tradingview/p6_udt_transport_probe.pine` (throwaway; not part of the scanner)
Saved on TradingView as: `P6 UDT TRANSPORT PROBE`
Run: 2026-09-03, FX:XAUUSD M15, host `calc_bars_count = 1800`

---

## 1. What was asked

Whether the exact shape the P5 transport extension needs — `[14 scalars, one
P5TransportExt object]` returned from each of six `request.security` contexts —
compiles and runs. The scalar alternative was already ruled out arithmetically
(6 × 34 = 204 against a combined cap of 127), so this was the gate on the whole
extension.

## 2. Result

**Both shapes work.** Compile: 0 errors. The study attached and ran.

```
PROBE|feed=FX:XAUUSD|host_tf=15|host_bars=1800
```

| TF | bars | contStreak | altCount4 | priorOppStreak | exhaustFlag | prevTransType |
|---|---|---|---|---|---|---|
| W1  | 1250 | 4 | 2 | 2 | 0 | 0 |
| D1  | 1250 | 4 | 2 | 2 | 0 | 0 |
| H4  | 1250 | 4 | 2 | 2 | 0 | 0 |
| H1  | 1250 | 4 | 2 | 2 | 0 | 0 |
| M15 | 1799 | 0 | 3 | 2 | 1 | 4 |
| M5  | 1250 | 4 | 2 | 2 | 0 | 0 |

The fallback shape, a bare object return, also works — and carries a NESTED
object with it:

```
FULL|W1|bars=1250|swings=8|price=4456.77|extNull=false
FULL|M5|bars=1250|swings=8|price=4437.69|extNull=false
```

`extNull=false` is the notable part: a `P5TransportExt` held as a field of
another UDT survived `request.security` intact. Nothing in the production design
needs that today, but it means the full-UDT fallback is genuinely available
rather than merely syntactically accepted.

## 3. Why the values are evidence and not decoration

The probe fills its fields from `seen % k`, where `seen` is that context's own
confirmed-bar count. So the table above is checkable arithmetic, not a vibe:

```
1250 % 7 = 4    1250 % 4 = 2    1250 % 3 = 2    1250 % 2 = 0    1250 % 5 = 0
1799 % 7 = 0    1799 % 4 = 3    1799 % 3 = 2    1799 % 2 = 1    1799 % 5 = 4
```

Every one of the twelve cells matches. That ties each field to the bar count of
the context that produced it, which an aliased, dropped or host-evaluated
projection could not do — the failure this campaign has actually hit before, when
six contexts all reported zero swings.

The float and price fields differentiate on the same principle: the ratio is
`close / first close in that context`, giving 14.07 (W1, whose oldest bar is from
2002) down through 2.45 (D1), 1.07 (H4), 1.05 (H1), 1.04 (M15) and 0.96 (M5).

## 4. What this licenses, and what it does not

Licensed: the production representation — 14 preserved scalar positions plus one
appended object, six contexts, 90 combined tuple elements against the cap of 127.

**Not licensed:** any claim about the SEMANTICS of the new fields. The probe
carries no P1/P2 state and its values are arbitrary by construction. Proving the
real reductions is the Python oracle's job, and then the real-data capture's.

Also not attempted: Pine's absolute UDT field ceiling. The probe used 23 fields —
at least the ~20 the audit found — which is what the production shape needs and
no more.

## 5. Envelope facts re-confirmed in passing

* five requested contexts returned **1250** confirmed bars from
  `calc_bars_count = 1251`, so the derived envelope still yields exactly the
  semantic minimum;
* the M15 host context returned **1799**, the same asymmetry the P6 closure
  recorded and explained;
* `syminfo.prefix` asserted **FX** — FXCM, per the standing feed rule.
