//+------------------------------------------------------------------+
//| RC5_EA.mq5 - BTMM / RC5 scanner, MT5 execution engine            |
//|                                                                  |
//| LAYER EA1: broker adapter, symbol resolution, normalization,     |
//| closed-bar causality, signal identity, and the SINGLE guarded    |
//| execution path. No strategy yet -- EA1 deliberately produces no  |
//| signals and calls no order function.                             |
//|                                                                  |
//| SAFETY. `InpExecutionEnabled` defaults FALSE, and every order    |
//| that will ever exist must pass through `SubmitOrder`, which is   |
//| the only place in this program that may call OrderSend. Nothing  |
//| in EA1 calls it. Live execution additionally requires the        |
//| terminal AND the account to permit algo trading, so a forgotten  |
//| input alone cannot arm it.                                       |
//|                                                                  |
//| BROKER. Nothing is hardcoded to a symbol or account type. Specs  |
//| are read from SymbolInfo at runtime, which is why the pending    |
//| RC5_SpecCapture CSV is validation evidence rather than a         |
//| dependency. Exness Standard exposes suffixed symbols (XAUUSDm,   |
//| EURUSDm, GBPUSDm); the resolver discovers the suffix instead of  |
//| assuming "m".                                                    |
//+------------------------------------------------------------------+
#property copyright "BTMM AI Scanner"
#property version   "1.00"
#property strict

//--- Logical strategy symbols. The broker's real names are resolved.
input string InpSymbolRoots     = "XAUUSD,EURUSD,GBPUSD";
input ENUM_TIMEFRAMES InpHostTF = PERIOD_M15;
//--- MUST default false. See the safety note above.
input bool   InpExecutionEnabled = false;
input double InpRiskPercent      = 0.5;
//--- V1 EXECUTION POLICY, not RC5 analytical doctrine. RC5 specifies no
//--- reward multiple and no risk fraction; these belong to Layer B alone.
input double InpRewardRisk       = 2.0;
//--- Identifies THIS EA's positions. Nothing else is treated as RC5's.
input long   InpMagic            = 5150001;
//--- Required for LIVE execution OUTSIDE the Strategy Tester. This gate only
//--- ever tightens: arming it is not sufficient on its own.
input bool   InpAllowLiveExecution = false;
input ulong  InpSlippagePoints   = 20;
//--- Reference-state fixture file in MQL5\Files. Empty = no setups, which is
//--- the default: the EA never manufactures analytical state of its own.
input string InpSetupFile        = "";

//--- COMMERCIAL LICENSING. The customer receives an EX5 and a key; nothing
//--- secret is embedded here. See the B9 block for the safety rule that a
//--- licence failure may block new entries but NEVER abandon an open trade.
#define RC5_PRODUCT_ID  "RC5-EA"
#define RC5_EA_VERSION  "1.00"
input string InpLicenseKey       = "";
input string InpLicenseUrl       = "https://license.bellforex.app/v1/licenses/validate";
input int    InpLicenseRecheckMinutes = 45;
input int    InpLicenseLeaseHours     = 12;
//--- Strategy Tester ONLY. Requires MQL_TESTER as well; on a live chart this
//--- input is ignored entirely.
input bool   InpLicenseTesterBypass   = false;
//--- EXECUTION DOCTRINE V1 PARAMETERS. Not analytical semantics: RC5
//--- specifies neither a spread tolerance nor a margin ceiling.
input double InpMaxSpreadToRisk  = 0.25;   // spread <= 25% of R
input double InpMaxMarginFraction = 0.20;  // required margin <= 20% of equity
//--- How far price may sit from the POI zone and still be an execution
//--- candidate, measured in SPREADS. tolerance = max(tickSize, spread * this)
input double InpMaxEntryDistanceSpreads = 1.0;
input int    InpMaxSpreadPoints  = 0;      // 0 = no spread filter yet
input bool   InpVerbose          = true;

//+------------------------------------------------------------------+
//| Broker contract for one symbol, read at runtime.                 |
//+------------------------------------------------------------------+
struct RC5SymbolSpec
  {
   string            name;
   int               digits;
   double            point;
   double            tickSize;
   double            tickValue;
   double            tickValueProfit;
   double            tickValueLoss;
   double            contractSize;
   double            volumeMin;
   double            volumeMax;
   double            volumeStep;
   long              stopsLevel;
   long              freezeLevel;
   long              tradeMode;
   long              fillingMode;
   long              expirationMode;
   double            bid;
   double            ask;
   long              spreadPoints;
   bool              valid;
  };

RC5SymbolSpec g_spec[];
string        g_roots[];
datetime      g_lastBar[];

//+------------------------------------------------------------------+
//| Resolve a logical root to the broker's actual symbol name.       |
//|                                                                  |
//| Exact match first; otherwise scan every symbol the server offers |
//| for one that STARTS with the root. That finds XAUUSDm without    |
//| hardcoding "m", and works for any other suffix convention.       |
//+------------------------------------------------------------------+
bool ResolveSymbol(const string root, string &resolved)
  {
   resolved = "";
   if(SymbolSelect(root, true))
     {
      resolved = root;
      return true;
     }

   int total = SymbolsTotal(false);
   string best = "";
   for(int i = 0; i < total; i++)
     {
      string name = SymbolName(i, false);
      if(StringFind(name, root) != 0)
         continue;
      // Prefer the shortest match, so XAUUSDm wins over XAUUSDm.raw
      if(best == "" || StringLen(name) < StringLen(best))
         best = name;
     }
   if(best != "" && SymbolSelect(best, true))
     {
      resolved = best;
      return true;
     }
   return false;
  }

//+------------------------------------------------------------------+
bool ReadSymbolSpec(const string sym, RC5SymbolSpec &s)
  {
   s.valid = false;
   if(sym == "")
      return false;

   s.name            = sym;
   s.digits          = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   s.point           = SymbolInfoDouble(sym, SYMBOL_POINT);
   s.tickSize        = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   s.tickValue       = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   s.tickValueProfit = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_PROFIT);
   s.tickValueLoss   = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS);
   s.contractSize    = SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE);
   s.volumeMin       = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   s.volumeMax       = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   s.volumeStep      = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   s.stopsLevel      = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL);
   s.freezeLevel     = SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL);
   s.tradeMode       = SymbolInfoInteger(sym, SYMBOL_TRADE_MODE);
   s.fillingMode     = SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);
   s.expirationMode  = SymbolInfoInteger(sym, SYMBOL_EXPIRATION_MODE);
   s.bid             = SymbolInfoDouble(sym, SYMBOL_BID);
   s.ask             = SymbolInfoDouble(sym, SYMBOL_ASK);
   s.spreadPoints    = SymbolInfoInteger(sym, SYMBOL_SPREAD);

   // A zero tick size would make price normalization silently wrong, so it is
   // treated as an unusable symbol rather than defaulted to point.
   if(s.tickSize <= 0.0 || s.volumeStep <= 0.0)
      return false;

   s.valid = true;
   return true;
  }

//+------------------------------------------------------------------+
//| Normalize an executable price to the broker's TICK SIZE.         |
//| `_Point` is not the tradable increment on every instrument, so   |
//| it is deliberately not used here.                                |
//+------------------------------------------------------------------+
double NormalizePriceToTick(const RC5SymbolSpec &s, const double price)
  {
   if(!s.valid || s.tickSize <= 0.0)
      return NormalizeDouble(price, s.digits);
   double steps = MathRound(price / s.tickSize);
   return NormalizeDouble(steps * s.tickSize, s.digits);
  }

//+------------------------------------------------------------------+
//| Clamp and quantize a volume to the broker's contract.            |
//| Returns 0.0 when no legal volume exists.                         |
//+------------------------------------------------------------------+
double NormalizeVolume(const RC5SymbolSpec &s, const double volume)
  {
   if(!s.valid || s.volumeStep <= 0.0)
      return 0.0;
   double v = MathFloor(volume / s.volumeStep) * s.volumeStep;
   if(v < s.volumeMin)
      v = s.volumeMin;
   if(v > s.volumeMax)
      v = s.volumeMax;
   // Re-quantize after clamping; min/max need not be multiples of step.
   v = MathFloor(v / s.volumeStep + 0.5) * s.volumeStep;
   int vd = (s.volumeStep >= 1.0) ? 0 : (int)MathCeil(-MathLog10(s.volumeStep));
   v = NormalizeDouble(v, vd);
   return (v < s.volumeMin || v > s.volumeMax) ? 0.0 : v;
  }

//+------------------------------------------------------------------+
//| Is a stop legal against the broker's stop distance?              |
//| Never widens the stop: RC5 stop placement is semantic, and moving|
//| it would change the trade the reference engine specified.        |
//+------------------------------------------------------------------+
bool StopDistanceOk(const RC5SymbolSpec &s, const double entry, const double stop)
  {
   if(!s.valid)
      return false;
   if(s.stopsLevel <= 0)
      return true;
   double minDist = s.stopsLevel * s.point;
   return MathAbs(entry - stop) >= minDist;
  }

double SpreadPrice(const RC5SymbolSpec &s) { return s.ask - s.bid; }

//+------------------------------------------------------------------+
//| EA2-A — ANALYTICAL STATE ADAPTER                                 |
//|                                                                  |
//| A deterministic MQL5 representation of ONE RC5 analytical setup,  |
//| shaped to hold exactly what the Python reference produces. No     |
//| detection lives here yet: EA2-A defines the vocabulary and the    |
//| parity log, so the port that fills it can be checked field by     |
//| field against Python rather than by eyeballing behaviour.         |
//+------------------------------------------------------------------+

//--- Mirrors poi/enums.py PoiDirection.
#define RC5_DIR_NONE     0
#define RC5_DIR_BULLISH  1
#define RC5_DIR_BEARISH -1

