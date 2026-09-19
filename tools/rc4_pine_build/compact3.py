"""RC4 USER compaction round 3. Semantics and presentation unchanged except:
the provisional P5 weights / bands become constants (their RC4 values) and the
developer-only "review zones as of" input is removed."""
import re

NL = chr(10)

FVG_OLD_START = "                array<float> cF = array.new<float>(2, na)" + NL
FVG_OLD_END = "                        array.set(cI, 2, cN + 1)" + NL
FVG_NEW = '''                P7zG c = na
                int cN = 0
                int cTy = 0
                for k = 0 to fn
                    int pI = k < fn ? array.get(fvgIdx, array.get(ord, k)) : -1
                    float bt = k < fn ? array.get(poiZoneBottom, pI) : na
                    float tp = k < fn ? array.get(poiZoneTop, pI) : na
                    if cN > 0 and (k == fn or bt > c.top)
                        c.names := f_p7zTypeLabel(cTy) + (cN > 1 ? " ×" + str.tostring(cN) : "")
                        array.push(p7zGs, c)
                        cN := 0
                    if k < fn
                        if cN == 0
                            c := P7zG.new(tp, bt, array.get(poiCandTime, pI), wantDir == C_POI_DIR_BULLISH, pI, "", array.get(poiTerminal, pI))
                            cTy := array.get(poiType, pI)
                        else
                            c.top := math.max(c.top, tp)
                            c.bot := math.min(c.bot, bt)
                            c.left := math.min(c.left, array.get(poiCandTime, pI))
                            c.key := math.min(c.key, pI)
                            c.term := c.term and array.get(poiTerminal, pI)
                        cN += 1
'''


def compact3(s: str) -> str:
    def rep(old: str, new: str, count: int = 1) -> None:
        nonlocal s
        assert s.count(old) == count, (old[:80], s.count(old))
        s = s.replace(old, new)

    a = s.index(FVG_OLD_START)
    b = s.index(FVG_OLD_END, a) + len(FVG_OLD_END)
    s = s[:a] + FVG_NEW + s[b:]

    # P8 edge state + the P5 one-final-row flag live on the POI record
    rep("    int p5Have = array.size(poiP5FinalDone)" + NL, "    int p5Have = array.size(fwPoi)" + NL)
    for v in ("poiP5FinalDone", "p8Known", "p8PrevBtmmValid", "p8TerminalAlerted"):
        rep("            array.push(" + v + ", false)" + NL, "")
    rep("            array.push(p8PrevPermission, -1)" + NL, "")
    s, n = re.subn(r"(?m)^var array<(bool|int)> +(poiP5FinalDone|p8Known|p8PrevBtmmValid|p8PrevPermission|p8TerminalAlerted) *=.*" + NL, "", s)
    assert n == 5, n
    rep("            if not array.get(poiP5FinalDone, i)" + NL,
        "            FwPoi fp = array.get(fwPoi, i)" + NL + "            if not fp.fd" + NL)
    rep("not array.get(p8Known, i)", "not fp.kn")
    rep("array.get(p8PrevBtmmValid, i)", "fp.pb")
    rep("array.get(p8PrevPermission, i)", "fp.pp")
    rep("not array.get(p8TerminalAlerted, i)", "not fp.ta")
    rep("array.set(p8Known, i, true)", "fp.kn := true")
    rep("array.set(p8PrevBtmmValid, i, btmmValid)", "fp.pb := btmmValid")
    rep("array.set(p8PrevPermission, i, permission)", "fp.pp := permission")
    rep("array.set(p8TerminalAlerted, i, true)", "fp.ta := true")
    rep("array.set(poiP5FinalDone, i, true)", "fp.fd := true")
    assert not re.search(r"\b(poiP5FinalDone|p8Known|p8PrevBtmmValid|p8PrevPermission|p8TerminalAlerted)\b",
                         "".join(l for l in s.splitlines(True) if not l.lstrip().startswith("//")))

    # provisional P5 weights / permission bands: RC4 constants
    s, n = re.subn(r"(?m)^(p5W\w+ *= *)input\.int\((\d+), [^\n]*\)$", r"\g<1>\g<2>", s)
    assert n == 9, n
    s, n = re.subn(r"(?m)^(p5(?:HighConfMin) *= *)input\.int\((\d+), [^\n]*\)$", r"\g<1>\g<2>", s)
    assert n == 1, n
    s, n = re.subn(r"(?m)^(p5DowngradeExtremeVol *= *)input\.bool\(true, [^\n]*\)$", r"\g<1>true", s)
    assert n == 1, n

    # developer-only zone review input
    s, n = re.subn(r"(?m)^p7zAsOf *= *input\.time\([^\n]*\)" + NL, "", s)
    assert n == 1, n
    rep("(p7zAsOf == 0 ? bar_index >= p1DatasetBars - 2 : time_close <= p7zAsOf)", "bar_index >= p1DatasetBars - 2")
    return s
