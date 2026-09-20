"""RC4 FVG qualification in Pine (author decision 2026-09-19), both builds.

Mirrors ``poi/qualification.py``:
  * the departure candle must be a real expansion -- the FROZEN displacement
    primitive (``f_medianRange`` over ``C_RANGE_CONTEXT_WINDOW`` bars,
    ``C_DISP_FAST_RATIO``) must class it at least FAST, and its range must
    exceed the immediately preceding candle's range;
  * an FVG released late by the reversal-context gate is refused when its
    imbalance was already fully consumed before that release
    (``PRE_AVAILABILITY_CONSUMED``); the check reads only confirmed bars up to
    the release, so it adds no lookahead and does not touch the frozen
    lifecycle (a pre-availability touch still never mitigates).
"""

OLD_EMIT = """        if typeCode != 0 and zoneTop - zoneBottom >= C_POI_FVG_MIN_GAP_ATR * array.get(wAtr, mi) and not map.contains(poiOriginKey, array.get(wOpenT, mi) * direction)
"""
NEW_EMIT = """        // RC4: the gap must be material AND the departure candle must be a real
        // expansion -- frozen displacement primitive at least FAST, and larger
        // than the candle immediately before it.
        float fvgDepR = array.get(wHigh, mi) - array.get(wLow, mi)
        float fvgBase = mi >= C_RANGE_CONTEXT_WINDOW ? f_medianRange(wHigh, wLow, mi - C_RANGE_CONTEXT_WINDOW, mi, scDispRange) : 0.0
        bool fvgDepOk = fvgBase > 0.0 and fvgDepR >= C_DISP_FAST_RATIO * fvgBase and fvgDepR > array.get(wHigh, fi) - array.get(wLow, fi)
        if typeCode != 0 and fvgDepOk and zoneTop - zoneBottom >= C_POI_FVG_MIN_GAP_ATR * array.get(wAtr, mi) and not map.contains(poiOriginKey, array.get(wOpenT, mi) * direction)
"""

OLD_RELEASE = """                        if f_poiFind(cp.poiType, cp.srcFirstTime, cp.srcCount, cp.srcLastTime, f_poiTicks(cp.zoneBottom), f_poiTicks(cp.zoneTop)) == -1
"""
NEW_RELEASE = """                        // RC4 PRE_AVAILABILITY_CONSUMED: an imbalance already
                        // filled before this late release is not admitted.
                        bool cpOk = true
                        if cp.poiType == C_POI_BUY_FAIR_VALUE_GAP or cp.poiType == C_POI_SELL_FAIR_VALUE_GAP
                            for [cj, cav] in wAvailT
                                if cpOk and cav > cp.availTime and cav <= ca and (cp.direction == C_POI_DIR_BULLISH ? array.get(wLow, cj) <= cp.zoneBottom : array.get(wHigh, cj) >= cp.zoneTop)
                                    cpOk := false
                        if cpOk and f_poiFind(cp.poiType, cp.srcFirstTime, cp.srcCount, cp.srcLastTime, f_poiTicks(cp.zoneBottom), f_poiTicks(cp.zoneTop)) == -1
"""


def apply_rc4_fvg(s: str) -> str:
    for old, new in ((OLD_EMIT, NEW_EMIT), (OLD_RELEASE, NEW_RELEASE)):
        assert s.count(old) == 1, old[:60]
        s = s.replace(old, new)
    return s
