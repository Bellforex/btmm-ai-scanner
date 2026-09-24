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

   if(usable == 0)
      return INIT_FAILED;
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   PrintFormat("RC5 EA: deinit reason=%d", reason);
  }

//+------------------------------------------------------------------+
//| EA1 dispatcher. Refreshes live quote state once per closed host  |
//| bar. No signal engine yet, and nothing here can trade.           |
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

      // EA2 attaches the RC5 semantic state here; EA3 maps it to intended
      // trades; EA4 adds lifecycle. Each passes through CanExecuteLive().
     }
  }
//+------------------------------------------------------------------+