//--- Mirrors btrc/enums.py SignalLifecycleState, analytical scope only.
//--- The future-bot states (RISK_VALIDATED..CLOSED) are deliberately absent:
//--- they are Layer B's to supply, and the frozen engine never assigns them.
#define RC5_LC_DETECTED                0
#define RC5_LC_STRUCTURALLY_VALIDATED  1
#define RC5_LC_BTMM_VALIDATED          2
#define RC5_LC_POI_VALIDATED           3
#define RC5_LC_TREND_VALIDATED         4
#define RC5_LC_REGIME_VALIDATED        5
#define RC5_LC_MOMENTUM_VALIDATED      6
#define RC5_LC_LIQUIDITY_VALIDATED     7   // Execution Doctrine V1 trigger

//--- Mirrors poi/rc5_semantics.py Rc5Validity.
#define RC5_VALID        0
#define RC5_INVALIDATED  1
#define RC5_SUPERSEDED   2

//+------------------------------------------------------------------+
struct RC5Setup
  {
   string            symbol;
   ENUM_TIMEFRAMES   timeframe;
   datetime          barTime;        // the CLOSED bar this state belongs to
   string            poiId;          // stable semantic identity
   int               poiType;
   int               direction;      // RC5_DIR_*
   double            zoneTop;
   double            zoneBottom;
   bool              authoritative;  // survived formation + same-origin authority
   int               validity;       // RC5_VALID / INVALIDATED / SUPERSEDED
   bool              p5Permission;   // ANALYTICAL permission, never an order
   int               lifecycle;      // RC5_LC_*
   bool              populated;
  };

//+------------------------------------------------------------------+
//| Distal = the boundary whose violation the frozen engine treats as |
//| genuine invalidation (poi/lifecycle.py::_is_breach):              |
//|   BULLISH -> zone_bottom, BEARISH -> zone_top.                    |
//| Not a convention chosen here; read out of the reference engine.   |
//+------------------------------------------------------------------+
double RC5Distal(const RC5Setup &s)
  {
   return (s.direction == RC5_DIR_BULLISH) ? s.zoneBottom : s.zoneTop;
  }

double RC5Proximal(const RC5Setup &s)
  {
   return (s.direction == RC5_DIR_BULLISH) ? s.zoneTop : s.zoneBottom;
  }

//+------------------------------------------------------------------+
//| Execution Doctrine V1 eligibility. ANALYTICAL state only -- this  |
//| reports whether a setup qualifies, and never places anything.     |
//+------------------------------------------------------------------+
bool RC5EligibleV1(const RC5Setup &s, string &denyReason)
  {
   denyReason = "";
   if(!s.populated)                         { denyReason = "NO_STATE";       return false; }
   if(!s.authoritative)                     { denyReason = "NOT_AUTHORITATIVE"; return false; }
   if(s.validity != RC5_VALID)              { denyReason = "NOT_VALID";      return false; }
   if(!s.p5Permission)                      { denyReason = "NO_P5";          return false; }
   if(s.lifecycle != RC5_LC_LIQUIDITY_VALIDATED) { denyReason = "NOT_CONFIRMED"; return false; }
   if(s.direction == RC5_DIR_NONE)          { denyReason = "NO_DIRECTION";   return false; }
   return true;
  }

//+------------------------------------------------------------------+
//| Compact parity line. Field order is fixed so a Python-side dump   |
//| can be diffed against it directly.                                |
//+------------------------------------------------------------------+
void RC5LogSetup(const RC5Setup &s)
  {
   string reason = "";
   bool eligible = RC5EligibleV1(s, reason);
   int d = (int)SymbolInfoInteger(s.symbol, SYMBOL_DIGITS);
   PrintFormat("RC5SETUP %s|%d|%I64d|%s|%d|%d|%s|%s|%d|%d|%d|%d|%s|%s",
               s.symbol, (int)s.timeframe, (long)s.barTime, s.poiId,
               s.poiType, s.direction,
               DoubleToString(s.zoneTop, d), DoubleToString(s.zoneBottom, d),
               (int)s.authoritative, s.validity, (int)s.p5Permission,
               s.lifecycle,
               (eligible ? "ELIGIBLE" : "DENIED"),
               (eligible ? "-" : reason));
  }

//+------------------------------------------------------------------+
//| THE ONLY PLACE THIS PROGRAM MAY TRADE.                           |
//|                                                                  |
//| Three independent permissions, all required. EA1 never calls     |
//| this; it exists so later layers have exactly one door.           |
//+------------------------------------------------------------------+
bool CanExecuteLive()
  {
   if(!InpExecutionEnabled)
      return false;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED))
      return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_ALLOWED))
      return false;
   if(!AccountInfoInteger(ACCOUNT_TRADE_EXPERT))
      return false;
   return true;
  }

//+------------------------------------------------------------------+
//| Stable identity for one executable decision.                     |
//|                                                                  |
//| Keyed on the formation and the bar that produced it, so the same |
//| POI cannot fire twice on the same event -- the MT5 equivalent of |
//| the scanner's stable POI key.                                    |
//+------------------------------------------------------------------+
string SignalKey(const string sym, const ENUM_TIMEFRAMES tf,
                 const datetime barTime, const int poiType, const int direction)
  {
   return StringFormat("%s|%d|%I64d|%d|%d",
                       sym, (int)tf, (long)barTime, poiType, direction);
  }

//+------------------------------------------------------------------+
//| Closed-bar causality: return true once per completed host bar.   |
//| RC5 confirms on bar close, so an intrabar tick must never create |
//| a decision the reference engine would not have made.             |
//+------------------------------------------------------------------+
bool NewClosedBar(const int idx, const string sym, const ENUM_TIMEFRAMES tf)
  {
   datetime t[];
   if(CopyTime(sym, tf, 1, 1, t) != 1)
      return false;
   if(t[0] == g_lastBar[idx])
      return false;
   g_lastBar[idx] = t[0];
   return true;
  }

//+------------------------------------------------------------------+
void LogSpec(const RC5SymbolSpec &s)
  {
   PrintFormat("RC5 %s digits=%d point=%s tick=%s tickVal=%s vol[%s..%s/%s] "
               "stops=%d freeze=%d fill=%d spread=%d",
               s.name, s.digits,
               DoubleToString(s.point, 8), DoubleToString(s.tickSize, 8),
               DoubleToString(s.tickValue, 5),
               DoubleToString(s.volumeMin, 4), DoubleToString(s.volumeMax, 2),
               DoubleToString(s.volumeStep, 4),
               (int)s.stopsLevel, (int)s.freezeLevel, (int)s.fillingMode,
               (int)s.spreadPoints);
  }

//+------------------------------------------------------------------+
//| EA2-B -- RC5 EXECUTION DOCTRINE V1                               |
//|                                                                  |
//| LAYER SEPARATION. Everything above is RC5: the analytical engine |
//| frozen at Python 28d432e, which produces STATE and never an      |
//| order. Everything in this section is Execution Doctrine V1, a    |
//| SEPARATE downstream layer authored after an audit established    |
//| that RC5 never contained an execution contract. Nothing here is  |
//| a claim about what the scanner has always done.                  |
//|                                                                  |
//| What V1 borrows from RC5 (derived, not invented):                |
//|   trigger  lifecycle == LIQUIDITY_VALIDATED, the last analytical |
//|            state the frozen engine assigns                       |
//|   stop     the distal boundary read out of poi/lifecycle.py      |
//|   exits    the two events the engine calls genuine invalidation  |
//|                                                                  |
//| What V1 decides for itself (execution policy, NOT RC5 doctrine): |
//|   2R take profit, 0.5% risk, one position per symbol.            |
//|   RC5 has never specified a reward multiple or a risk fraction.  |
//+------------------------------------------------------------------+

//--- Layer-B states. These names match the future-bot seam the Python
//--- interface declares (RISK_VALIDATED..CLOSED), but the BEHAVIOUR below is
//--- Execution Doctrine V1's, not something Python implemented.
#define RC5_XB_ANALYTICAL_CONFIRMED  0
#define RC5_XB_RISK_VALIDATED        1
#define RC5_XB_EXECUTION_READY       2
#define RC5_XB_TRIGGERED             3
#define RC5_XB_MANAGED               4
#define RC5_XB_CLOSED                5

//--- Analytical terminal / lifecycle events, and what V1 does about each.
#define RC5_TE_NONE                           0
#define RC5_TE_MITIGATED                      1  // first touch -- NEVER closes
#define RC5_TE_FALSE_INVALIDATION_CONFIRMED   2  // stays VALID -- NEVER closes
#define RC5_TE_GENUINE_INVALIDATION_CONFIRMED 3  // CLOSES
#define RC5_TE_INVALIDATED                    4  // CLOSES
#define RC5_TE_RECLAIM_WITHOUT_DISPLACEMENT   5  // state migration -- NO CLOSE
#define RC5_TE_RECLAIM_FAILED                 6  // state migration -- NO CLOSE
#define RC5_TE_PROMOTED_TO_ORDER_BLOCK        7  // state migration -- NO CLOSE

//--- What RC5TerminalPolicy returns.
#define RC5_TP_NO_ACTION        0
#define RC5_TP_CLOSE            1
//--- RESOLVED as no-close, and logged distinctly because the POI's RECORD
//--- changed even though the position's management did not. It replaced an
//--- earlier pending-doctrine policy once the author ruled on all three.
#define RC5_TP_STATE_MIGRATION  2

//+------------------------------------------------------------------+
//| One intended trade, fully computed. A plan is produced whether   |
//| or not execution is armed, so safe mode logs exactly the trade   |
//| that armed mode would have sent.                                 |
//+------------------------------------------------------------------+
struct RC5Plan
  {
   bool              eligible;
   int               xbState;
   string            signalId;
   string            symbol;
   ENUM_TIMEFRAMES   timeframe;
   int               direction;
   datetime          confirmedAt;   // the analytical bar that confirmed
   datetime          decidedAt;     // when THIS layer decided
   double            entry;
   double            stop;
   double            take;
   double            r;             // |entry - stop|, in price
   double            riskPercent;
   double            riskMoney;     // intended, from equity
   double            realizedRisk;  // what the normalized volume actually risks
   double            volume;
   double            spread;
   double            spreadToRisk;     // spread / R, 0 when R is not known yet
   double            requiredMargin;   // from OrderCalcMargin, never modelled
   double            marginFraction;   // requiredMargin / equity
   double            confirmationClose;   // STAGE 1 reference, from history
   double            confirmationDistance;
   double            entryDistance;       // STAGE 2, the executable price
   double            proximityTolerance;
   double            rTicks;              // diagnostics only -- never enforced
   double            rOverEntry;
   double            tpDistance;
   double            tpOverEntry;
   int               lifecycleTrigger;
   string            denyReason;
  };

