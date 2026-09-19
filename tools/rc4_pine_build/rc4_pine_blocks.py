"""RC4 Pine blocks, compact UDT form (v2). Imported by rc4_pine_patch.py."""

VARS = '''
// ---- RC4 MARKET FRAMEWORK state (framework/engine.py FrameworkTracker) -----
// Append-only: a level / range / swing is registered the first time it is
// seen and never retracted, and every confirmed candle is swept exactly once,
// so the framework never repaints. Host timeframe only (P6 stays closed).
type FwLv
    float p     // price at the anchor
    float s     // price change per bar (trendlines)
    int   a     // anchor absolute bar index
    int   d     // +1 buy-side (above price), -1 sell-side
    int   k     // known from (availability)
    int   x     // bar of a pending close-through
    int   t     // 0 swing, 1 equal level, 2 trendline, 3 range
type FwEv
    int   t     // sweep availability (bar close)
    int   d
    float p
    int   o     // sweep bar open (drawing only)
type FwRg
    int   c     // confirmation
    int   e     // end (na = active)
    float h
    float l
type FwSw
    int   s     // pivot start time
    int   y
    float q
type FwPoi
    int    cur  // next sweep event to read
    bool   dis  // DISTRACTION seen
    bool   swp  // approach-side sweep since availability
    float  ext  // impulse extreme since the source candle
    string txt  // table text (presentation)
    int    perm // P7 table: permission (colour)
    string row  // P7 table: the row's cells
    bool   kn   // P8: already seen
    bool   pb   // P8: previous BTMM-valid
    int    pp   // P8: previous permission
    bool   ta   // P8: terminal alerted
    bool   fd   // P5: final (terminal) row emitted
var map<string, bool> fwSeen = map.new<string, bool>()
var array<FwLv>  fwLv  = array.new<FwLv>()
var array<FwEv>  fwEv  = array.new<FwEv>()
var array<FwRg>  fwRgs = array.new<FwRg>()
var map<int, FwRg> fwRgByC = map.new<int, FwRg>()
var array<FwSw>  fwSw  = array.new<FwSw>()
var array<FwPoi> fwPoi = array.new<FwPoi>()
var array<EqualLevelRec> fwEqs = array.new<EqualLevelRec>()
var array<TrendlineRec>  fwTls = array.new<TrendlineRec>()
var FwRg fwR = na
'''

