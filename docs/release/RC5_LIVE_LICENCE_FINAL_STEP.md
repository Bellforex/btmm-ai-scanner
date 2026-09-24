# THE ONE STEP I COULD NOT DO — AND HOW TO FINISH IT IN A MINUTE

Everything on the software side of live licence validation is verified. One
thing is left, it needs a checkbox, and a checkbox is the only way to set it.

---

## WHY IT IS NOT DONE

MetaTrader keeps the WebRequest allow-list inside the terminal's **encrypted
`settings.ini`**. There is no config-file key, no command-line flag and no file
I can write. The only route is **Tools → Options → Expert Advisors**.

I did not drive that dialog with synthetic keystrokes, because this terminal is
logged into a **real-money account** (`Exness-MT5Real10`) and a stray keystroke
in a trading terminal is not an acceptable risk to take on your behalf.

## WHAT IS ALREADY SET UP

| | |
| --- | --- |
| licence server | running on `127.0.0.1:8713`, health returns `{"status":"ok"}` |
| demo licence | `LIC-20260924-2BR03`, ACTIVE, bound to your MT5 login and server |
| EA preset | `MQL5/Presets/RC5_livecheck.set` — key filled in, **execution disabled three ways** |
| startup config | `config/RC5_livecheck.ini` — attaches the EA to XAUUSDm M15 |
| recheck interval | **1 minute**, so the licence state flips while you watch |

`RC5_livecheck.set` contains the demo licence key in plain text. It is a
two-day demo on your own machine; **delete the file when you are done.**

## THE STEP

1. Open MetaTrader normally.
2. **Tools → Options → Expert Advisors**.
3. Tick **Allow WebRequest for listed URL**.
4. Add exactly:

```
http://127.0.0.1:8713
```

5. OK.

Then start the terminal with the prepared config:

```bash
"C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe" /config:"C:\Users\user\AppData\Roaming\MetaQuotes\Terminal\53785E099C927DB68A545C249CDBCE06\config\RC5_livecheck.ini"
```

## WHAT YOU SHOULD SEE — within about a minute

```
RC5LIC RC5-HYQVJ-***-2BR03 state LICENSE_INVALID -> LICENSE_VALID | newEntries=ALLOWED | openPositionsUnaffected=TRUE
```

Nothing will trade: `InpExecutionEnabled=false`, `InpAllowLiveExecution=false`
and AutoTrading is off. The most the EA can log is `WOULD_EXECUTE`.

## THEN THE TWO TESTS THAT MATTER

Leave the terminal running. In a shell, with the pepper set:

```bash
python -m licensing.admin --db <event.db> revoke LIC-20260924-2BR03
```

Within a minute the Experts log must show:

```
RC5LIC ... state LICENSE_VALID -> LICENSE_REVOKED | newEntries=BLOCKED | openPositionsUnaffected=TRUE
```

Then:

```bash
python -m licensing.admin --db <event.db> reactivate LIC-20260924-2BR03
```

and it must return to `LICENSE_VALID | newEntries=ALLOWED`, with
`activations 1/1` unchanged — the reactivate must not consume a second slot.

That exact sequence has already passed over HTTP against the same server and
the same store. What this run adds is the **EA** as the client instead of a
command-line tool.

## AND THE QUESTION IT ALSO ANSWERS

With the URL allow-listed, run the **Strategy Tester** once with
`InpLicenseTesterBypass=false`. If it still reports `err=4014`, the tester
prohibition is real and we can finally say so as a measurement. If it validates,
then the earlier tester failure was only ever the missing allow-list.

Right now we do not know which, and nothing we ship claims to.
