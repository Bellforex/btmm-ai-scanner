//+------------------------------------------------------------------+
//| RC5_SpecCapture.mq5                                              |
//|                                                                  |
//| READ-ONLY broker specification capture for the RC5 EA.           |
//|                                                                  |
//| This is a SCRIPT, not an Expert Advisor, and it contains no      |
//| trading call of any kind -- no OrderSend, no CTrade, no          |
//| PositionClose. It reads SymbolInfo/AccountInfo and writes one    |
//| CSV into MQL5\Files. It is safe to run on a live account with    |
//| AlgoTrading disabled.                                            |
//|                                                                  |
//| Why it exists: the RC5 EA must adapt to the broker's ACTUAL      |
//| contract -- tick size, tick value, volume step, stops level --   |
//| not to account marketing labels. Exness Standard uses suffixed   |
//| symbols (XAUUSDm, EURUSDm, GBPUSDm), so nothing here hardcodes   |
//| an unsuffixed name.                                              |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

//--- Comma-separated symbols. Defaults are the Exness Standard names.
input string InpSymbols = "XAUUSDm,EURUSDm,GBPUSDm";
//--- When true, also scan Market Watch for the unsuffixed roots, so a
//--- different suffix on another server is discovered rather than assumed.
input bool   InpDiscover = true;
input string InpOutFile  = "RC5_broker_spec.csv";

//+------------------------------------------------------------------+
string ModeTrade(const long v)
  {
   switch((ENUM_SYMBOL_TRADE_MODE)v)
     {
      case SYMBOL_TRADE_MODE_DISABLED:  return "DISABLED";
      case SYMBOL_TRADE_MODE_LONGONLY:  return "LONGONLY";
      case SYMBOL_TRADE_MODE_SHORTONLY: return "SHORTONLY";
      case SYMBOL_TRADE_MODE_CLOSEONLY: return "CLOSEONLY";
      case SYMBOL_TRADE_MODE_FULL:      return "FULL";
     }
   return "UNKNOWN";
  }

//--- Filling and expiration modes are bit masks, so report the raw mask
//--- plus the decoded flags; the EA needs the mask to pick a legal fill.
string FillingMask(const long m)
  {
   string s = "";
   if((m & SYMBOL_FILLING_FOK) != 0) s += "FOK ";
   if((m & SYMBOL_FILLING_IOC) != 0) s += "IOC ";
   if(s == "") s = "NONE";
   return s;
  }

//+------------------------------------------------------------------+
bool Resolve(const string want, string &found)
  {
   if(SymbolSelect(want, true)) { found = want; return true; }
   if(!InpDiscover) return false;

   // The root without a trailing lowercase suffix, e.g. XAUUSDm -> XAUUSD.
   string root = want;
   int n = StringLen(root);
   while(n > 0)
     {
      ushort c = StringGetCharacter(root, n - 1);
      if(c >= 'a' && c <= 'z') { root = StringSubstr(root, 0, n - 1); n--; }
      else break;
     }

   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
     {
      string name = SymbolName(i, false);
      if(StringFind(name, root) == 0 && SymbolSelect(name, true))
        {
         found = name;
         return true;
        }
     }
   return false;
  }

//+------------------------------------------------------------------+
void OnStart()
  {
   int h = FileOpen(InpOutFile, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE)
     {
      PrintFormat("RC5_SpecCapture: cannot open %s (err %d)", InpOutFile, GetLastError());
      return;
     }

   PrintFormat("RC5_SpecCapture: broker=%s server=%s login=%I64d",
               AccountInfoString(ACCOUNT_COMPANY),
               AccountInfoString(ACCOUNT_SERVER),
               AccountInfoInteger(ACCOUNT_LOGIN));

   FileWrite(h, "field", "value");
   FileWrite(h, "broker",        AccountInfoString(ACCOUNT_COMPANY));
   FileWrite(h, "server",        AccountInfoString(ACCOUNT_SERVER));
   FileWrite(h, "currency",      AccountInfoString(ACCOUNT_CURRENCY));
   FileWrite(h, "leverage",      (string)AccountInfoInteger(ACCOUNT_LEVERAGE));
   FileWrite(h, "margin_mode",
             AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
             ? "RETAIL_HEDGING"
             : (AccountInfoInteger(ACCOUNT_MARGIN_MODE) == ACCOUNT_MARGIN_MODE_RETAIL_NETTING
                ? "RETAIL_NETTING" : "EXCHANGE"));
   FileWrite(h, "trade_allowed", (string)AccountInfoInteger(ACCOUNT_TRADE_ALLOWED));
   FileWrite(h, "expert_allowed", (string)AccountInfoInteger(ACCOUNT_TRADE_EXPERT));
   FileWrite(h, "terminal_algo", (string)TerminalInfoInteger(TERMINAL_TRADE_ALLOWED));
   FileWrite(h, "");

   FileWrite(h,
             "symbol", "digits", "point", "tick_size", "tick_value",
             "tick_value_profit", "tick_value_loss", "contract_size",
             "vol_min", "vol_max", "vol_step", "stops_level", "freeze_level",
             "trade_mode", "filling_mask", "filling_flags", "expiration_mask",
             "bid", "ask", "spread_points", "spread_price");

   string parts[];
   int cnt = StringSplit(InpSymbols, ',', parts);
   for(int i = 0; i < cnt; i++)
     {
      string want = parts[i];
      StringTrimLeft(want);
      StringTrimRight(want);
      if(want == "") continue;

      string sym = "";
      if(!Resolve(want, sym))
        {
         PrintFormat("RC5_SpecCapture: %s NOT FOUND on this server", want);
         FileWrite(h, want, "NOT_FOUND");
         continue;
        }

      double bid  = SymbolInfoDouble(sym, SYMBOL_BID);
      double ask  = SymbolInfoDouble(sym, SYMBOL_ASK);
      double pt   = SymbolInfoDouble(sym, SYMBOL_POINT);
      long   spd  = SymbolInfoInteger(sym, SYMBOL_SPREAD);
      long   fill = SymbolInfoInteger(sym, SYMBOL_FILLING_MODE);

      FileWrite(h, sym,
                (string)SymbolInfoInteger(sym, SYMBOL_DIGITS),
                DoubleToString(pt, 8),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE), 8),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE), 8),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_PROFIT), 8),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE_LOSS), 8),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_CONTRACT_SIZE), 2),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), 4),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX), 4),
                DoubleToString(SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP), 4),
                (string)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL),
                (string)SymbolInfoInteger(sym, SYMBOL_TRADE_FREEZE_LEVEL),
                ModeTrade(SymbolInfoInteger(sym, SYMBOL_TRADE_MODE)),
                (string)fill,
                FillingMask(fill),
                (string)SymbolInfoInteger(sym, SYMBOL_EXPIRATION_MODE),
                DoubleToString(bid, 8),
                DoubleToString(ask, 8),
                (string)spd,
                DoubleToString(ask - bid, 8));

      PrintFormat("RC5_SpecCapture: %s digits=%d tick=%s stops=%d spread=%d",
                  sym,
                  (int)SymbolInfoInteger(sym, SYMBOL_DIGITS),
                  DoubleToString(SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE), 8),
                  (int)SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL),
                  (int)spd);
     }

   FileClose(h);
   PrintFormat("RC5_SpecCapture: wrote MQL5\\Files\\%s", InpOutFile);
  }
//+------------------------------------------------------------------+