FUNCS = '''
// =============================================================================
// RC4 MARKET FRAMEWORK — framework/engine.py (author decisions 2026-09-19).
// Range = the BTRC RANGE rule (>= 3 CHOCH in the last 4 transitions), high /
// low = the extreme levels those breaks broke, ended by the first later BOS or
// superseded by the next range. Sweep: a wick through a level with the close
// back (WICK_SWEEP), or a close through reclaimed within 3 bars
// (CLOSE_THROUGH_RECLAIM); an unreclaimed close-through consumes the level.
// =============================================================================
f_fwAdd(string k, float p, float s, int a, int d, int kn, int ty) =>
    if not map.contains(fwSeen, k)
        map.put(fwSeen, k, true)
        array.push(fwLv, FwLv.new(p, s, a, d, kn, na, ty))

// the range confirmed at or before t and not yet ended (latest confirmation)
f_fwRange(int t) =>
    FwRg r = na
    for g in fwRgs
        if g.c <= t and (na(g.e) or g.e > t) and (na(r) or g.c >= r.c)
            r := g
    r

f_fwRanges(array<StructEventRec> ev) =>
    int n = array.size(ev)
    array<FwRg> found = array.new<FwRg>()
    array<int> fk = array.new<int>()
    if n >= 4
        for k = 3 to n - 1
            int ch = 0
            float hi = na
            float lo = na
            for q = k - 3 to k
                StructEventRec e = array.get(ev, q)
                ch += math.abs(e.transitionCode) == 2 ? 1 : 0
                if e.transitionCode > 0
                    hi := na(hi) ? e.brokenLevel : math.max(hi, e.brokenLevel)
                else
                    lo := na(lo) ? e.brokenLevel : math.min(lo, e.brokenLevel)
            if ch >= 3 and hi > lo
                array.push(fk, k)
                array.push(found, FwRg.new(array.get(ev, k).availabilityTime, na, hi, lo))
    for [m, g] in found
        int k = array.get(fk, m)
        bool more = m + 1 < array.size(fk)
        int nk = more ? array.get(fk, m + 1) : n - 1
        if nk > k
            for q = k + 1 to nk
                StructEventRec e = array.get(ev, q)
                if na(g.e) and math.abs(e.transitionCode) == 1
                    g.e := e.availabilityTime
        if na(g.e) and more
            g.e := array.get(ev, nk).availabilityTime
        FwRg old = map.get(fwRgByC, g.c)
        if na(old)
            array.push(fwRgs, g)
            map.put(fwRgByC, g.c, g)
        else if na(old.e)
            old.e := g.e
        g

// evaluate_poi_framework for POI i on this confirmed bar.
// Returns [on, pretradeValid, locationScore, episode(0 none,1 active,2 ended,3 failed)].
f_fwPoi(int i) =>
    bool on = array.get(poiType, i) <= C_POI_CORE_TYPE_MAX
    bool pre = false
    int loc = 0
    int ep = 0
    if on
        FwPoi f = array.get(fwPoi, i)
        bool bull = array.get(poiDirection, i) == C_POI_DIR_BULLISH
        int dir = bull ? 1 : -1
        float zt = array.get(poiZoneTop, i)
        float zb = array.get(poiZoneBottom, i)
        float mid = (zt + zb) / 2
        int pa = array.get(poiAvailTime, i)
        int nw = array.size(wHigh) - 1
        // episode start: the first host bar closing at/after the first touch
        int sI = -1
        if array.get(poiTermReason, i) == C_POI_TERM_MITIGATED
            int j = nw
            while j >= 0 and array.get(wAvailT, j) >= array.get(poiTermTime, i)
                sI := j
                j -= 1
        int sAv = sI >= 0 ? array.get(wAvailT, sI) : na
        // DISTRACTION: approach-path liquidity swept after availability and
        // before the touch bar (sell-side above a bullish POI, buy-side below
        // a bearish one); any approach-side sweep earns the location bonus.
        int ne = array.size(fwEv)
        if na(f.cur)
            f.cur := ne
            while f.cur > 0 and array.get(fwEv, f.cur - 1).t > pa
                f.cur := f.cur - 1
        if f.cur < ne
            for e = f.cur to ne - 1
                FwEv v = array.get(fwEv, e)
                if v.t > pa and v.d == -dir
                    f.swp := true
                    if (na(sAv) or v.t < sAv) and (bull ? v.p > zt : v.p < zb)
                        f.dis := true
        f.cur := ne
        // DELAY / WIPEOUT / TRUE FAILURE inside the 5-bar interaction episode
        bool dly = false
        bool wip = false
        bool fail = false
        if sI >= 0
            int eI = sI + 4
            float tol = math.max(0.02, math.min(0.10 * nz(array.get(wAtr, sI)), 0.25 * (zt - zb)))
            int run = 0
            int reent = 0
            bool left = false
            int pen = -1
            bool rec = false
            for j = sI to math.min(nw, eI)
                if not fail
                    float h = array.get(wHigh, j)
                    float l = array.get(wLow, j)
                    float cl = array.get(wClose, j)
                    bool out = bull ? cl > zt : cl < zb
                    run := cl >= zb and cl <= zt ? run + 1 : 0
                    dly := dly or run >= 2
                    if left and l <= zt and h >= zb
                        reent += 1
                        left := false
                    left := left or out
                    if pen < 0 and (bull ? l < zb - tol : h > zt + tol)
                        pen := j
                    if pen >= 0 and not rec
                        if bull ? cl >= zb : cl <= zt
                            rec := true
                        else if j - pen >= 3
                            fail := true
                    wip := wip or (rec and out)
            dly := dly or reent >= 1
            ep := fail ? 3 : nw >= eI ? 2 : 1
        pre := (f.dis or dly or wip) and not fail
        // location: range thirds, or depth inside the POI's origin impulse
        int src = array.get(poiCandTime, i)
        if na(f.ext)
            for j = 0 to nw
                if array.get(wOpenT, j) >= src
                    float x = bull ? array.get(wHigh, j) : array.get(wLow, j)
                    f.ext := na(f.ext) or (x - f.ext) * dir > 0 ? x : f.ext
        else
            f.ext := bull ? math.max(f.ext, high) : math.min(f.ext, low)
        string lt = "NONE"
        if not na(fwR)
            float rel = (mid - fwR.l) / (fwR.h - fwR.l)
            int pos = rel < 1.0 / 3 ? -1 : rel > 2.0 / 3 ? 1 : 0
            loc := pos == 0 ? 35 : pos == -dir ? 75 : 20
            lt := "RANGE " + (pos < 0 ? "LOW" : pos > 0 ? "HIGH" : "MID")
        else
            float org = bull ? zb : zt
            int best = na
            for w in fwSw
                if w.s <= src and w.y == (bull ? SWING_LOW : SWING_HIGH) and (na(best) or w.s >= best)
                    best := w.s
                    org := bull ? math.min(zb, w.q) : math.max(zt, w.q)
            float span = (f.ext - org) * dir
            loc := 50
            if span > 0
                float ret = math.round((f.ext - mid) * dir / span * 10000) / 100
                loc := ret < 50 ? 40 : ret < 61.8 ? 65 : ret <= 79 ? 80 : 55
                lt := "TREND " + str.tostring(ret) + "%"
        if f.swp
            loc := math.min(100, loc + 15)
            lt += " +SWEEP"
        f.txt := (fail ? "FAIL" : pre ? ((f.dis ? "DIS " : "") + (dly ? "DEL " : "") + (wip ? "WIP " : "")) : "- ") + "| " + lt + " | " + str.tostring(loc)
    [on, pre, loc, ep]

// ---- per-bar framework advance (before P5 reads it) ----
if barstate.isconfirmed
    int fwNow = confirmedBarCount - 1
    for s in p3Swings
        string k = "S" + str.tostring(s.pivotEndTime) + "|" + str.tostring(s.price)
        if not map.contains(fwSeen, k)
            array.push(fwSw, FwSw.new(array.get(wOpenT, s.pivotStartIdx), s.swingType, s.price))
        f_fwAdd(k, s.price, 0.0, 0, s.swingType == SWING_HIGH ? 1 : -1, s.meaningfulConfTime, 0)
    for e in fwEqs
        bool eh = e.clusterType == SWING_HIGH
        f_fwAdd("E" + str.tostring(e.clusterType) + "|" + str.tostring(e.firstTime), eh ? e.zoneTop : e.zoneBottom, 0.0, 0, eh ? 1 : -1, e.confirmationTime, 1)
    for t in fwTls
        int a = array.indexof(wOpenT, t.anchor1Time)
        if a >= 0
            f_fwAdd("T" + str.tostring(t.orientation) + "|" + str.tostring(t.anchor1Time) + "|" + str.tostring(t.anchor2Time) + "|" + str.tostring(t.confirmationTime), t.anchor1Price, t.rawSlope, confirmedBarCount - array.size(wHigh) + a, t.orientation == SWING_LOW ? -1 : 1, t.confirmationTime, 2)
    f_fwRanges(p3Events)
    FwRg ro = f_fwRange(time)
    if not na(ro)
        f_fwAdd("RH" + str.tostring(ro.c), ro.h, 0.0, 0, 1, ro.c, 3)
        f_fwAdd("RL" + str.tostring(ro.c), ro.l, 0.0, 0, -1, ro.c, 3)
    int nl = array.size(fwLv)
    if nl > 0
        for j = nl - 1 to 0
            FwLv l = array.get(fwLv, j)
            if l.k <= time
                float p = l.p + l.s * (fwNow - l.a)
                bool bc = (close - p) * l.d > 0
                bool ev = na(l.x) ? not bc and (l.d > 0 ? high > p : low < p) : not bc
                if na(l.x) and bc
                    l.x := fwNow
                if ev
                    array.push(fwEv, FwEv.new(time_close, l.d, p, time))
                if ev or (not na(l.x) and bc and fwNow - l.x >= 3)
                    array.remove(fwLv, j)
    fwR := f_fwRange(time_close)
'''