//+------------------------------------------------------------------+
//| Stable identity for one executable decision.                     |
//|                                                                  |
//| A bar timestamp alone is not enough: several POIs can confirm on |
//| the same bar, so the POI's own identity is part of the key. The  |
//| confirmation instance (the bar at which LIQUIDITY_VALIDATED      |
//| became causally available) makes a later re-confirmation of the  |
//| same POI a DIFFERENT signal, which is what "at most once per     |
//| semantic setup" means.                                           |
//+------------------------------------------------------------------+
string RC5SignalId(const RC5Setup &s)
  {
   // '~' and NOT '|': the id is embedded in pipe-delimited RC5PLAN and
   // RC5DENY lines, so a pipe inside it would silently break any parser of
   // the journal. Found by writing that parser.
   return StringFormat("%s~%d~%s~%d~%d~%I64d",
                       s.symbol, (int)s.timeframe, s.poiId,
                       s.poiType, s.direction, (long)s.barTime);
  }

//+------------------------------------------------------------------+
//| B1 -- eligibility. Analytical state only; computes no price.     |
//+------------------------------------------------------------------+
bool RC5PlanEligibility(const RC5Setup &s, RC5Plan &p)
  {
   p.eligible         = false;
   p.xbState          = RC5_XB_ANALYTICAL_CONFIRMED;
   p.signalId         = RC5SignalId(s);
   p.symbol           = s.symbol;
   p.timeframe        = s.timeframe;
   p.direction        = s.direction;
   p.confirmedAt      = s.barTime;
   p.decidedAt        = TimeCurrent();
   p.entry            = 0.0;
   p.stop             = 0.0;
   p.take             = 0.0;
   p.r                = 0.0;
   p.riskPercent      = InpRiskPercent;
   p.riskMoney        = 0.0;
   p.realizedRisk     = 0.0;
   p.volume           = 0.0;
   p.spread           = 0.0;
   p.spreadToRisk     = 0.0;
   p.requiredMargin   = 0.0;
   p.marginFraction   = 0.0;
   p.confirmationClose    = 0.0;
   p.confirmationDistance = 0.0;
   p.entryDistance        = 0.0;
   p.proximityTolerance   = 0.0;
   p.rTicks      = 0.0;
   p.rOverEntry  = 0.0;
   p.tpDistance  = 0.0;
   p.tpOverEntry = 0.0;
   p.lifecycleTrigger = s.lifecycle;
   p.denyReason       = "";

   string reason = "";
   if(!RC5EligibleV1(s, reason))
     {
      p.denyReason = reason;
      return false;
     }
   p.eligible = true;
   return true;
  }

//+------------------------------------------------------------------+
//| Is a stop/target distance legal against BOTH broker levels?      |
//|                                                                  |
//| STOPS_LEVEL is the minimum distance from market for an attached  |
//| SL/TP; FREEZE_LEVEL is the band in which an existing order may   |
//| not be modified. V1 checks both and, when either is violated,    |
//| DENIES the trade. It never widens the stop: the distal boundary  |
//| is semantic, and moving it would execute a trade the reference   |
//| engine did not specify.                                          |
//+------------------------------------------------------------------+
bool BrokerLevelsOk(const RC5SymbolSpec &s, const double entry, const double price)
  {
   if(!s.valid)
      return false;
   double dist  = MathAbs(entry - price);
   long   level = MathMax(s.stopsLevel, s.freezeLevel);
   if(level <= 0)
      return true;
   return dist >= level * s.point;
  }

//+------------------------------------------------------------------+
//| B2 -- entry, stop and take profit.                               |
//|                                                                  |
//| ENTRY. The first tradable price AFTER the confirmation became    |
//| causally available: the live ask for a buy, the live bid for a   |
//| sell, read at decision time. There is no backfill and no fill at |
//| the POI price -- the setup is confirmed at a bar close, and the  |
//| only honest entry is what the market offers next.                |
//|                                                                  |
//| STOP. The distal boundary plus one executable tick BEYOND it,    |
//| normalized to SYMBOL_TRADE_TICK_SIZE. `_Point` is not the        |
//| tradable increment on every instrument and is not used.          |
//|                                                                  |
//| TAKE. InpRewardRisk x R. This is V1 EXECUTION POLICY. RC5 has    |
//| never specified a reward multiple.                               |
//+------------------------------------------------------------------+
bool RC5PlanPrices(const RC5SymbolSpec &spec, const RC5Setup &s, RC5Plan &p)
  {
   if(!spec.valid)
     {
      p.denyReason = "SPEC_INVALID";
      return false;
     }

   double bid = SymbolInfoDouble(spec.name, SYMBOL_BID);
   double ask = SymbolInfoDouble(spec.name, SYMBOL_ASK);
   if(bid <= 0.0 || ask <= 0.0)
     {
      p.denyReason = "NO_QUOTE";
      return false;
     }
   p.spread = ask - bid;

   // STAGE 1. Eligibility, from the confirmation bar's own close. Runs before
   // any geometry: a remote POI is not an execution candidate however small a
   // lot would satisfy the risk budget.
   if(!RC5ConfirmationProximity(spec, s, p))
      return false;

   bool   isBuy  = (s.direction == RC5_DIR_BULLISH);
   double entry  = NormalizePriceToTick(spec, isBuy ? ask : bid);
   p.entry = entry;

   // STAGE 2. The ACTUAL executable price -- ask to buy, bid to sell.
   if(!RC5EntryProximity(spec, s, p))
      return false;

   double distal = RC5Distal(s);
   double stop   = NormalizePriceToTick(spec,
                      isBuy ? distal - spec.tickSize : distal + spec.tickSize);

   // The stop must be on the far side of entry. If price has already run
   // through the zone by the time the layer decides, there is no V1 trade.
   if((isBuy && stop >= entry) || (!isBuy && stop <= entry))
     {
      p.entry = entry;
      p.stop  = stop;
      p.denyReason = "STOP_WRONG_SIDE";
      return false;
     }

   double r = MathAbs(entry - stop);
   double take = NormalizePriceToTick(spec,
                    isBuy ? entry + r * InpRewardRisk
                          : entry - r * InpRewardRisk);

   p.entry = entry;
   p.stop  = stop;
   p.take  = take;
   p.r     = r;
   RC5Diagnostics(p, spec);

   if(!StopDistanceOk(spec, entry, stop) || !BrokerLevelsOk(spec, entry, stop))
     {
      p.denyReason = "BROKER_STOP_INVALID";
      return false;
     }
   if(!BrokerLevelsOk(spec, entry, take))
     {
      p.denyReason = "BROKER_TARGET_INVALID";
      return false;
     }
   if(InpMaxSpreadPoints > 0 && spec.spreadPoints > InpMaxSpreadPoints)
     {
      p.denyReason = "SPREAD_TOO_WIDE";
      return false;
     }

   p.xbState = RC5_XB_RISK_VALIDATED;
   return true;
  }

//+------------------------------------------------------------------+
//| B3 -- risk and volume.                                           |
//|                                                                  |
//| Volume is a pure function of account equity, the stop distance   |
//| and the broker's contract. It reads NOTHING about previous       |
//| trades: there is no martingale, no grid, no averaging down, no   |
//| loss-recovery multiplier and no progressive escalation anywhere  |
//| in this program, and the absence is structural rather than a     |
//| setting -- no prior-result term exists to switch on.             |
//|                                                                  |
//| The 0.5% default is V1 TESTER/RESEARCH policy. RC5 specifies no  |
//| risk fraction.                                                   |
//|                                                                  |
//| When the smallest legal volume would risk MORE than the budget,  |
//| V1 denies instead of rounding the risk up. That mirrors the stop |
//| rule: the layer never quietly takes a bigger trade than the one  |
//| it was authorized to take.                                       |
//+------------------------------------------------------------------+
bool RC5PlanRisk(const RC5SymbolSpec &spec, RC5Plan &p)
  {
   if(!spec.valid || p.r <= 0.0 || spec.tickSize <= 0.0)
     {
      p.denyReason = "RISK_MODEL_INVALID";
      return false;
     }

   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
     {
      p.denyReason = "NO_EQUITY";
      return false;
     }
   p.riskMoney = equity * InpRiskPercent / 100.0;
   if(p.riskMoney <= 0.0)
     {
      p.denyReason = "RISK_BUDGET_ZERO";
      return false;
     }

   // Money lost per 1.0 lot per tick. TICK_VALUE_LOSS is the correct side of
   // the contract for a stop; fall back to TICK_VALUE only if the broker does
   // not publish it.
   double perTickPerLot = (spec.tickValueLoss > 0.0) ? spec.tickValueLoss
                                                     : spec.tickValue;
   if(perTickPerLot <= 0.0)
     {
      p.denyReason = "RISK_MODEL_INVALID";
      return false;
     }

   double ticks      = p.r / spec.tickSize;
   double lossPerLot = ticks * perTickPerLot;
   if(lossPerLot <= 0.0)
     {
      p.denyReason = "RISK_MODEL_INVALID";
      return false;
     }

   double desired = p.riskMoney / lossPerLot;

   // Quantize DOWN first, without clamping, so "smaller than the minimum lot"
   // is distinguishable from "a legal size that happens to be the minimum".
   double floored = MathFloor(desired / spec.volumeStep) * spec.volumeStep;
   if(floored < spec.volumeMin - spec.volumeStep * 0.5)
     {
      p.volume       = 0.0;
      p.realizedRisk = spec.volumeMin * lossPerLot;
      p.denyReason   = "RISK_BUDGET_EXCEEDED";
      return false;
     }

   double vol = NormalizeVolume(spec, desired);
   if(vol <= 0.0)
     {
      p.denyReason = "VOLUME_INVALID";
      return false;
     }

   p.volume       = vol;
   p.realizedRisk = vol * lossPerLot;
   if(p.realizedRisk > p.riskMoney * 1.000001)
     {
      p.denyReason = "RISK_BUDGET_EXCEEDED";
      return false;
     }

   p.xbState = RC5_XB_EXECUTION_READY;
   return true;
  }

