@echo off
setlocal enabledelayedexpansion
:: WARNA BACKGROUND BIRU (1) TEKS PUTIH (7)
color 1F
title FREEDOM SYNDICATE - OMNI-PROCESSOR V10

:: --- MATRIX LOADING ANIMATION (BIRU) ---
cls
echo.
echo  [SYSTEM] INITIALIZING CYBER RADAR...
set "chars=01ABCDEFGHIJKLMN01OPQRSTUVWXYZ01"
for /L %%i in (1,1,40) do (
    set /a "rand=!random! %% 30"
    for %%j in (!rand!) do set "char=!chars:~%%j,1!"
    cls
    echo.
    echo  [SYSTEM] FREEDOM SYNDICATE V10 - LOADING
    echo  --------------------------------------------------
    echo   !random! !random! FREEDOM !random! !random!
    echo   !random! SYNDICATE !random! !random! PONOROGO
    echo   !char! !char! !char! !char! !char! !char! !char! !char! !char! !char! !char! !char!
    echo  --------------------------------------------------
    timeout /t 0 /nobreak >nul
)

:: --- ASCII ART FREEDOM RAMPING ---
cls
echo.
echo  ============================================================
echo   _______  _______  _______  _______  ______   _______  _______
echo  (  ____ \(  ____ \(  ____ \(  ____ \(  __  \ (  ___  )(       )
echo  | (    \/| (    \/| (    \/| (    \/| (  \  )| (   ) || () () |
echo  | (__    | (__    | (__    | (__    | |   ) || |   | || || || |
echo  |  __)   |  __)   |  __)   |  __)   | |   | || |   | || |(_)| |
echo  | (      | (      | (      | (      | |   ) || |   | || |   | |
echo  | )      | )      | )      | )      | (__/  )| (___) || )   ( |
echo  |/       |/       |/       |/       |______/ (_______)|/     \|
echo.
echo             [ FREEDOM SYNDICATE - PONOROGO ENGINE ]
echo  ============================================================
echo.
echo   [+] STATUS   : SYSTEM ONLINE (DUAL-RADAR)
echo   [+] LEADER   : DOMS (THE GODFATHER)
echo   [+] LOCATION : PONOROGO, INDONESIA
echo   [+] TIME     : %TIME% WIB
echo.
echo  ------------------------------------------------------------
echo   [!] MENGAKTIFKAN PREDATOR + OMNISCIENCE INTEL...
echo  ------------------------------------------------------------
echo.

:: EKSEKUSI BOT (Pake Path Absolut biar aman)
start "DOMS PREDATOR" py "C:\DOMS_SYSTEM\bot_predator.py"
timeout /t 2 >nul
start "DOMS INTEL" py "C:\DOMS_SYSTEM\bot_fundametal.py"

echo.
echo   [OK] SEMUA RADAR SUDAH AKTIF DI JENDELA TERPISAH.
echo   [OK] JANGAN TUTUP JENDELA KONTROL INI.
echo.
echo  ============================================================
pause