DRAW = '''
    // ---- RC4 display layers (presentation only; nothing above reads them) ----
    if bar_index >= last_bar_index - 1
        f_clearLines(fwLines)
        f_clearLabels(fwLabels)
        if dspRange and not na(fwR)
            for [q, y] in array.from(fwR.h, fwR.l, (fwR.h + fwR.l) / 2)
                array.push(fwLines, line.new(fwR.c, y, time, y, xloc.bar_time, extend.right, color.aqua, q == 2 ? line.style_dotted : line.style_solid))
            array.push(fwLabels, label.new(fwR.c, fwR.h, "RANGE", xloc.bar_time, color = color(na), textcolor = color.aqua, style = label.style_label_lower_left, size = size.tiny))
        int nd = 0
        for l in fwLv
            if nd < maxDrawPerFamily and l.k <= time and ((dspTl and l.t == 2) or (dspLiq and l.t < 2))
                nd += 1
                color lc = l.d > 0 ? color.orange : color.teal
                if l.t == 2
                    array.push(fwLines, line.new(bar_index - fwNow + l.a, l.p, bar_index, l.p + l.s * (fwNow - l.a), xloc.bar_index, extend.right, color.purple))
                else
                    array.push(fwLines, line.new(l.k, l.p, time, l.p, xloc.bar_time, extend.right, lc, line.style_dashed))
                    array.push(fwLabels, label.new(bar_index + 2, l.p, (l.t == 1 ? "EQ " : "") + (l.d > 0 ? "BSL" : "SSL"), color = color(na), textcolor = lc, style = label.style_label_left, size = size.tiny))
        int ne2 = array.size(fwEv)
        if dspLiq and ne2 > 0
            for e = math.max(0, ne2 - maxDrawPerFamily) to ne2 - 1
                FwEv v = array.get(fwEv, e)
                array.push(fwLabels, label.new(v.o, v.p, "SWEEP", xloc.bar_time, color = color(na), textcolor = v.d > 0 ? color.orange : color.teal, style = v.d > 0 ? label.style_label_down : label.style_label_up, size = size.tiny))
'''

