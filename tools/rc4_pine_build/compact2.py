"""RC4 USER compaction round 2 (presentation only; same rows / boxes)."""

NEAR_FUNCS = '''
// RC4 USER compaction: the P7 table and the P7-Z boxes share one
// nearest-to-price ordering (repeated minimum, ties to the lower key).
f_dist(float t, float b) =>
    close < b ? b - close : close > t ? close - t : 0.0

f_nearest(array<float> d, array<int> key, array<bool> taken, int n) =>
    array<int> out = array.new<int>()
    bool more = true
    while more and array.size(out) < n
        int b = -1
        for [g, dg] in d
            if not array.get(taken, g) and (b < 0 or dg < array.get(d, b) or (dg == array.get(d, b) and array.get(key, g) < array.get(key, b)))
                b := g
        more := b >= 0
        if more
            array.set(taken, b, true)
            array.push(out, b)
    out
'''

TABLE_OLD_START = "                float p7RowTop = array.get(poiZoneTop, p7RowPoi)\n"
TABLE_OLD_END = "                    array.push(p7RowOrder, p7RowBest)\n"
TABLE_NEW = '''                array.push(p7RowDist, f_dist(array.get(poiZoneTop, p7RowPoi), array.get(poiZoneBottom, p7RowPoi)))
            p7RowOrder := f_nearest(p7RowDist, p7PoiIdx, p7RowTaken, p7Shown)
'''

Z_OLD_START = "        array<float> p7zGDist = array.new<float>()\n"
Z_OLD_END = "                    array.push(p7zSelected, array.get(p7zGs, bestG).key)\n"
Z_NEW = '''        if p7zShown > 0
            array<float> p7zGDist = array.new<float>()
            array<int> p7zGKeys = array.new<int>()
            for g in p7zGs
                array.push(p7zGDist, f_dist(g.top, g.bot))
                array.push(p7zGKeys, g.key)
            p7zSelGrp := f_nearest(p7zGDist, p7zGKeys, array.new<bool>(p7zNGrp, false), p7zShown)
            for g in p7zSelGrp
                array.push(p7zSelected, array.get(p7zGKeys, g))
'''

DRAW2 = '''
    // ---- RC4 display layers (presentation only; nothing above reads them) ----
    if bar_index >= last_bar_index - 1
        f_clearLines(fwLines)
        f_clearLabels(fwLabels)
        if dspRange and not na(fwR)
            for [q, y] in array.from(fwR.h, fwR.l, (fwR.h + fwR.l) / 2)
                array.push(fwLines, line.new(fwR.c, y, time, y, xloc.bar_time, extend.right, color.aqua, q == 2 ? line.style_dotted : line.style_solid))
        int nd = 0
        for l in fwLv
            if nd < maxDrawPerFamily and l.k <= time and (l.t == 2 ? dspTl : dspLiq and l.t < 2)
                nd += 1
                int x1 = l.t == 2 ? bar_index - fwNow + l.a : bar_index - 10
                array.push(fwLines, line.new(x1, l.p + l.s * (x1 - bar_index + fwNow - l.a), bar_index, l.p + l.s * (fwNow - l.a), extend = extend.right, color = l.t == 2 ? color.purple : l.d > 0 ? color.orange : color.teal, style = l.t == 2 ? line.style_solid : line.style_dashed))
                if l.t < 2
                    array.push(fwLabels, label.new(bar_index + 2, l.p, l.d > 0 ? "BSL" : "SSL", color = color(na), textcolor = l.d > 0 ? color.orange : color.teal, style = label.style_label_left, size = size.tiny))
        int ne2 = array.size(fwEv)
        if dspLiq and ne2 > 0
            for e = math.max(0, ne2 - maxDrawPerFamily) to ne2 - 1
                FwEv v = array.get(fwEv, e)
                array.push(fwLabels, label.new(v.o, v.p, "SWEEP", xloc.bar_time, color = color(na), textcolor = color.yellow, style = v.d > 0 ? label.style_label_down : label.style_label_up, size = size.tiny))
'''


def compact2(s: str, draw_old: str) -> str:
    assert s.count(draw_old) == 1
    s = s.replace(draw_old, DRAW2)
    a = s.index(TABLE_OLD_START)
    b = s.index(TABLE_OLD_END, a) + len(TABLE_OLD_END)
    s = s[:a] + TABLE_NEW + s[b:]
    a = s.index(Z_OLD_START)
    b = s.index(Z_OLD_END, a) + len(Z_OLD_END)
    s = s[:a] + Z_NEW + s[b:]
    return s
