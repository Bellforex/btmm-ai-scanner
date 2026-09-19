"""RC4 USER token budget: remove stores to globals that nothing reads any more
(they fed the data-window plots / P5X meta log removed from this build)."""


def _cut(s: str, start: str, end: str) -> str:
    a = s.index(start)
    assert s.count(start) == 1, start[:60]
    b = s.index(end, a) + len(end)
    return s[:a] + s[b:]


def strip_dead_user(s: str) -> str:
    NL = chr(10)
    s = _cut(s, "    latestDispCode := dispCode" + NL, "    latestDispRatio := dispRatio" + NL)
    s = _cut(s, "    p2SwingCount := array.size(p2Swings)" + NL, "        p2LastStartAbs := lastView.pivotStartAbs" + NL)
    s = _cut(s, "    p2RelCount := array.size(p2Rels)" + NL, "            p2LastLowRel := r.relationshipCode" + NL)
    s = _cut(s, "    p2ProtHighKey := p2bProtHigh" + NL, "    p2ChochAborts   := p2bAborts" + NL)
    s = _cut(s, "    p2LastTransCode := C_ST_NA" + NL, "        p2LastBrokenLvl := lastEv.brokenLevel" + NL)
    s = _cut(s, "    bool haveHigh = false" + NL, "        si2 -= 1" + NL)
    s = _cut(s, "    latestSRTop := na" + NL, "    lastSRFingerprint := newSRFingerprint" + NL)
    s = _cut(s, "        latestEqualHigh := na" + NL, "                latestEqualLow := e.representativePrice" + NL)
    s = _cut(s, "        latestTLNormSlope := na" + NL, "            latestTLOrient := tl.orientation" + NL)
    s = _cut(s, "var int p6AliasHits   = 0" + NL, "    p6HostBarsMax := math.max(p6HostBarsMax, bar_index + 1)" + NL)
    return s