PUSH = "            array.push(fwPoi, FwPoi.new(na, false, false, na, \"\", na, \"\", false, false, -1, false, false))\n"
TXT = "fwPoi.get(poiI).txt"
DASH = "not na(fwR) ? \"RANGE \" + str.tostring(fwR.l) + \" - \" + str.tostring(fwR.h) : \"TREND / impulse\""

P8_OLD_START = '                    string p8Sym = syminfo.prefix + ":" + syminfo.ticker\n'
P8_OLD_END = '                          "|lifecycle=" + f_p7LifecycleLabel(lifecycle), alert.freq_once_per_bar_close)\n'
P8_NEW = '''                    // Compaction (RC4): shared message parts built once; every alert
                    // text is byte-identical to the RC3 wording.
                    string p8Hd = "|" + syminfo.prefix + ":" + syminfo.ticker + "|tf=" + timeframe.period + "|poiIdx=" + str.tostring(i) + "|dir=" + (poiBullish ? "BULL" : "BEAR")
                    string p8Pm = "|permission=" + f_p7PermLabel(permission)
                    string p8Lc = "|lifecycle=" + f_p7LifecycleLabel(lifecycle)
                    if p8IsNew and p8EnablePoiActivated
                        alert("P8 POI_ACTIVATED" + p8Hd + "|tier=" + f_p7TierLabel(array.get(poiTier, i)) + p8Pm + p8Lc, alert.freq_once_per_bar_close)
                    if p8BtmmEnteredValid and p8EnableBtmmValidated
                        alert("P8 BTMM_VALIDATED" + p8Hd + p8Pm, alert.freq_once_per_bar_close)
                    if (p8EnteredActionable and p8EnableEnteredActionable) or (p8LostActionable and p8EnableLostActionable)
                        alert("P8 PERMISSION_" + (p8EnteredActionable ? "ENTERED" : "LOST") + "_ACTIONABLE" + p8Hd + p8Pm + "|score=" + str.tostring(finalScore), alert.freq_once_per_bar_close)
                    if p8TerminalNow and p8EnableTerminal
                        alert("P8 POI_TERMINAL" + p8Hd + "|reason=" + f_p8TermReasonLabel(fwEp == 3 ? C_POI_TERM_INVALIDATED : array.get(poiTermReason, i)) + p8Lc, alert.freq_once_per_bar_close)
'''