//+------------------------------------------------------------------+
//| B4 -- signal identity and concurrency.                           |
//|                                                                  |
//| Two independent guards, both required:                           |
//|   * one execution per SEMANTIC SETUP (the signal id), so a       |
//|     confirmed POI cannot re-fire on every subsequent tick or     |
//|     after an EA re-init;                                         |
//|   * at most one RC5 position per RESOLVED BROKER SYMBOL, so      |
//|     there is no pyramiding and no same-symbol hedge.             |
//|                                                                  |
//| Durability: the in-memory list answers the common case, and a    |
//| terminal GlobalVariable keyed by a hash of the id survives an    |
//| OnInit (timeframe change, recompile, reattach) that would empty  |
//| the array. The hash exists only because GlobalVariable names are |
//| length-limited; the full id is what the log records.             |
//+------------------------------------------------------------------+
string g_consumed[];

//--- FNV-1a, 64-bit, used ONLY to name a persistence slot.
string RC5IdHash(const string id)
  {
   ulong h = 1469598103934665603;
   int n = StringLen(id);
   for(int i = 0; i < n; i++)
     {
      h ^= (ulong)StringGetCharacter(id, i);
      h *= 1099511628211;
     }
   return "RC5X_" + StringFormat("%I64X", h);
  }

bool SignalConsumed(const string id)
  {
   int n = ArraySize(g_consumed);
   for(int i = 0; i < n; i++)
      if(g_consumed[i] == id)
         return true;
   return GlobalVariableCheck(RC5IdHash(id));
  }

void MarkSignalConsumed(const string id)
  {
   int n = ArraySize(g_consumed);
   ArrayResize(g_consumed, n + 1);
   g_consumed[n] = id;
   GlobalVariableSet(RC5IdHash(id), (double)TimeCurrent());
  }

//--- Positions this EA owns on one symbol. Other EAs' and manual trades are
//--- deliberately ignored: the magic number is what makes a position "RC5's".
int RC5PositionCount(const string sym)
  {
   int count = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != sym)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      count++;
     }
   return count;
  }

