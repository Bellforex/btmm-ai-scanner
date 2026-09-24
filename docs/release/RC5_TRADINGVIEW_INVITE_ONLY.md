# RC5 SCANNER — INVITE-ONLY COMMERCIAL ACCESS

Everything needed to sell and grant scanner access at the event. **Nothing here
publishes anything** — the final publish button needs the author's explicit
word.

---

## 0. ELIGIBILITY — CONFIRMED

Checked on the authorized account, not assumed:

| | |
| --- | --- |
| account | **`bellcare1994`** |
| plan | **`pro_premium`** (Premium) |
| billing | monthly, **26 days** remaining at check time |
| invite-only publication | **SUPPORTED** — Premium or Ultimate is the requirement |

One thing to watch: the plan renews monthly. **If the plan lapses, invite-only
management goes with it**, so the renewal matters commercially, not just
personally.

## 1. THE PUBLICATION TYPE — and the one that would be wrong

Use **PUBLIC + INVITE-ONLY**.

Do **not** use a *private* script for customer sales. A private script is a
personal draft; it is not TradingView's commercial-distribution path, and
access management there does not do what a paying customer needs.

**No licence key goes inside Pine.** TradingView's own access control is the
mechanism — a key embedded in a script would be visible to anyone with access
and shareable by anyone who has it.

## 2. WHY ACCESS CANNOT LEAK LIKE A KEY

There is no reusable invitation link. The author grants permission to a
**specific TradingView user** through **Manage Access**.

So if Customer A hands Customer B a link, B still has nothing: B must be
separately authorized by the author. This is a genuinely stronger position than
the EA's, where the binary is in the customer's hands.

## 3. THE ACCESS IDENTITY IS THE TRADINGVIEW USERNAME

Ask for the **exact TradingView username**. Not the email, not the display
name.

Collect an email as well — for the BellForex customer record and for support —
but **an email is not the access identity** unless TradingView's own UI
resolves it to an account.

**Confirm the spelling with the customer before granting.** A mistyped username
grants a stranger and leaves your customer locked out, and at an event both
happen in front of a queue.

## 4. GRANTING — the steps, in order

1. customer registers and pays
2. customer gives their **exact TradingView username**
3. record it in the access registry
4. **read it back to them and confirm**
5. open the invite-only publication
6. **Manage Access**
7. add the exact username
8. set the **expiration** for their plan
9. confirm access appears in the list
10. mark `TV_GRANTED` in the registry

Customer then: **Indicators → Invite-only scripts → RC5 Scanner → add to
chart**.

## 5. EXPIRATION AND REVOCATION

TradingView supports **per-user expiration**. Use it rather than relying on
remembering to remove people.

| plan | expiration |
| --- | --- |
| trial | 7 days |
| monthly | 30 days |
| lifetime | no expiration, per commercial policy |

*Durations are placeholders — the author sets pricing and terms.*

Revocation is the same screen: remove the user, or let the expiry lapse. Do
both through **Manage Access**; there is no other lever.

## 6. WHAT THE CUSTOMER NEVER RECEIVES

* no `.pine` source file
* no CORE, VIEW or PANEL source
* no repository access

Invite-only publication protects the source from ordinary users, which is
exactly why it is the distribution path. **Do not email source to anyone**,
including a customer who asks for "just a look".

## 7. VENDOR RULES — what the description must and must not say

TradingView's vendor requirements apply. In particular:

* **no profitability claims**, no "guaranteed", no win-rate promises;
* explain plainly how to request access (TradingView username);
* describe what the script does, its limits and its supported markets.

Two sentences that must never appear anywhere: a performance guarantee, and any
suggestion that the scanner predicts price. It identifies structure and points
of interest; that is the claim, and it is true.

---

## 8. PUBLICATION DRAFT

### Title

`RC5 BTMM Structure & POI Scanner — Invite Only`

### Short description

A market-structure and point-of-interest scanner implementing a BTMM-style
reading of price: confirmed swings, BOS/CHOCH transitions, and the zones where
structure was decided — order blocks, bases, fair value gaps, reversal
formations and liquidity references.

It marks **where** the market made a decision. It does not predict what happens
next, and it places no orders.

### Full description

**What it draws**

* market structure — HH / HL / LH / LL on confirmed swings only, with BOS and
  CHOCH transitions drawn at the candle that broke the level
* points of interest — order blocks, bases (rally-base-rally and
  drop-base-drop), fair value gaps, engulfing and star formations, pressure
  wicks, doji and liquidity references
* a structural trendline layer built from protected and broken swing roles
* per-zone lifecycle: a POI is shown while it is live and stops being shown
  when the engine considers it finished

**What makes it different**

Every zone is attributed to the structural decision that produced it. When two
readings describe the same formation — a Base and a candle pattern inside it —
the scanner resolves which one *owns* the decision rather than drawing both and
leaving you to guess.

**Supported**

* any symbol TradingView provides
* designed and verified on M5 through H4; the structure engine runs on any
  timeframe
* two scripts: **CORE** (analysis and zones) and **VIEW** (structure overlay),
  designed to run together

**Limitations — stated plainly**

* it is an analysis tool, not a signal service and not financial advice
* it does not predict direction and makes no performance claim
* zones are drawn on **confirmed** bars; nothing repaints on a closed bar, and
  nothing is shown before the engine could causally have known it
* higher-timeframe context affects results, so the same symbol on two
  timeframes will legitimately differ

### Author instructions (the field customers read)

> Access is granted per TradingView account.
>
> To request access, send your **exact TradingView username** (not your email
> address) to [contact]. Access is added manually and normally within [window].
>
> Once granted, open **Indicators → Invite-only scripts** and add RC5 Scanner
> to your chart.
>
> Access is per-user and cannot be shared or transferred. If your access
> expires, message [contact] to renew.

### Release notes — v1.0 Event Release

```
RC5 Scanner v1.0
- structure: confirmed swings, BOS/CHOCH, HH/HL/LH/LL labelling
- POIs: order blocks, bases, FVGs, reversal formations, pressure wicks,
  doji, liquidity references
- formation ownership: a Base owns contained and co-extensive patterns
- structural trendline layer
- CORE + VIEW release pair
```

---

## 9. CUSTOMER INTAKE FORM

| field | notes |
| --- | --- |
| Full name | |
| Email | customer record, not the access identity |
| WhatsApp | |
| **TradingView username** | **exact — read back and confirm** |
| EA required? | YES / NO |
| MT5 account login | only if an EA licence is requested |
| MT5 broker server | the EA binds to LOGIN + SERVER |
| Access plan | trial / monthly / lifetime |
| Payment reference | |
| Start date | |
| Expiry date | |
| Status | |

## 10. ACCESS REGISTRY

`release/event/Licensing/access_registry.csv` — columns:

```
CUSTOMER, EMAIL, WHATSAPP, TRADINGVIEW_USERNAME, TV_ACCESS_STATUS, TV_EXPIRY,
EA_LICENSE_ID, MT5_LOGIN, MT5_SERVER, EA_EXPIRY, PAYMENT_STATUS, NOTES
```

Status values: `PENDING`, `TV_GRANTED`, `EA_GRANTED`, `ACTIVE`, `EXPIRED`,
`REVOKED`.

**Record the EA licence ID, never the key.** The key is shown once at creation
and given to the customer; the registry holds the ID so support can revoke or
extend without ever handling a working key.

---

## 11. PUBLICATION AUTHORIZATION

Preparing this publication: **authorized**.
Pressing publish: **NOT authorized** until the author says PUBLISH.

Nothing in this document has been published, and no script access has been
granted.