def trim_p6_user(s: str) -> str:
    """RC4 USER token budget: the P6 projection returns only what P5 reads
    (bars, swing count, fingerprint, P2 direction, P5 transport UDT). The ten
    other outputs fed the P6 data-window diagnostics removed from this build."""
    def rep(old: str, new: str, count: int = 1) -> None:
        nonlocal s
        assert s.count(old) == count, (old[:70], s.count(old))
        s = s.replace(old, new)

    for v in ("    var int   lastType   = C_ST_NA\n", "    var float lastPrice  = na\n",
              "    var int   lastConfT  = C_ST_NA\n", "    var int   eqCount    = 0\n",
              "    var int   dispCode   = C_ST_NA\n", "    var float dispRatio  = na\n",
              "    var int   p2TransCount = 0\n", "    var int   p2LastTrans  = C_ST_NA\n",
              "    var float p2LastBrokenLvl = na\n", "    int qDataset = last_bar_index + 1\n"):
        rep(v, "")
    rep("        dispCode  := qDispCode\n        dispRatio := qDispRatio\n", "")
    rep("""        if swingCount > 0
            SwingRec sr = array.get(qSwings, swingCount - 1)
            lastType  := sr.swingType
            lastPrice := sr.price
            lastConfT := sr.meaningfulConfTime
        eqCount := array.size(f_detectEqualLevels(qSwings))
""", "")
    rep("""        p2TransCount := array.size(qP2Events)
        if p2TransCount > 0
            StructEventRec qLastEv = array.get(qP2Events, p2TransCount - 1)
            p2LastTrans      := qLastEv.transitionCode
            p2LastBrokenLvl  := qLastEv.brokenLevel
""", "")
    rep("    [qBars, swingCount, lastType, lastPrice, lastConfT, eqCount, qFingerprint, qDataset, dispCode, dispRatio, p2Dir, p2TransCount, p2LastTrans, p2LastBrokenLvl, xExt]\n",
        "    [qBars, swingCount, qFingerprint, p2Dir, xExt]\n")
    import re
    s, n = re.subn(
        r"\[(\w+)Bars, +(\w+)Sw, +\w+Type, +\w+Price, +\w+Conf, +\w+Eq, +(\w+)Fp *, \w+Ds, \w+Dc, \w+Dr, (\w+)P2d, \w+Tc, \w+Lt, \w+Bl, (\w+)Ext\]",
        lambda m: f"[{m.group(1)}Bars, {m.group(1)}Sw, {m.group(1)}Fp, {m.group(1)}P2d, {m.group(1)}Ext]",
        s,
    )
    assert n == 6, n
    return s


P7_TYPES = '''
// RC4 USER compaction: one record per P7-Z zone group (presentation only).
type P7zG
    float  top
    float  bot
    int    left
    bool   bull
    int    key
    string names
    bool   term
'''