//+------------------------------------------------------------------+
//| Duplicate / concurrency gate. Runs before ANY intended order.    |
//+------------------------------------------------------------------+
bool RC5PlanGuards(const RC5SymbolSpec &spec, RC5Plan &p)
  {
   if(SignalConsumed(p.signalId))
     {
      p.denyReason = "SIGNAL_ALREADY_EXECUTED";
      return false;
     }
   if(RC5PositionCount(spec.name) > 0)
     {
      p.denyReason = "SYMBOL_POSITION_ACTIVE";
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| B5 -- terminal / invalidation mapping.                           |
//|                                                                  |
//| Derived from the frozen engine, not chosen here:                 |
//|                                                                  |
//|  MITIGATED                      NO CLOSE. rc5_semantics.py says  |
//|                                 outright that mitigation is not  |
//|                                 termination -- it is set at the  |
//|                                 FIRST TOUCH. A layer that enters |
//|                                 AT a POI touches it by entering, |
//|                                 so closing here would close      |
//|                                 every trade at its own entry.    |
//|                                                                  |
//|  FALSE_INVALIDATION_CONFIRMED   NO CLOSE. The engine keeps the   |
//|                                 setup VALID; closing would exit  |
//|                                 exactly the trap the doctrine    |
//|                                 exists to survive.               |
//|                                                                  |
//|  GENUINE_INVALIDATION_CONFIRMED CLOSE.                           |
//|  PoiTerminalReason.INVALIDATED  CLOSE.                           |
//|                                                                  |
//| Deliberately NOT closes, and deliberately not listed above:      |
//| an opposite analytical pattern, a trend-direction change, and    |
//| the appearance of a new authoritative POI. None of them is an    |
//| invalidation of THIS setup.                                      |
//|                                                                  |
//|  RECLAIM_WITHOUT_DISPLACEMENT  NO CLOSE. A PoiLifecycleStatus,   |
//|  RECLAIM_FAILED                 not a PoiTerminalReason: neither  |
//|                                 sets `terminal`, the walk         |
//|                                 continues past both, and the POI  |
//|                                 stays VALID. Closing would        |
//|                                 contradict the analytical layer.  |
//|                                                                  |
//|  PROMOTED_TO_ORDER_BLOCK        NO CLOSE on an OPEN position.     |
//|                                 It IS terminal, but rc5_validity  |
//|                                 maps it to SUPERSEDED and states  |
//|                                 it is NOT a failure -- the RC3    |
//|                                 rule ends an engulfing record     |
//|                                 when its ORDER BLOCK record       |
//|                                 becomes available, so the         |
//|                                 formation lives on under a new    |
//|                                 record. NEW entries are already   |
//|                                 blocked, with no extra rule,      |
//|                                 because SUPERSEDED is not VALID.  |
//|                                 Promotion also never opens a      |
//|                                 second trade.                    |
//|                                                                  |
//| All three log <EVENT>_STATE_MIGRATION. Author-locked V1 policy,   |
//| decided from what the frozen engine does, not assumed.            |
//+------------------------------------------------------------------+
int RC5TerminalPolicy(const int ev)
  {
   switch(ev)
     {
      case RC5_TE_GENUINE_INVALIDATION_CONFIRMED:
      case RC5_TE_INVALIDATED:
         return RC5_TP_CLOSE;

      case RC5_TE_RECLAIM_WITHOUT_DISPLACEMENT:
      case RC5_TE_RECLAIM_FAILED:
      case RC5_TE_PROMOTED_TO_ORDER_BLOCK:
         return RC5_TP_STATE_MIGRATION;

      case RC5_TE_MITIGATED:
      case RC5_TE_FALSE_INVALIDATION_CONFIRMED:
      case RC5_TE_NONE:
         return RC5_TP_NO_ACTION;
     }
   return RC5_TP_NO_ACTION;
  }

string RC5TerminalName(const int ev)
  {
   switch(ev)
     {
      case RC5_TE_NONE:                           return "NONE";
      case RC5_TE_MITIGATED:                      return "MITIGATED";
      case RC5_TE_FALSE_INVALIDATION_CONFIRMED:   return "FALSE_INVALIDATION_CONFIRMED";
      case RC5_TE_GENUINE_INVALIDATION_CONFIRMED: return "GENUINE_INVALIDATION_CONFIRMED";
      case RC5_TE_INVALIDATED:                    return "INVALIDATED";
      case RC5_TE_RECLAIM_WITHOUT_DISPLACEMENT:   return "RECLAIM_WITHOUT_DISPLACEMENT";
      case RC5_TE_RECLAIM_FAILED:                 return "RECLAIM_FAILED";
      case RC5_TE_PROMOTED_TO_ORDER_BLOCK:        return "PROMOTED_TO_ORDER_BLOCK";
     }
   return "UNKNOWN";
  }

//+------------------------------------------------------------------+
//| B6 -- the execution adapter.                                     |
//|                                                                  |
//| EVERY OrderSend in this program is inside this section, and both |
//| of them are behind CanExecuteHere(). There is no other path to   |
//| the market.                                                      |
//+------------------------------------------------------------------+

//--- Fifth gate, and it only ever TIGHTENS. Inside the Strategy Tester the
//--- four existing permissions are enough; outside it, live execution
//--- additionally requires this input to be armed deliberately. Nothing here
//--- makes live trading easier in order to make testing possible.
bool CanExecuteHere()
  {
   if(!CanExecuteLive())
      return false;
   if(MQLInfoInteger(MQL_TESTER))
      return true;
   return InpAllowLiveExecution;
  }

//--- The broker publishes a mask; sending an unsupported fill is rejected.
ENUM_ORDER_TYPE_FILLING PickFilling(const RC5SymbolSpec &s)
  {
   if((s.fillingMode & SYMBOL_FILLING_FOK) != 0)
      return ORDER_FILLING_FOK;
   if((s.fillingMode & SYMBOL_FILLING_IOC) != 0)
      return ORDER_FILLING_IOC;
   return ORDER_FILLING_RETURN;
  }

//+------------------------------------------------------------------+
//| SAFE-MODE RECORD. Emitted for every decision, armed or not, so   |
//| a tester run and a Python reference dump can be diffed field by  |
//| field before a single order is ever sent.                        |
//+------------------------------------------------------------------+
void RC5LogPlan(const RC5SymbolSpec &spec, const RC5Plan &p, const string verdict)
  {
   PrintFormat("RC5PLAN %s|%s|%s|%d|%s|conf=%I64d|dec=%I64d|entry=%s|sl=%s|tp=%s|"
               "R=%s|riskPct=%s|riskMoney=%s|realized=%s|vol=%s|spread=%s|spreadToR=%s|margin=%s|marginFrac=%s|confDist=%s|entryDist=%s|tol=%s|Rticks=%s|R/entry=%s|TPdist=%s|TP/entry=%s|lc=%d|xb=%d|%s",
               verdict, p.signalId, p.symbol, (int)p.timeframe,
               (p.direction == RC5_DIR_BULLISH ? "BUY"
                : (p.direction == RC5_DIR_BEARISH ? "SELL" : "NONE")),
               (long)p.confirmedAt, (long)p.decidedAt,
               DoubleToString(p.entry, spec.digits),
               DoubleToString(p.stop,  spec.digits),
               DoubleToString(p.take,  spec.digits),
               DoubleToString(p.r,     spec.digits),
               DoubleToString(p.riskPercent, 2),
               DoubleToString(p.riskMoney, 2),
               DoubleToString(p.realizedRisk, 2),
               DoubleToString(p.volume, 2),
               DoubleToString(p.spread, spec.digits),
               DoubleToString(p.spreadToRisk, 4),
               DoubleToString(p.requiredMargin, 2),
               DoubleToString(p.marginFraction, 4),
               DoubleToString(p.confirmationDistance, spec.digits),
               DoubleToString(p.entryDistance, spec.digits),
               DoubleToString(p.proximityTolerance, spec.digits),
               DoubleToString(p.rTicks, 1),
               DoubleToString(p.rOverEntry, 6),
               DoubleToString(p.tpDistance, spec.digits),
               DoubleToString(p.tpOverEntry, 6),
               p.lifecycleTrigger, p.xbState,
               (p.denyReason == "" ? "-" : p.denyReason));
  }

//+------------------------------------------------------------------+
//| THE ONLY OrderSend THAT OPENS A POSITION.                        |
//+------------------------------------------------------------------+
bool SubmitOrder(const RC5SymbolSpec &spec, RC5Plan &p)
  {
   if(!CanExecuteHere())
     {
      p.denyReason = "EXECUTION_DISABLED";
      return false;
     }
   // LICENCE GATE -- on the OPEN path only. CloseRC5Position deliberately has
   // no equivalent check: a lapsed licence must never leave a position
   // unmanaged. See the B9 block.
   if(!RC5LicenseAllowsNewEntries())
     {
      p.denyReason = "LICENSE_MANAGE_ONLY_" + RC5LicenseStateName(g_licenseState);
      PrintFormat("RC5LIC %s new entry BLOCKED (%s); open positions keep "
                  "their SL, TP and approved invalidation exits",
                  RC5MaskKey(InpLicenseKey),
                  RC5LicenseStateName(g_licenseState));
      return false;
     }

   MqlTradeRequest  req;
   MqlTradeResult   res;
   ZeroMemory(req);
   ZeroMemory(res);

   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = spec.name;
   req.volume       = p.volume;
   req.type         = (p.direction == RC5_DIR_BULLISH) ? ORDER_TYPE_BUY
                                                       : ORDER_TYPE_SELL;
   req.price        = p.entry;
   req.sl           = p.stop;
   req.tp           = p.take;
   req.deviation    = InpSlippagePoints;
   req.magic        = InpMagic;
   req.comment      = "RC5V1";
   req.type_filling = PickFilling(spec);

   if(!OrderSend(req, res))
     {
      p.denyReason = StringFormat("ORDER_SEND_FAILED_%d", res.retcode);
      return false;
     }
   if(res.retcode != TRADE_RETCODE_DONE && res.retcode != TRADE_RETCODE_PLACED)
     {
      p.denyReason = StringFormat("ORDER_REJECTED_%d", res.retcode);
      return false;
     }

   p.xbState = RC5_XB_TRIGGERED;
   return true;
  }

//+------------------------------------------------------------------+
//| THE ONLY OrderSend THAT CLOSES A POSITION.                       |
//| Reached exclusively from a RC5_TP_CLOSE policy decision.         |
//+------------------------------------------------------------------+
bool CloseRC5Position(const RC5SymbolSpec &spec, const string why)
  {
   if(!CanExecuteHere())
      return false;

   bool any = false;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != spec.name)
         continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;

      long dir = PositionGetInteger(POSITION_TYPE);

      MqlTradeRequest req;
      MqlTradeResult  res;
      ZeroMemory(req);
      ZeroMemory(res);
      req.action       = TRADE_ACTION_DEAL;
      req.position     = ticket;
      req.symbol       = spec.name;
      req.volume       = PositionGetDouble(POSITION_VOLUME);
      req.type         = (dir == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL
                                                    : ORDER_TYPE_BUY;
      req.price        = (dir == POSITION_TYPE_BUY)
                         ? SymbolInfoDouble(spec.name, SYMBOL_BID)
                         : SymbolInfoDouble(spec.name, SYMBOL_ASK);
      req.deviation    = InpSlippagePoints;
      req.magic        = InpMagic;
      req.comment      = "RC5V1X";
      req.type_filling = PickFilling(spec);

      bool ok = OrderSend(req, res);
      PrintFormat("RC5CLOSE %s ticket=%I64u why=%s ok=%d retcode=%d",
                  spec.name, ticket, why, (int)ok, (int)res.retcode);
      any = any || ok;
     }
   return any;
  }

//+------------------------------------------------------------------+
//| Apply an analytical terminal event to a live RC5 position.       |
//| The policy table in B5 decides; this only carries it out.        |
//+------------------------------------------------------------------+
void RC5OnTerminalEvent(const RC5SymbolSpec &spec, const int ev, const string poiId)
  {
   int policy = RC5TerminalPolicy(ev);
   string name = RC5TerminalName(ev);

   if(policy == RC5_TP_STATE_MIGRATION)
     {
      // V1 DECISION, author-locked. The record moved; the trade did not.
      // A promoted engulfing continues to exist as its ORDER BLOCK record and
      // a reclaim state leaves the POI VALID, so none of the three is a
      // failure of the setup this position was opened on. Management stays
      // with the existing SL, the existing TP, and the two approved
      // invalidation exits.
      PrintFormat("RC5TERM %s poi=%s event=%s %s_STATE_MIGRATION "
                  "(NO CLOSE; management continues on SL/TP + the two "
                  "approved invalidation exits)",
                  spec.name, poiId, name, name);
      return;
     }
   if(policy != RC5_TP_CLOSE)
     {
      if(InpVerbose)
         PrintFormat("RC5TERM %s poi=%s event=%s NO_CLOSE (non-terminal for V1)",
                     spec.name, poiId, name);
      return;
     }

   if(RC5PositionCount(spec.name) == 0)
     {
      PrintFormat("RC5TERM %s poi=%s event=%s CLOSE_REQUESTED but no RC5 position",
                  spec.name, poiId, name);
      return;
     }
   if(!CanExecuteHere())
     {
      PrintFormat("RC5TERM %s poi=%s event=%s CLOSE_REQUESTED "
                  "(safe mode -- not sent)", spec.name, poiId, name);
      return;
     }
   CloseRC5Position(spec, name);
  }

//+------------------------------------------------------------------+
//| B1..B6 in order, for one analytical setup.                       |
//|                                                                  |
//| The WHOLE pipeline runs whether or not execution is armed. In    |
//| safe mode the only thing that does not happen is the OrderSend,  |
//| which is what makes the safe-mode log a faithful preview.        |
//+------------------------------------------------------------------+
bool RC5ProcessSetup(const RC5SymbolSpec &spec, const RC5Setup &s)
  {
   RC5Plan p;

   if(!RC5PlanEligibility(s, p))  { RC5LogPlan(spec, p, "DENIED"); return false; }
   if(!RC5PlanGuards(spec, p))    { RC5LogPlan(spec, p, "DENIED"); return false; }
   if(!RC5PlanPrices(spec, s, p)) { RC5LogPlan(spec, p, "DENIED"); return false; }
   // Gate 1 before sizing: no point costing a trade the spread disqualifies.
   if(!RC5SpreadGate(spec, p))    { RC5LogPlan(spec, p, "DENIED"); return false; }
   if(!RC5PlanRisk(spec, p))      { RC5LogPlan(spec, p, "DENIED"); return false; }
   // Gate 2 after sizing: margin is a function of the volume just computed.
   if(!RC5MarginGate(spec, p))    { RC5LogPlan(spec, p, "DENIED"); return false; }

   if(!CanExecuteHere())
     {
      RC5LogPlan(spec, p, "WOULD_EXECUTE");
      return false;
     }

   bool sent = SubmitOrder(spec, p);
   if(sent)
      MarkSignalConsumed(p.signalId);
   RC5LogPlan(spec, p, sent ? "EXECUTED" : "DENIED");
   return sent;
  }

//+------------------------------------------------------------------+
//| B7 -- FIXTURE FEED (tester / parity only).                        |
//|                                                                  |
//| THIS IS NOT A LIVE SIGNAL SOURCE. The MT5 side of RC5 has no      |
//| detector: the analytical engine is Python (frozen at 28d432e) and |
//| Pine. What this reads is a file of ALREADY-DECIDED analytical     |
//| state, exported from the reference engine, in exactly the field   |
//| order RC5LogSetup prints. Its purpose is to let a Strategy Tester |
//| run drive Execution Doctrine V1 with REAL reference state so the  |
//| EA's decisions can be diffed against the Python expectation,      |
//| instead of against state the EA invented for itself.              |
//|                                                                  |
//| Format, one setup per line, '#' starts a comment:                 |
//|   symbol|tf|barTimeEpoch|poiId|poiType|direction|zoneTop|         |
//|   zoneBottom|authoritative|validity|p5|lifecycle                  |
//|                                                                  |
//| `symbol` is the LOGICAL root (XAUUSD); the broker's real name is  |
//| resolved at runtime, so a fixture is portable across servers.     |
//+------------------------------------------------------------------+
RC5Setup g_fixtures[];
bool     g_fixtureDone[];

bool ParseFixtureLine(const string line, RC5Setup &s)
  {
   string f[];
   if(StringSplit(line, '|', f) != 12)
      return false;
   for(int i = 0; i < 12; i++)
     {
      StringTrimLeft(f[i]);
      StringTrimRight(f[i]);
     }

   s.symbol        = f[0];
   s.timeframe     = (ENUM_TIMEFRAMES)(int)StringToInteger(f[1]);
   s.barTime       = (datetime)StringToInteger(f[2]);
   s.poiId         = f[3];
   s.poiType       = (int)StringToInteger(f[4]);
   s.direction     = (int)StringToInteger(f[5]);
   s.zoneTop       = StringToDouble(f[6]);
   s.zoneBottom    = StringToDouble(f[7]);
   s.authoritative = (StringToInteger(f[8]) != 0);
   s.validity      = (int)StringToInteger(f[9]);
   s.p5Permission  = (StringToInteger(f[10]) != 0);
   s.lifecycle     = (int)StringToInteger(f[11]);
   s.populated     = true;

   // A zone with top below bottom is a broken export, not a tradable setup.
   return (s.zoneTop >= s.zoneBottom && s.poiId != "");
  }

int LoadFixtures(const string file)
  {
   ArrayResize(g_fixtures, 0);
   ArrayResize(g_fixtureDone, 0);
   if(file == "")
      return 0;

   // The Strategy Tester sandboxes file access PER AGENT: a file in the
   // terminal's own MQL5\Files is invisible to
   // Tester\Agent-...\MQL5\Files, which is where a tester FileOpen looks.
   // Measured, not assumed -- a run failed here with error 5004 while the
   // file sat in the terminal folder. So try the local sandbox first, then
   // the SHARED Common\Files folder, which both environments can reach.
   bool common = false;
   int h = FileOpen(file, FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE)
     {
      h = FileOpen(file, FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
      common = (h != INVALID_HANDLE);
     }
   if(h == INVALID_HANDLE)
     {
      PrintFormat("RC5 EA: fixture file %s not found in either the local or "
                  "the common sandbox (err %d) -- pipeline idle",
                  file, GetLastError());
      return 0;
     }
   PrintFormat("RC5 EA: fixture file %s opened from the %s sandbox",
               file, (common ? "COMMON" : "local"));

   int n = 0, bad = 0;
   while(!FileIsEnding(h))
     {
      string line = FileReadString(h);
      StringTrimLeft(line);
      StringTrimRight(line);
      if(line == "" || StringGetCharacter(line, 0) == '#')
         continue;

      RC5Setup s;
      if(!ParseFixtureLine(line, s))
        {
         bad++;
         continue;
        }
      ArrayResize(g_fixtures, n + 1);
      ArrayResize(g_fixtureDone, n + 1);
      g_fixtures[n]    = s;
      g_fixtureDone[n] = false;
      n++;
     }
   FileClose(h);
   PrintFormat("RC5 EA: loaded %d fixture setups from %s (%d unparseable)",
               n, file, bad);
   return n;
  }

//--- Dispatch every fixture whose confirmation bar has now CLOSED on this
//--- symbol. `<=` rather than `==` so a fixture whose exact bar was skipped
//--- by the tester's data is still seen once, and never before its time.
void DispatchFixtures(const RC5SymbolSpec &spec, const string root,
                      const datetime closedBarTime)
  {
   int n = ArraySize(g_fixtures);
   for(int i = 0; i < n; i++)
     {
      if(g_fixtureDone[i])
         continue;
      if(g_fixtures[i].symbol != root && g_fixtures[i].symbol != spec.name)
         continue;
      if(g_fixtures[i].barTime > closedBarTime)
         continue;

      // The EA trades the broker's symbol, whatever the fixture called it.
      RC5Setup s = g_fixtures[i];
      s.symbol = spec.name;

      g_fixtureDone[i] = true;
      RC5LogSetup(s);
      RC5ProcessSetup(spec, s);
     }
  }

//+------------------------------------------------------------------+
//| B8 -- EXECUTION QUALITY GATES                                    |
//|                                                                  |
//| Two gates that the monetary risk budget provably does NOT cover. |
//| Both are EXECUTION DOCTRINE V1 PARAMETERS, not frozen analytical |
//| semantics: RC5 specifies neither a spread tolerance nor a margin |
//| ceiling, and zero-height POIs remain fully valid ANALYTICALLY.   |
//| Nothing here deletes or invalidates a POI; it only refuses to    |
//| TRADE one.                                                       |
//|                                                                  |
//| WHY THEY EXIST -- measured, not imagined. A real generated        |
//| fixture produced a liquidity-level POI with                       |
//| zone_top == zone_bottom, entry 1.14832, R about 2 ticks against a |
//| spread of about 10 ticks, sized to 200.00 lots (~20,000,000 EUR). |
//| Realized risk was 40.00 against a 50.00 budget, so EVERY existing |
//| risk gate PASSED. The trade was nevertheless stopped out by       |
//| transaction cost alone, and its gross exposure was bounded only   |
//| by the broker's volume_max -- a contract limit, not a risk rule.  |
//|                                                                  |
//| Neither gate special-cases zero-height zones. Any setup whose R   |
//| is small relative to the spread, or whose margin is large         |
//| relative to equity, has the same problem whatever its geometry.   |
//+------------------------------------------------------------------+

//--- spread <= InpMaxSpreadToRisk * R. The boundary is INCLUSIVE.
double SpreadToRisk(const double spread, const double r)
  {
   return (r > 0.0) ? spread / r : 0.0;
  }

//--- Required margin for the intended order, from the BROKER. This asks
//--- OrderCalcMargin rather than reimplementing MT5's margin engine, because
//--- a second implementation would be a second thing to be wrong.
bool RequiredMargin(const RC5SymbolSpec &spec, const RC5Plan &p, double &margin)
  {
   margin = 0.0;
   ENUM_ORDER_TYPE type = (p.direction == RC5_DIR_BULLISH) ? ORDER_TYPE_BUY
                                                           : ORDER_TYPE_SELL;
   return OrderCalcMargin(type, spec.name, p.volume, p.entry, margin);
  }

//+------------------------------------------------------------------+
//| Gate 1 -- transaction cost against the planned stop.             |
//| Runs right after prices, before any sizing: there is no point    |
//| computing a volume for a trade the spread already disqualifies.  |
//+------------------------------------------------------------------+
bool RC5SpreadGate(const RC5SymbolSpec &spec, RC5Plan &p)
  {
   if(p.r <= 0.0)
     {
      p.denyReason = "R_ZERO";
      return false;
     }
   p.spreadToRisk = SpreadToRisk(p.spread, p.r);
   if(p.spread > InpMaxSpreadToRisk * p.r)
     {
      p.denyReason = "SPREAD_TO_RISK_INVALID";
      PrintFormat("RC5DENY SPREAD_TO_RISK_INVALID %s|spread=%s|R=%s|ratio=%s|max=%s",
                  p.signalId,
                  DoubleToString(p.spread, spec.digits),
                  DoubleToString(p.r, spec.digits),
                  DoubleToString(p.spreadToRisk, 4),
                  DoubleToString(InpMaxSpreadToRisk, 4));
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Gate 2 -- gross exposure against equity.                         |
//| Runs AFTER sizing, because margin is a function of the volume.   |
//| The broker's volume_max is NOT a substitute for this: it bounds  |
//| the contract, not the account.                                   |
//+------------------------------------------------------------------+
bool RC5MarginGate(const RC5SymbolSpec &spec, RC5Plan &p)
  {
   double equity = AccountInfoDouble(ACCOUNT_EQUITY);
   if(equity <= 0.0)
     {
      p.denyReason = "NO_EQUITY";
      return false;
     }
   double margin = 0.0;
   if(!RequiredMargin(spec, p, margin))
     {
      // A broker that will not price the margin is a broker this layer will
      // not trade blind against.
      p.denyReason = "MARGIN_UNAVAILABLE";
      return false;
     }
   p.requiredMargin = margin;
   p.marginFraction = margin / equity;
   if(margin > equity * InpMaxMarginFraction)
     {
      p.denyReason = "MARGIN_EXPOSURE_INVALID";
      PrintFormat("RC5DENY MARGIN_EXPOSURE_INVALID %s|margin=%s|equity=%s|"
                  "fraction=%s|max=%s|vol=%s|entry=%s|sl=%s",
                  p.signalId,
                  DoubleToString(margin, 2), DoubleToString(equity, 2),
                  DoubleToString(p.marginFraction, 4),
                  DoubleToString(InpMaxMarginFraction, 4),
                  DoubleToString(p.volume, 2),
                  DoubleToString(p.entry, spec.digits),
                  DoubleToString(p.stop, spec.digits));
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| B7 -- TWO-STAGE POI PROXIMITY                                    |
//|                                                                  |
//| The gate that closes the stale-POI hole. A setup can be          |
//| authoritative, VALID, P5-permitted and LIQUIDITY_VALIDATED while |
//| price is nowhere near the zone: the first real trigger this       |
//| project found was a HAMMER at 308.75-312.85 while gold traded     |
//| near 4,400, and it passed the monetary risk, spread/R and margin  |
//| gates simultaneously.                                            |
//|                                                                  |
//| ANALYTICAL VALIDITY IS UNTOUCHED. That POI is still a valid POI;  |
//| V1 simply refuses to TRADE it. Nothing here deletes, invalidates  |
//| or ages out a record, and there is deliberately NO POI AGE CAP:   |
//| age alone does not prove irrelevance, and a decades-old level     |
//| genuinely revisited by price would pass this gate on its merits.  |
//|                                                                  |
//| TWO STAGES, BOTH REQUIRED:                                       |
//|   1. the causally available CONFIRMATION close must be near the   |
//|      zone -- eligibility, evaluated without any future price;     |
//|   2. the ACTUAL executable price (ask to buy, bid to sell) must   |
//|      STILL be near it at the moment of the order.                 |
//+------------------------------------------------------------------+

//--- B7a. Distance from a price to the nearest zone edge; 0 when inside.
double ZoneDistance(const double price, const double zoneTop,
                    const double zoneBottom)
  {
   if(price < zoneBottom)
      return zoneBottom - price;
   if(price > zoneTop)
      return price - zoneTop;
   return 0.0;
  }

//--- The tolerance is built from what the BROKER publishes, not from R and not
//--- from a percentage of price.
//---
//--- NOT a fraction of R, because a stale far-away zone produces an enormous R:
//--- an R-relative test would grant MORE slack the further away the zone is,
//--- which is exactly backwards. NOT a fraction of price either, because that
//--- behaves completely differently on EURUSD and on gold.
double ProximityTolerance(const RC5SymbolSpec &spec, const double spread)
  {
   double scaled = spread * InpMaxEntryDistanceSpreads;
   return MathMax(spec.tickSize, scaled);
  }

//--- The confirmation close of the bar the setup was confirmed ON. Read from
//--- history by time, never from the live tick: this is an eligibility test
//--- and must not see a price that did not exist at confirmation.
bool ConfirmationClose(const string sym, const ENUM_TIMEFRAMES tf,
                       const datetime barTime, double &out)
  {
   double c[];
   if(CopyClose(sym, tf, barTime, 1, c) != 1)
      return false;
   out = c[0];
   return true;
  }

//+------------------------------------------------------------------+
//| B7b -- STAGE 1, confirmation proximity.                          |
//| Runs BEFORE any geometry or sizing: a remote POI is not an       |
//| execution candidate however small a lot would satisfy the risk   |
//| budget, so there is no point computing one.                      |
//+------------------------------------------------------------------+
bool RC5ConfirmationProximity(const RC5SymbolSpec &spec, const RC5Setup &s,
                              RC5Plan &p)
  {
   double close = 0.0;
   if(!ConfirmationClose(spec.name, s.timeframe, s.barTime, close))
     {
      p.denyReason = "CONFIRMATION_CLOSE_UNAVAILABLE";
      return false;
     }

   p.confirmationClose = close;
   p.confirmationDistance = ZoneDistance(close, s.zoneTop, s.zoneBottom);
   p.proximityTolerance = ProximityTolerance(spec, p.spread);

   if(p.confirmationDistance > p.proximityTolerance)
     {
      p.denyReason = "CONFIRMATION_PROXIMITY_INVALID";
      PrintFormat("RC5DENY CONFIRMATION_PROXIMITY_INVALID %s|price=%s|"
                  "zone=%s..%s|distance=%s|spread=%s|tick=%s|tolerance=%s",
                  p.signalId,
                  DoubleToString(close, spec.digits),
                  DoubleToString(s.zoneBottom, spec.digits),
                  DoubleToString(s.zoneTop, spec.digits),
                  DoubleToString(p.confirmationDistance, spec.digits),
                  DoubleToString(p.spread, spec.digits),
                  DoubleToString(spec.tickSize, spec.digits),
                  DoubleToString(p.proximityTolerance, spec.digits));
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| B7c -- STAGE 2, entry proximity.                                 |
//| The ACTUAL executable price, ask to buy and bid to sell. The     |
//| confirmation close is NOT substituted here: it is a hindsight    |
//| price the layer could never have been filled at.                 |
//+------------------------------------------------------------------+
bool RC5EntryProximity(const RC5SymbolSpec &spec, const RC5Setup &s, RC5Plan &p)
  {
   p.entryDistance = ZoneDistance(p.entry, s.zoneTop, s.zoneBottom);
   if(p.entryDistance > p.proximityTolerance)
     {
      p.denyReason = "ENTRY_PROXIMITY_INVALID";
      PrintFormat("RC5DENY ENTRY_PROXIMITY_INVALID %s|price=%s|"
                  "zone=%s..%s|distance=%s|spread=%s|tick=%s|tolerance=%s",
                  p.signalId,
                  DoubleToString(p.entry, spec.digits),
                  DoubleToString(s.zoneBottom, spec.digits),
                  DoubleToString(s.zoneTop, spec.digits),
                  DoubleToString(p.entryDistance, spec.digits),
                  DoubleToString(p.spread, spec.digits),
                  DoubleToString(spec.tickSize, spec.digits),
                  DoubleToString(p.proximityTolerance, spec.digits));
      return false;
     }
   return true;
  }

//+------------------------------------------------------------------+
//| B7d -- R / TP DIAGNOSTICS. Recorded, never enforced.             |
//|                                                                  |
//| V1 deliberately has NO maximum-R and NO maximum-TP-distance gate. |
//| Once proximity passes, R reflects LOCAL zone geometry rather than |
//| the distance to some remote stale level, and the existing three   |
//| gates already bound the trade. These numbers exist so a future    |
//| threshold can be calibrated from evidence instead of guessed at.  |
//+------------------------------------------------------------------+
void RC5Diagnostics(RC5Plan &p, const RC5SymbolSpec &spec)
  {
   p.rTicks     = (spec.tickSize > 0.0) ? p.r / spec.tickSize : 0.0;
   p.rOverEntry = (p.entry > 0.0) ? p.r / p.entry : 0.0;
   p.tpDistance = MathAbs(p.take - p.entry);
   p.tpOverEntry = (p.entry > 0.0) ? p.tpDistance / p.entry : 0.0;
  }

//+------------------------------------------------------------------+
//| B9 -- COMMERCIAL LICENSING                                       |
//|                                                                  |
//| THE SECURITY TARGET IS COMMERCIAL-GRADE CONTROLLED ACCESS, NOT   |
//| UNCRACKABILITY. This EX5 runs on the customer's machine and can  |
//| be inspected; nothing here pretends otherwise. What it does buy  |
//| is real: keys cannot be guessed, a licence can be revoked        |
//| centrally, and one key cannot quietly run on many accounts.      |
//|                                                                  |
//| NOTHING SECRET IS EMBEDDED. No database password, no admin       |
//| token, no signing key. The EA is an untrusted client and is      |
//| built like one: it asks a server and believes the answer, and    |
//| the worst a decompiler yields is the endpoint URL.               |
//|                                                                  |
//| THE SAFETY RULE THAT OUTRANKS EVERY OTHER RULE HERE:             |
//|                                                                  |
//|   A LICENCE FAILURE MUST NEVER ABANDON AN OPEN TRADE.            |
//|                                                                  |
//| An expired, revoked or unreachable licence blocks NEW positions  |
//| and nothing else. Existing positions keep their stop, their      |
//| target and their approved invalidation exits. A customer whose   |
//| subscription lapses mid-trade is not punished with an unmanaged  |
//| position -- that would be a worse outcome than piracy.           |
//+------------------------------------------------------------------+

//--- Licence states. Mirrors licensing/service.py LicenseState; a Python test
//--- asserts the two lists agree, so they cannot drift apart silently.
#define RC5_LIC_VALID              0
#define RC5_LIC_GRACE              1
#define RC5_LIC_INVALID            2
#define RC5_LIC_EXPIRED            3
#define RC5_LIC_REVOKED            4
#define RC5_LIC_ACCOUNT_MISMATCH   5
#define RC5_LIC_ACTIVATION_LIMIT   6
#define RC5_LIC_SERVER_UNREACHABLE 7
#define RC5_LIC_VERSION_BLOCKED    8
#define RC5_LIC_TESTER_BYPASS      9

int      g_licenseState   = RC5_LIC_INVALID;
datetime g_licenseChecked = 0;
datetime g_leaseUntil     = 0;
string   g_licenseId      = "";

string RC5LicenseStateName(const int s)
  {
   switch(s)
     {
      case RC5_LIC_VALID:              return "LICENSE_VALID";
      case RC5_LIC_GRACE:              return "LICENSE_GRACE";
      case RC5_LIC_INVALID:            return "LICENSE_INVALID";
      case RC5_LIC_EXPIRED:            return "LICENSE_EXPIRED";
      case RC5_LIC_REVOKED:            return "LICENSE_REVOKED";
      case RC5_LIC_ACCOUNT_MISMATCH:   return "LICENSE_ACCOUNT_MISMATCH";
      case RC5_LIC_ACTIVATION_LIMIT:   return "LICENSE_ACTIVATION_LIMIT";
      case RC5_LIC_SERVER_UNREACHABLE: return "LICENSE_SERVER_UNREACHABLE";
      case RC5_LIC_VERSION_BLOCKED:    return "LICENSE_VERSION_BLOCKED";
      case RC5_LIC_TESTER_BYPASS:      return "LICENSE_TESTER_BYPASS";
     }
   return "LICENSE_UNKNOWN";
  }

//+------------------------------------------------------------------+
//| The ONLY form of the key that may ever be printed.               |
//| RC5-ABCDE-FGHIJ-KLMNO-PQRST -> RC5-ABCDE-***-PQRST               |
//+------------------------------------------------------------------+
string RC5MaskKey(const string key)
  {
   string parts[];
   if(StringSplit(key, '-', parts) < 3)
      return "RC5-****";
   return parts[0] + "-" + parts[1] + "-***-" + parts[ArraySize(parts) - 1];
  }

//--- Where the cached lease lives. FILE_COMMON so it survives a data-folder
//--- move and is reachable from the tester, exactly like the fixture file.
string RC5LeasePath()
  {
   return "RC5_lease_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN))
          + ".txt";
  }

//+------------------------------------------------------------------+
//| A lease is only usable for the EXACT context that earned it.     |
//| Key, account, server, product and version all bind, so a lease   |
//| cannot be copied to another account or survive a version block.  |
//+------------------------------------------------------------------+
string RC5LeaseFingerprint()
  {
   return StringFormat("%s|%I64d|%s|%s|%s",
                       RC5MaskKey(InpLicenseKey),
                       AccountInfoInteger(ACCOUNT_LOGIN),
                       AccountInfoString(ACCOUNT_SERVER),
                       RC5_PRODUCT_ID,
                       RC5_EA_VERSION);
  }

void RC5SaveLease(const datetime until, const string licenseId)
  {
   int h = FileOpen(RC5LeasePath(),
                    FILE_WRITE | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return;
   FileWriteString(h, RC5LeaseFingerprint() + "\n");
   FileWriteString(h, IntegerToString((long)until) + "\n");
   FileWriteString(h, licenseId + "\n");
   FileClose(h);
  }

//--- Returns the lease expiry, or 0 when there is no USABLE lease. A lease
//--- for a different account/server/version is treated as absent, not as a
//--- weaker yes.
datetime RC5LoadLease(string &licenseId)
  {
   licenseId = "";
   int h = FileOpen(RC5LeasePath(),
                    FILE_READ | FILE_TXT | FILE_ANSI | FILE_COMMON);
   if(h == INVALID_HANDLE)
      return 0;
   string fingerprint = FileReadString(h);
   string untilText   = FileReadString(h);
   string id          = FileIsEnding(h) ? "" : FileReadString(h);
   FileClose(h);

   if(fingerprint != RC5LeaseFingerprint())
      return 0;
   licenseId = id;
   return (datetime)StringToInteger(untilText);
  }

//+------------------------------------------------------------------+
//| Ask the licensing service. Returns the resulting state.          |
//|                                                                  |
//| WebRequest needs the URL allow-listed in the terminal; when it is |
//| not, this reports SERVER_UNREACHABLE rather than failing open.    |
//+------------------------------------------------------------------+
int RC5ValidateLicenseOnline()
  {
   string payload = StringFormat(
      "{\"license_key\":\"%s\",\"product_id\":\"%s\",\"ea_version\":\"%s\","
      "\"account_login\":\"%I64d\",\"account_server\":\"%s\",\"nonce\":\"%I64d\"}",
      InpLicenseKey, RC5_PRODUCT_ID, RC5_EA_VERSION,
      AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER),
      (long)TimeLocal());

   char post[], result[];
   string headers = "Content-Type: application/json\r\n";
   string response_headers = "";
   StringToCharArray(payload, post, 0, StringLen(payload), CP_UTF8);

   ResetLastError();
   int code = WebRequest("POST", InpLicenseUrl, headers, 8000,
                         post, result, response_headers);
   if(code != 200)
     {
      int err = GetLastError();
      // MEASURED, not assumed: inside the Strategy Tester WebRequest returns
      // -1 with 4014 (ERR_FUNCTION_NOT_ALLOWED) and the request never leaves
      // the terminal. No allow-list entry can fix that, so pointing a
      // back-testing customer at Tools > Options would send them in circles.
      if(MQLInfoInteger(MQL_TESTER))
         PrintFormat("RC5LIC %s licence cannot be validated in the Strategy "
                     "Tester: MetaTrader does not permit WebRequest there "
                     "(http=%d err=%d). Set InpLicenseTesterBypass=true to "
                     "back-test; it has no effect on a live chart.",
                     RC5MaskKey(InpLicenseKey), code, err);
      else
         PrintFormat("RC5LIC %s server unreachable (http=%d err=%d) -- "
                     "add %s to Tools > Options > Expert Advisors > WebRequest",
                     RC5MaskKey(InpLicenseKey), code, err, InpLicenseUrl);
      return RC5_LIC_SERVER_UNREACHABLE;
     }

   string body = CharArrayToString(result, 0, WHOLE_ARRAY, CP_UTF8);
   // Deliberately a substring read rather than a JSON parser: the contract is
   // three fields and a thousand-line parser is a liability in a product that
   // must not crash a customer's terminal.
   bool ok = (StringFind(body, "\"valid\": true") >= 0
              || StringFind(body, "\"valid\":true") >= 0);

   int state = RC5_LIC_INVALID;
   if(ok)
      state = RC5_LIC_VALID;
   else if(StringFind(body, "LICENSE_REVOKED") >= 0)
      state = RC5_LIC_REVOKED;
   else if(StringFind(body, "LICENSE_EXPIRED") >= 0)
      state = RC5_LIC_EXPIRED;
   else if(StringFind(body, "LICENSE_ACTIVATION_LIMIT") >= 0)
      state = RC5_LIC_ACTIVATION_LIMIT;
   else if(StringFind(body, "LICENSE_VERSION_BLOCKED") >= 0)
      state = RC5_LIC_VERSION_BLOCKED;
   else if(StringFind(body, "LICENSE_ACCOUNT_MISMATCH") >= 0)
      state = RC5_LIC_ACCOUNT_MISMATCH;

   if(state == RC5_LIC_VALID)
     {
      g_leaseUntil = TimeCurrent() + (datetime)(InpLicenseLeaseHours * 3600);
      RC5SaveLease(g_leaseUntil, g_licenseId);
     }
   return state;
  }

//+------------------------------------------------------------------+
//| The licence decision, including the tester bypass.               |
//|                                                                  |
//| THE BYPASS CANNOT ACTIVATE ON A LIVE CHART. It requires BOTH     |
//| MQLInfoInteger(MQL_TESTER) and an explicit input that defaults    |
//| false. Setting the input alone does nothing outside the tester,  |
//| which is asserted by a static regression test.                   |
//+------------------------------------------------------------------+
int RC5EvaluateLicense()
  {
   if(MQLInfoInteger(MQL_TESTER) && InpLicenseTesterBypass)
      return RC5_LIC_TESTER_BYPASS;

   if(StringLen(InpLicenseKey) == 0)
      return RC5_LIC_INVALID;

   int state = RC5ValidateLicenseOnline();
   if(state == RC5_LIC_SERVER_UNREACHABLE)
     {
      // GRACE: a cached, context-bound lease keeps a paying customer trading
      // through a dropped connection. An expired or absent lease does not.
      string leasedId = "";
      datetime until = RC5LoadLease(leasedId);
      if(until > TimeCurrent())
        {
         g_leaseUntil = until;
         g_licenseId  = leasedId;
         return RC5_LIC_GRACE;
        }
     }
   return state;
  }

//--- May this program OPEN a new position? Licence-gated.
bool RC5LicenseAllowsNewEntries()
  {
   return (g_licenseState == RC5_LIC_VALID
           || g_licenseState == RC5_LIC_GRACE
           || g_licenseState == RC5_LIC_TESTER_BYPASS);
  }

//+------------------------------------------------------------------+
//| Refresh on a timer, never on a tick.                             |
//| Trading decisions must not block on an HTTP round trip.          |
//+------------------------------------------------------------------+
void RC5RefreshLicense(const bool force = false)
  {
   datetime now = TimeCurrent();
   if(!force && g_licenseChecked > 0
      && (now - g_licenseChecked) < (datetime)(InpLicenseRecheckMinutes * 60))
      return;

   int previous = g_licenseState;
   g_licenseState   = RC5EvaluateLicense();
   g_licenseChecked = now;

   if(previous != g_licenseState)
      PrintFormat("RC5LIC %s state %s -> %s | newEntries=%s | "
                  "openPositionsUnaffected=TRUE",
                  RC5MaskKey(InpLicenseKey),
                  RC5LicenseStateName(previous),
                  RC5LicenseStateName(g_licenseState),
                  (RC5LicenseAllowsNewEntries() ? "ALLOWED" : "BLOCKED"));
  }

//+------------------------------------------------------------------+
int OnInit()
  {
   int n = StringSplit(InpSymbolRoots, ',', g_roots);
   if(n <= 0)
     {
      Print("RC5 EA: no symbol roots configured");
      return INIT_PARAMETERS_INCORRECT;
     }

   ArrayResize(g_spec, n);
   ArrayResize(g_lastBar, n);

   int usable = 0;
   for(int i = 0; i < n; i++)
     {
      StringTrimLeft(g_roots[i]);
      StringTrimRight(g_roots[i]);
      g_lastBar[i] = 0;

      string resolved = "";
      if(!ResolveSymbol(g_roots[i], resolved))
        {
         PrintFormat("RC5 EA: %s NOT AVAILABLE on this server", g_roots[i]);
         g_spec[i].valid = false;
         continue;
        }
      if(!ReadSymbolSpec(resolved, g_spec[i]))
        {
         PrintFormat("RC5 EA: %s -> %s spec unusable (tickSize/volumeStep)",
                     g_roots[i], resolved);
         continue;
        }
      usable++;
      PrintFormat("RC5 EA: %s -> %s", g_roots[i], resolved);
      if(InpVerbose)
         LogSpec(g_spec[i]);
     }

   PrintFormat("RC5 EA v1.00 EA1: %d/%d symbols usable | execution=%s | "
               "terminal_algo=%d account_algo=%d | account=%s %s lev=1:%d",
               usable, n,
               (InpExecutionEnabled ? "ENABLED" : "DISABLED (safe mode)"),
               (int)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED),
               (int)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED),
               AccountInfoString(ACCOUNT_COMPANY),
               AccountInfoString(ACCOUNT_CURRENCY),
               (int)AccountInfoInteger(ACCOUNT_LEVERAGE));

   LoadFixtures(InpSetupFile);

   RC5RefreshLicense(true);
   EventSetTimer(60);
   PrintFormat("RC5LIC %s %s | newEntries=%s | product=%s v%s | tester=%d",
               RC5MaskKey(InpLicenseKey),
               RC5LicenseStateName(g_licenseState),
               (RC5LicenseAllowsNewEntries() ? "ALLOWED" : "BLOCKED"),
               RC5_PRODUCT_ID, RC5_EA_VERSION,
               (int)MQLInfoInteger(MQL_TESTER));
   PrintFormat("RC5 EA2-B: trigger=LIQUIDITY_VALIDATED | RR=%s | risk=%s%% | magic=%I64d | tester=%d | liveArmed=%d | canExecute=%d",
               DoubleToString(InpRewardRisk, 2), DoubleToString(InpRiskPercent, 2),
               InpMagic, (int)MQLInfoInteger(MQL_TESTER),
               (int)InpAllowLiveExecution, (int)CanExecuteHere());

   if(usable == 0)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   PrintFormat("RC5 EA: deinit reason=%d", reason);
  }

//+------------------------------------------------------------------+
//| EA1 dispatcher. Refreshes live quote state once per closed host  |
//| bar. No signal engine yet, and nothing here can trade.           |
//+------------------------------------------------------------------+
//| Licensing is refreshed HERE, never in OnTick: a trading decision  |
//| must not block on an HTTP round trip.                             |
//+------------------------------------------------------------------+
void OnTimer()
  {
   RC5RefreshLicense(false);
  }

//+------------------------------------------------------------------+
void OnTick()
  {
   int n = ArraySize(g_spec);
   for(int i = 0; i < n; i++)
     {
      if(!g_spec[i].valid)
         continue;
      if(!NewClosedBar(i, g_spec[i].name, InpHostTF))
         continue;

      g_spec[i].bid          = SymbolInfoDouble(g_spec[i].name, SYMBOL_BID);
      g_spec[i].ask          = SymbolInfoDouble(g_spec[i].name, SYMBOL_ASK);
      g_spec[i].spreadPoints = SymbolInfoInteger(g_spec[i].name, SYMBOL_SPREAD);

      if(InpVerbose)
         PrintFormat("RC5 %s closed bar | bid=%s ask=%s spread=%d pts (%s)",
                     g_spec[i].name,
                     DoubleToString(g_spec[i].bid, g_spec[i].digits),
                     DoubleToString(g_spec[i].ask, g_spec[i].digits),
                     (int)g_spec[i].spreadPoints,
                     DoubleToString(SpreadPrice(g_spec[i]), g_spec[i].digits));

      // EA2-B: drive Execution Doctrine V1 from REFERENCE state only. With no
      // fixture file this loop dispatches nothing, which is the whole point --
      // the EA has no detector and must never act as if it had one.
      DispatchFixtures(g_spec[i], g_roots[i], g_lastBar[i]);
     }
  }
//+------------------------------------------------------------------+
