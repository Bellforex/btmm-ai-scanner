# BTRC-V1 — P6→P5 transport: real-data parity

Status: **6/6 input identity, OLD 30/30 EXACT, NEW 156/156 EXACT**
Branch: `pine-p4-btmm`
Captured: 2026-09-04, FX:XAUUSD M15, TradingView account bellcare1994

---

## 1. The capture

Extended `P6 ATOMIC PARITY` (sha256 `bb7e28a4f3fe01c68b0f65c58bf557a9e5882be73dec7fcec9070e776418a04c`)
attached live alongside extended `P6 DEV`, capture mode `ALL`, downloaded via
TradingView's Pine Logs → Download logs (5,033,968 bytes,
`artifacts/p6x_capture/atomic_all_raw_log.csv`, gitignored, re-derived by
`tests/unit/test_p6x_transport_real_parity.py`).

The log holds many re-emissions — TradingView re-runs the realtime execution
periodically under load, exactly the pattern
`BTRC_V1_P6_P5X_RESOURCE_ATTRIBUTION.md` already documented — and every repeat
at a given timestamp was verified byte-identical before selection, which is
the strongest evidence yet that the extension is deterministic across restarts.

```
capture_id    f2dfa1152ad06d1e05ba2f99c58dcbd0
feed          FX:XAUUSD (FXCM)      host M15, dataset 1800, confirmed 1799
envelopes     semanticMin 1250  request 1251  host 1800     aliasHits 0
```

Because raw candles for six timeframes arrive across several seconds, the raw
captures selected are the LATEST complete one per timeframe (not all
sharing one literal snapshot timestamp) — each individually locked against the
snapshot's five-dimension identity before use, per the existing capture
contract's own rule that digests alone are insufficient.

```
TF    rows   first            last             ih1         ih2
W1    1250   1031522400000    1787522400000     27898685    408967381
D1    1250   1636063200000    1788386400000    801921670    488898722
H4    1250   1762916400000    1788458400000    799783556    520561637
H1    1250   1781874000000    1788480000000    959482010    224623277
M15   1799   1786097700000    1788482700000      9821948    713028876
M5    1250   1787916900000    1788483900000    422258999    314950646
```

## 2. 6/6 real input identity

Every raw capture matches the snapshot exactly on all five dimensions (rows,
first, last, H1, H2). `tests/unit/test_p6x_transport_real_parity.py::test_6_of_6_raw_input_identity`.

## 3. OLD 30/30 — unchanged at the new anchor

The five surfaces the closed P6 already transports (`SWINGS`, `EQUAL`, `DISP`,
`P2_TRANS`, `P2_STATE`), replayed with the SAME `p6_projection_oracle` /
`p6_real_data_replay` machinery the original closure used — untouched by this
campaign — against Pine's live output at this new, later anchor:

```
30 / 30 EXACT
```

This is the proof the additive extension did not disturb P6's original
semantics: the same production code, run over the same closed pipeline,
produces the same surfaces Pine reports, on a live capture taken AFTER the
extension shipped.

The **historical** frozen artifact and its digest (H1 74231825 / H2 124714621,
`tests/unit/test_p6_real_data_parity.py`) are independently reconfirmed —
**61/61 passed**, unmodified — rather than superseded by this new anchor.

## 4. NEW 156/156 — the 26-field real differential

For every one of the six timeframes, the 26 `P5TransportExt` fields Pine
emitted live (`P5X|<TF>|...`) are compared against
`tests/parity_support/p6x_transport_replay.replay_transport_series` — an
INDEPENDENT, BLIND Python oracle that:

* calls the exact production detectors the closed oracle calls
  (`_confirmed_swings`, `detect_displacement_observations`,
  `analyze_structure_state`) over the exact same window and `injected_atr`
  bridge as `p6_projection_oracle.project_terminal`, never a second windowing
  implementation;
* feeds their FULL output — not the closed oracle's reduced scalars — into
  `p5_transport_oracle.reduce_authoritative`, the same 26-field reducer proven
  against the authoritative engines and the mutation campaign in
  `tests/unit/test_p5_transport_reduction.py` / `test_p5_transport_mutations.py`.

```
26 fields x 6 timeframes = 156 comparisons
0 mismatches
```

Sample (W1, the deepest history — a 24-year-old first bar):

```
Pine:   stateAvailT=1771623900000 contStreak=9 priorOppStreak=0 exhaustFlag=1
        transWindowCount=4 trans1..4Type=1,1,1,1 lastTransAvailT=1766785500000
        dispWindowCount=3 disp1Ratio=0.5547040275 disp2Ratio=1.2769419138
        disp3Ratio=1.0441405358 dispClsAtTrans=1
        pbImpulsePrice=4890.67 pbOriginPrice=4097.98 pbPullbackPrice=3941.75
        pbValid=true
Python: identical on every field (floats within 1e-6, matching Pine's
        display-precision truncation, not a real divergence)
```

## 5. The transport digest — Python-derived, not Pine==Python

Unlike the closed P6 surface, the atomic twin's capture section was
deliberately left untouched (per the resource-attribution ownership boundary),
so Pine never folds a digest over the 26 new fields. The values below are a
**regression fingerprint**, computed once from the field-exact real capture, so
a future change that moved any of the 156 already-verified values would move
this number too — not a second independent Pine↔Python proof, which the
field-level 156/156 already is, and which this campaign's own capture-parser
doctrine names as authoritative over any digest.

```
TF     H1          H2
W1     992954022   143829031
D1     893013043   346300067
H4     978144049   336125251
H1     918084312   633265513
M15    57476645    768475044
M5     774659550   357379521

GLOBAL 587324251   795923623
```

## 6. Gate

```
P6X_INPUT_IDENTITY_6_OF_6          TRUE
P6X_OLD_SURFACES_30_OF_30          TRUE   (new anchor)
P6_HISTORICAL_30_OF_30             TRUE   (unmodified, reconfirmed)
P6X_NEW_TRANSPORT_156_OF_156       TRUE
P6X_TRANSPORT_REAL_PARITY          VERIFIED
```

**Not claimed here**: that the transport digest is independently Pine-verified
(see §5). **Not claimed here**: anything about P5's own arithmetic, bands, or
calibration — this closes the boundary Pine hands data across, not what P5
does with it once received.
