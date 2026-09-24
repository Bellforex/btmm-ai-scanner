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
