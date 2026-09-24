# THE SCANNER ON TRADINGVIEW IS NOT THE SCANNER IN THE REPOSITORY

The author said the chart "looks like nothing has changed". That was right, and
the reason is not presentation. **Nothing has been deployed since 23 September.**

---

## THE MEASUREMENT

Fetched the deployed source from TradingView's own store
(`pine-facade/get/USER;e2b236547ce4445681c1f3d582906de2/last/`) as
`bellcare1994`, normalised CRLF to LF, and hashed it against the repository.

| | deployed `[RC5 USER]` v18 | repository CORE |
| --- | --- | --- |
| SHA-256 | `9266c10624b5bdbc...` | `79484e120adec018...` |
| characters | 386,313 | 386,278 |
| lines | 7,011 | 7,146 |
| last updated | **2026-09-23 08:41:04 UTC** | commit `1a236d6`, 2026-09-24 04:10 |

**Verdict: STALE BUILD LOADED.**

Note the deployed copy has *more* characters in *fewer* lines. This is not an
older prefix of the same file -- it is a different build, from before the
CORE/VIEW split.

## WHAT THE CHART IS MISSING

Six commits have touched CORE since the deployed copy was saved:

| commit | when | what the chart does not have |
| --- | --- | --- |
| `00674d7` | 09-23 10:05 | **outer means EXTERNAL structure** -- a trendline correctness fix |
| `36d2ebb` | 09-23 19:32 | P1 Arm E Base size |
| `4e65243` | 09-23 21:02 | **the structure-only VIEW split** (CORE measured 98,335) |
| `1e45d4f` | 09-24 01:35 | P2+P3 faithful arrival and the Base family |
| `efd10c8` | 09-24 02:38 | 73 tokens recovered from the parity log |
| `1a236d6` | 09-24 04:10 | **all of P4 formation ownership** (three-point, 100,183) |

Confirmed by identifier probe on the deployed source: `rc5Ownership` 0,
`rc5Ownable` 0, `rc5BaseFam` 0 -- against 2, 2 and 6 in the repository. The
deployed build has `rc5Subordinate` and `rc5LadderRank` from the earlier
authority work, but **not the P4 ownership layer**.

It also still contains the structure drawing (`"BOS"`/`"CHOCH"` present), which
the repository CORE no longer has because that moved to VIEW. That is why the
chart shows BOS/CHOCH marks even though **no `[RC5 VIEW]` script exists on the
account at all** -- the saved list has `[RC5 USER]` and `[RC5 PANEL]` and no
VIEW.

## SO THE DEPLOYMENT IS TWO ACTIONS, NOT ONE

1. save the repository CORE as a new version of `[RC5 USER]`;
2. **create `[RC5 VIEW]`, which does not exist yet**, and add it to the chart.

Until (2) is done, upgrading CORE alone would *remove* the structure overlay
from the chart, because the new CORE does not draw it. Doing only half of this
would look like a regression on stage.

## WHY IT IS NOT DONE YET

The transfer itself is solved and proven: the two sources were carried into the
browser and hashed there against the repository -- CORE `79484e120adec018` and
VIEW `1e6d6b30cdfa7613`, both exact.

What blocked it was the account. The save endpoint returned **401**, and the
browser then reported `window.user.username == STEVECRYPTO1995` -- the account
the project rules forbid state-changing. The `bellcare1994` browser has since
dropped its extension connection, and it is the only place this work may
happen.

**No write of any kind was made to either account.**
