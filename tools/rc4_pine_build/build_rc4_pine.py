"""Build the RC4 Pine USER + PARITY files from the RC3 builds (RC3 files untouched).

    python tools/rc4_pine_build/build_rc4_pine.py

Deterministic: regenerating from the frozen RC3 sources reproduces both RC4
files byte for byte. The USER build is additionally compacted (presentation-only
refactors, developer-only outputs removed) to fit TradingView's 100256-token
compiled-code limit; the PARITY build keeps every capture stream the aligned
comparison reads.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "tradingview"
SRC = {
    "user": ROOT / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine",
    "parity": ROOT / "btmm_poi_btrc_scanner_rc3_parity_dev.pine",
}
DST = {
    "user": ROOT / "btmm_poi_btrc_scanner_rc4_user.pine",
    "parity": ROOT / "btmm_poi_btrc_scanner_rc4_parity.pine",
}


def sub(s: str, old: str, new: str, count: int = 1) -> str:
    n = s.count(old)
    assert n == count, (old[:80], n)
    return s.replace(old, new)


import sys

sys.path.insert(0, str(Path(__file__).parent))
from rc4_pine_blocks import (
    DASH,
    DRAW,
    FUNCS,
    P7_TYPES,
    P8_NEW,
    P8_OLD_END,
    P8_OLD_START,
    PUSH,
    TXT,
    VARS,
    compact_p7,
    trim_p6_user,
)

for which in ("user", "parity"):
    s = SRC[which].read_bytes().decode("utf-8")
    assert "\r\n" not in s
    s = sub(
        s,
        "var array<StructEventRec> p3Events = array.new<StructEventRec>()   // this bar's P2 breaks, for the OB leg-origin gate\n",
        "var array<StructEventRec> p3Events = array.new<StructEventRec>()   // this bar's P2 breaks, for the OB leg-origin gate\n" + VARS,
    )
    s = sub(
        s,
        "        array<TrendlineRec> tls = f_detectTrendlines(wClose, wAtr, swings, scTlAtr)\n",
        "        array<TrendlineRec> tls = f_detectTrendlines(wClose, wAtr, swings, scTlAtr)\n"
        "        fwEqs := eqs   // RC4 framework reads the same P1 clusters / trendlines\n"
        "        fwTls := tls\n",
    )
    funcs = FUNCS
    if which == "user":
        funcs = funcs.replace(
            "    fwR := f_fwRange(time_close)\n",
            "    fwR := f_fwRange(time_close)\n" + DRAW,
        )
        funcs = (
            "var array<line>  fwLines  = array.new<line>()\n"
            "var array<label> fwLabels = array.new<label>()\n" + funcs
        )
    s = sub(s, "var bool p8Primed = false\n", funcs + "\nvar bool p8Primed = false\n")
    s = sub(
        s,
        "            array.push(p8TerminalAlerted, false)\n",
        "            array.push(p8TerminalAlerted, false)\n" + PUSH,
    )
    a = s.index("            bool isTerminal = not array.get(poiFreshActive, i)\n")
    b = s.index("            if eligible\n") + len("            if eligible\n")
    s = (
        s[:a]
        + "            // RC4: a POI is evaluated until its P5 final row. Terminal = no\n"
        + "            // longer fresh, EXCEPT a first-touch mitigation stays in P5 / P8\n"
        + "            // for its BTMM interaction episode (5 bars, or an earlier true\n"
        + "            // failure); P3 still records the touch at the touch bar.\n"
        + "            if not array.get(poiP5FinalDone, i)\n"
        + "                [fwOn, fwPre, fwLoc, fwEp] = f_fwPoi(i)\n"
        + "                bool isTerminal = not array.get(poiFreshActive, i) and not (array.get(poiTermReason, i) == C_POI_TERM_MITIGATED and fwEp == 1)\n"
        + s[b:]
    )
    s = sub(
        s,
        "                int liquidityScore = f_p5LiquidityScoreConfluence(btmmValid)\n",
        "                int liquidityScore = f_p5LiquidityScoreConfluence(btmmValid)\n"
        "                // RC4 (18 canonical types): BTMM = the pre-trade cycle, a score\n"
        "                // not a gate (85 action / 55 setup only / 25 none); liquidity =\n"
        "                // framework location. Weights and permission bands unchanged.\n"
        "                if fwOn\n"
        "                    btmmScore := fwPre ? 85 : btmmValid ? 55 : 25\n"
        "                    btmmValid := fwPre\n"
        "                    liquidityScore := fwLoc\n",
    )
    s = s.replace(
        "f_p8TermReasonLabel(array.get(poiTermReason, i))",
        "f_p8TermReasonLabel(fwEp == 3 ? C_POI_TERM_INVALIDATED : array.get(poiTermReason, i))",
    )
    from rc4_fvg import apply_rc4_fvg

    s = apply_rc4_fvg(s)
    a = s.index(P8_OLD_START)
    b = s.index(P8_OLD_END, a) + len(P8_OLD_END)
    s = s[:a] + P8_NEW + s[b:]
    s = s.replace("[RC3 POI SEMANTICS DEV]", "[RC4 MARKET FRAMEWORK]").replace(
        "[RC3 PARITY DEV]", "[RC4 PARITY]"
    )
    if which == "user":
        s = sub(
            s,
            'maxDrawPerFamily = input.int(20, "Market structure: events and swings drawn", minval = 1, maxval = 200, group = grpView)\n',
            'dspTl    = input.bool(false, "Show Trendlines", group = grpView)\n'
            'dspRange = input.bool(false, "Show Consolidation / Range (high, low, midpoint)", group = grpView)\n'
            'dspLiq   = input.bool(false, "Show Liquidity (BSL / SSL pools, sweeps)", group = grpView)\n'
            'maxDrawPerFamily = input.int(20, "Objects drawn per layer", minval = 1, maxval = 200, group = grpView)\n',
        )
        # POI table: one more column with the BTMM cycle + location
        s = sub(s, "table.new(position.bottom_right, 8, ", "table.new(position.bottom_right, 9, ")
        s = sub(s, '"#|Dir|Tier|BTMM|Align|Score|Permission|State"', '"#|Dir|Tier|BTMM|Align|Score|Permission|State|Cycle / Location / Liq"')
        s = sub(
            s,
            "        for c = 0 to 7\n            table.cell(p7Pois, c, 0,",
            "        for c = 0 to 8\n            table.cell(p7Pois, c, 0,",
        )
        s = sub(
            s,
            "f_p7PermLabel(perm), f_p7LifecycleLabel(lc))\n                for c = 0 to 7\n",
            "f_p7PermLabel(perm), f_p7LifecycleLabel(lc), " + TXT + ")\n                for c = 0 to 8\n",
        )
        s = sub(
            s,
            "                for c = 0 to 7\n                    table.cell(p7Pois, c, r, \"\", text_size = size.tiny)\n",
            "                for c = 0 to 8\n                    table.cell(p7Pois, c, r, \"\", text_size = size.tiny)\n",
        )
        s = sub(s, "        for c = 1 to 7\n            table.cell(p7Pois, c, p7MaxVisiblePois + 1,", "        for c = 1 to 8\n            table.cell(p7Pois, c, p7MaxVisiblePois + 1,")
        # dashboard: one framework row
        s = sub(s, "table.new(position.top_left, 2, 12,", "table.new(position.top_left, 2, 10,")
        # RC4 USER token budget: the three purely informational dashboard rows
        # (momentum acceleration, pullback, session) leave the student build so
        # the RC4 FVG qualification rules fit; their label helpers become dead.
        s = sub(
            s,
            '"Global direction|Regime|Momentum|Momentum accel.|Breakout|Pullback|Session|Volatility|Active POIs"',
            '"Global direction|Regime|Momentum|Breakout|Volatility|Active POIs|Market framework"',
        )
        s = sub(
            s,
            "f_p7DirLabel(p7LastMomDir), f_p7MomAccelLabel(p7LastMomAccel), f_p7BrkLabel(p7LastBrk), f_p7PbLabel(p7LastPb), f_p7SessionLabel(p7LastSession), f_p7VolLabel(p7LastVol)",
            "f_p7DirLabel(p7LastMomDir), f_p7BrkLabel(p7LastBrk), f_p7VolLabel(p7LastVol)",
        )
        s = sub(
            s,
            "str.tostring(array.size(p7PoiIdx)))\n",
            "str.tostring(array.size(p7PoiIdx)), " + DASH + ")\n",
        )
        s = sub(s, "        for r = 3 to 11\n", "        for r = 3 to 9\n")
        # RC4 USER token budget: developer-only outputs leave the student build
        # (the PARITY build keeps every capture stream). Nothing reads them.
        a = s.index("var bool p5xEmitted = false\n")
        b = s.index('    log.info(f_p5xLine("M5",  m5Ext))\n') + len('    log.info(f_p5xLine("M5",  m5Ext))\n')
        s = s[:a] + "// RC4 USER: the P5X_META deployment log lives in the PARITY build only.\n" + s[b:]
        import re
        s, n = re.subn(r"(?m)^plot\([^\n]*display = display\.data_window\)\n", "", s)
        assert n == 41, n
        s = sub(s, "var bool p5xEmitted", "var bool p5xEmitted", 0)
        # RC4 USER: the P9 trace input is inert here (the trace lives in the
        # PARITY build); removing it frees budget for the RC4 FVG rules.
        s, n = re.subn(
            r"(?m)^grpP9 = [^\n]*\np9DebugLog = input\.bool\([^\n]*\)\n", "", s
        )
        assert n == 1 and "p9DebugLog = input" not in s
        s = trim_p6_user(s)
        s = compact_p7(s)
        from strip_dead import strip_dead_user
        s = strip_dead_user(s)
        from compact2 import NEAR_FUNCS, compact2
        s = compact2(s, DRAW)
        from compact3 import compact3
        s = compact3(s)
        from compact4 import compact4
        s = compact4(s)
        s = sub(s, "var map<string, bool> fwSeen", NEAR_FUNCS + "var map<string, bool> fwSeen")
        s = sub(s, "var map<string, bool> fwSeen", P7_TYPES + "var map<string, bool> fwSeen")
    if which == "parity":
        # RC4 PARITY token budget: keep every capture stream the aligned
        # comparison reads (RUNMETA, P5C, P8EVENT / P8PRIME, P3LIFE); drop the
        # P5X meta log, the per-POI P5EVAL line (P5C carries the same row),
        # the data-window plots and the unused P6 diagnostic outputs.
        import re
        a = s.index("var bool p5xEmitted = false\n")
        b = s.index('    log.info(f_p5xLine("M5",  m5Ext))\n') + len('    log.info(f_p5xLine("M5",  m5Ext))\n')
        s = s[:a] + "// RC4 PARITY: P5X_META removed (P6 is closed; P5C carries the P5 wire).\n" + s[b:]
        a = s.index('                if debugMode\n                    log.info("P5EVAL|bar="')
        b = s.index('"|lifecycle=" + str.tostring(lifecycle))\n', a) + len('"|lifecycle=" + str.tostring(lifecycle))\n')
        s = s[:a] + s[b:]
        s, n = re.subn(r"(?m)^plot\([^\n]*display = display\.data_window\)\n", "", s)
        assert n == 61, n
        s = trim_p6_user(s)
    DST[which].write_bytes(s.encode("utf-8"))
    print(which, len(s.splitlines()))
