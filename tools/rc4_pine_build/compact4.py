"""RC4 USER round 4: the "BTMM" display switch now marks the RC4 BTMM pre-trade
cycle (a diamond under the bar on which a POI's cycle becomes valid -- the same
edge that fires P8 BTMM_VALIDATED) instead of the RC3 P4 lifecycle counters."""
import re

NL = chr(10)


def compact4(s: str) -> str:
    def rep(old: str, new: str) -> None:
        nonlocal s
        assert s.count(old) == 1, (old[:80], s.count(old))
        s = s.replace(old, new)

    rep("        f_btmmReportCounts()" + NL, "")
    a = s.index("float p4dGate = ta.change(")
    b = s.index(NL, s.index("plotshape(dspBtmm and barstate.isconfirmed", a)) + 1
    s = s[:a] + s[b:]
    s, n = re.subn(r"(?m)^dspBtmm  = input\.bool\([^\n]*\)$",
                   'dspBtmm  = input.bool(false, "Show BTMM Cycle (markers)", tooltip = "Diamond under the bar on which a POI\'s BTMM pre-trade cycle (DISTRACTION / DELAY / WIPEOUT) becomes valid -- the same event as the P8 BTMM_VALIDATED alert.", group = grpView)', s)
    assert n == 1, n
    rep("    int p5Have = array.size(fwPoi)" + NL, "    fwCyc := 0" + NL + "    int p5Have = array.size(fwPoi)" + NL)
    rep("                bool p8BtmmEnteredValid = (not p8PrevBtmm) and btmmValid" + NL,
        "                bool p8BtmmEnteredValid = (not p8PrevBtmm) and btmmValid" + NL + "                fwCyc += p8BtmmEnteredValid ? 1 : 0" + NL)
    rep("var bool p8Primed = false" + NL, "var int fwCyc = 0" + NL + "var bool p8Primed = false" + NL)
    a = s.index(NL + "if barstate.islast" + NL, s.index("fwCyc += "))
    s = s[:a] + NL + 'plotshape(dspBtmm and fwCyc > 0, "BTMM cycle valid", shape.diamond, location.bottom, color.orange, size = size.tiny)' + NL + s[a:]
    return s
