# WHICH SCANNER BUILD IS THIS?

So that the build on the projector can be named exactly, from outside the
script. Nothing here costs a CORE token.

**Repository commit:** `e546749` on `rc5-poi-authority`

| file | source | SHA-256 (LF-normalised) | lines |
| --- | --- | --- | --- |
| **CORE** | `tradingview/btmm_poi_btrc_scanner_rc5_user.pine` | `79484e120adec0180f2c4182d3710a0b...` | 7146 |
| **VIEW** | `tradingview/btmm_poi_btrc_scanner_rc5_view.pine` | `1e6d6b30cdfa76130180f45a9c1c084d...` | 1414 |
| **PANEL** | `tradingview/btmm_poi_btrc_scanner_rc5_panel.pine` | `43953d2e87d268356fe8f39d9622fed5...` | 6968 |

Hashes are over the file with CRLF normalised to LF, which is the form
TradingView stores. To check a deployed script, fetch it from
`pine-facade/get/<id>/last/`, normalise the same way, and hash it -- that is
exactly how the stale build was caught.

**CORE token count: 100,183 / 100,256 (headroom 73)** -- last measured on the
real TradingView compiler at commit `1a236d6`. CORE has not changed since, so
the number still stands, but it is a *recorded* measurement, not one re-taken
this session: re-measuring needs the token oracle, which needs the browser.

**VIEW and PANEL are generated from CORE**, and `tools/rc5_compose.py --check`
reports they match. Verified this session: *RC5 PANEL and VIEW match RC5 CORE*.

---

## DEPLOYED ON TRADINGVIEW (bellcare1994) -- 2026-09-24

Each was saved through TradingView's own store and then **read back and
re-hashed**, so these are verified, not assumed.

| script | scriptIdPart | version | deployed SHA-256 (LF) | matches repo |
| --- | --- | --- | --- | --- |
| `[RC5 USER]` (CORE) | `USER;e2b236547ce4445681c1f3d582906de2` | **19.0** | `79484e120adec018...` | YES |
| `[RC5 VIEW]` | `USER;5c32419eabfd4c85972e73dc2380df9a` | **1.0** | `1e6d6b30cdfa7613...` | YES |
| `[RC5 PANEL]` | `USER;eef6ec5c2f394bf1b5a4176c364a70f5` | **2.0** | `43953d2e87d26835...` | YES |

`[RC5 VIEW]` was **created** in this deployment -- it had never existed on the
account. CORE went 18.0 -> 19.0; TradingView keeps the old versions, so 18.0
remains available if a rollback is ever wanted.

Both CORE and VIEW were test-compiled first on the scratch token-oracle script:
`success: true`, zero errors, for each.

### The chart still needs one manual step

Saving a script does not change a study already on a chart -- TradingView
attaches a cached compiled version. The chart in `BAH-RC5-LAB` is still running
the old CORE until the study is **removed and re-added**, and `[RC5 VIEW]` has
to be added for the first time.

Then set `dspMs` ON in VIEW and `dspTl` ON in CORE, per
`RC5_SCANNER_DEPLOY_RUNBOOK.md` -- both default to false.