def compact_p7(s: str) -> str:
    """Presentation-only compaction of the P7 table and P7-Z groups (RC4 USER).
    Same rows, same boxes, same text; fewer compiled tokens."""
    import re

    def rep(old: str, new: str) -> None:
        nonlocal s
        assert s.count(old) == 1, (old[:90], s.count(old))
        s = s.replace(old, new)

    # --- P7-Z zone groups: seven parallel arrays -> one record array ---------
    s, n = re.subn(
        r"        array<float>  p7zGTop +=.*\n        array<float>  p7zGBot +=.*\n        array<int>    p7zGLeft +=.*\n"
        r"        array<bool>   p7zGBull +=.*\n        array<int>    p7zGKey +=.*\n        array<string> p7zGNames +=.*\n"
        r"        array<bool>   p7zGTerm +=.*\n",
        "        array<P7zG> p7zGs = array.new<P7zG>()\n", s)
    assert n == 1, n
    rep("""                        array.push(p7zGTop, array.get(cF, 0))
                        array.push(p7zGBot, array.get(cF, 1))
                        array.push(p7zGLeft, array.get(cI, 0))
                        array.push(p7zGBull, wantDir == C_POI_DIR_BULLISH)
                        array.push(p7zGKey, array.get(cI, 1))
                        array.push(p7zGNames, f_p7zTypeLabel(array.get(cI, 3)) + (cN > 1 ? " ×" + str.tostring(cN) : ""))
                        array.push(p7zGTerm, array.get(cT, 0))
""", """                        array.push(p7zGs, P7zG.new(array.get(cF, 0), array.get(cF, 1), array.get(cI, 0), wantDir == C_POI_DIR_BULLISH, array.get(cI, 1), f_p7zTypeLabel(array.get(cI, 3)) + (cN > 1 ? " ×" + str.tostring(cN) : ""), array.get(cT, 0)))
""")
    for old, new in (
        ("int gi = map.get(p7zSlot, gk)", "P7zG g = array.get(p7zGs, map.get(p7zSlot, gk))"),
        ("array.set(p7zGKey, gi, math.min(array.get(p7zGKey, gi), pI))", "g.key := math.min(g.key, pI)"),
        ("array.set(p7zGLeft, gi, math.min(array.get(p7zGLeft, gi), cd))", "g.left := math.min(g.left, cd)"),
        ("array.set(p7zGTerm, gi, array.get(p7zGTerm, gi) and array.get(poiTerminal, pI))", "g.term := g.term and array.get(poiTerminal, pI)"),
        ("string nmsCur = array.get(p7zGNames, gi)", "string nmsCur = g.names"),
        ('array.set(p7zGNames, gi, nmsCur + " + " + nm)', 'g.names := nmsCur + " + " + nm'),
    ):
        rep(old, new)
    rep("""                    map.put(p7zSlot, gk, array.size(p7zGTop))
                    array.push(p7zGTop, tp)
                    array.push(p7zGBot, bt)
                    array.push(p7zGLeft, cd)
                    array.push(p7zGBull, dr == C_POI_DIR_BULLISH)
                    array.push(p7zGKey, pI)
                    array.push(p7zGNames, nm)
                    array.push(p7zGTerm, array.get(poiTerminal, pI))
""", """                    map.put(p7zSlot, gk, array.size(p7zGs))
                    array.push(p7zGs, P7zG.new(tp, bt, cd, dr == C_POI_DIR_BULLISH, pI, nm, array.get(poiTerminal, pI)))
""")
    rep("array.size(p7zGTop)", "array.size(p7zGs)")
    fields = {"Top": "top", "Bot": "bot", "Left": "left", "Bull": "bull", "Key": "key", "Names": "names", "Term": "term"}
    s, n = re.subn(r"array\.get\(p7zG(Top|Bot|Left|Bull|Key|Names|Term), (\w+)\)",
                   lambda m: f"array.get(p7zGs, {m.group(2)}).{fields[m.group(1)]}", s)
    assert n >= 8, n
    assert not re.search(r"p7zG(Top|Bot|Left|Bull|Key|Names|Term)\b", s)

    # --- P7 table rows: seven per-row arrays -> the POI's prebuilt row --------
    s, n = re.subn(r"var array<(bool|int)> +p7Poi(Bull|Tier|BtmmValid|Align|Final|Perm|Lc) *=.*\n", "", s)
    assert n == 7, n
    s, n = re.subn(r"    array\.clear\(p7Poi(Bull|Tier|BtmmValid|Align|Final|Perm|Lc)\)\n", "", s)
    assert n == 7, n
    rep("""                array.push(p7PoiBull, poiBullish)
                array.push(p7PoiTier, array.get(poiTier, i))
                array.push(p7PoiBtmmValid, btmmValid)
                array.push(p7PoiAlign, align)
                array.push(p7PoiFinal, finalScore)
                array.push(p7PoiPerm, permission)
                array.push(p7PoiLc, lifecycle)
""", """                FwPoi fq = array.get(fwPoi, i)
                fq.perm := permission
                fq.row := str.tostring(i) + "~" + (poiBullish ? "BULL" : "BEAR") + "~" + f_p7TierLabel(array.get(poiTier, i)) + "~" + (btmmValid ? "YES" : "NO") + "~" + f_p7AlignLabel(align) + "~" + str.tostring(finalScore) + "~" + f_p7PermLabel(permission) + "~" + f_p7LifecycleLabel(lifecycle) + "~" + fq.txt
""")
    a = s.index("                bool bull     = array.get(p7PoiBull, srcRow)\n")
    b = s.index("                for c = 0 to 8\n", a)
    s = s[:a] + """                FwPoi fr = array.get(fwPoi, poiI)
                bool bull = array.get(poiDirection, poiI) == C_POI_DIR_BULLISH
                int perm = fr.perm
                array<string> p7Cells = str.split(fr.row, "~")
""" + s[b:]
    return s
