@echo off
REM ---------------------------------------------------------------------
REM  RC5 licence desk wrapper.
REM
REM  So event staff type          rc5-license create --customer "Jane" ...
REM  instead of                   python -m licensing.admin --db ... create ...
REM
REM  Set these two once, per machine, before the event:
REM     RC5_LICENSE_PEPPER   the secret. Never committed, never given out.
REM     RC5_LICENSE_DB       full path to the licence database.
REM ---------------------------------------------------------------------
setlocal

if "%RC5_LICENSE_PEPPER%"=="" (
  echo.
  echo   RC5_LICENSE_PEPPER is not set. Refusing to run.
  echo.
  echo   Without the pepper this command would create licences that the
  echo   live server cannot verify. Set it first:
  echo.
  echo       set RC5_LICENSE_PEPPER=^<the event pepper^>
  echo.
  exit /b 2
)

if "%RC5_LICENSE_DB%"=="" set RC5_LICENSE_DB=%~dp0licenses.db

python -m licensing.admin --db "%RC5_LICENSE_DB%" %*
exit /b %ERRORLEVEL%
