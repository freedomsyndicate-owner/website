@echo off
setlocal enabledelayedexpansion
:: WARNA BIRU BACKGROUND (1) TEKS PUTIH (7)
color 1F
title FREEDOM SYNDICATE OMNI-PROCESSOR V10

:LOADING
cls
echo.
echo  [SYSTEM] INITIALIZING CYBER RADAR...
set "bar=##################################################"
for /L %%i in (1,1,50) do (
    cls
    echo.
    echo  [SYSTEM] LOADING FREEDOM SYNDICATE V10
    echo  --------------------------------------------------
    set "progress=!bar:~0,%%i!"
    echo  [!progress!] %%i%%
    echo  --------------------------------------------------
    timeout /t 0 /nobreak >nul
)

:MAIN
cls
echo.
echo  ============================================================
echo     _______  _______  _______  _______  _______  _______ 
echo    (  ____ \(  ____ \(  ____ \(  ____ \(  ____ \(       )
echo    | (    \/| (    \/| (    \/| (    \/| (    \/| () () |
echo    | (__    | (__    | (__    | (__    | (__    | || || |
echo    |  __)   |  __)   |  __)   |  __)   |  __)   | |(_)| |
echo    | (      | (      | (      | (      | (      | |   | |
echo    | )      | )      | )      | )      | )      | )   ( |
echo    |/       |/       |/       |/       |/       |/     \|
echo.
echo             [ FREEDOM SYNDICATE - PONOROGO ENGINE ]
echo  ============================================================
echo.
echo   [+] STATUS   : SYSTEM ONLINE
echo   [+] LEADER   : DOMS (THE GODFATHER)
echo   [+] LOCATION : PONOROGO, INDONESIA
echo   [+] TIME     : %TIME%
echo.
echo  ------------------------------------------------------------
echo   [!] MENGAKTIFKAN DUAL-RADAR (PREDATOR + OMNISCIENCE)...
echo  ------------------------------------------------------------
echo.

:: EKSEKUSI BOT (PASTIKAN NAMA FILE .PY SUDAH BENAR)
start "DOMS PREDATOR" py bot_predator.py
timeout /t 2 >nul
start "DOMS INTEL" py bot_fundametal.py

echo.
echo   [OK] SEMUA RADAR SUDAH AKTIF DI JENDELA TERPISAH.
echo   [OK] JANGAN TUTUP JENDELA INI UNTUK MENJAGA SYNC.
echo.
echo  ============================================================
pause
