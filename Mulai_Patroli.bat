@echo off
:: Background Hitam, Teks Putih
color 07
title FREEDOM SYNDICATE - PONOROGO ENGINE
cls

echo.
:: Pake warna Biru Terang (9) cuma buat header
color 09
echo  ============================================================
echo     F R E E D O M    S Y N D I C A T E    V 1 0
echo  ============================================================
color 07
echo.
echo   [+] STATUS   : SYSTEM ONLINE
echo   [+] LEADER   : DOMS (THE GODFATHER)
echo   [+] LOCATION : PONOROGO, INDONESIA
echo.
echo  ------------------------------------------------------------
echo   [!] BOOTING DUAL-RADAR (PREDATOR + OMNISCIENCE)...
echo  ------------------------------------------------------------
echo.

:: Paksa masuk folder biar gak salah jalan
cd /d "C:\DOMS_SYSTEM"

:: Buka jendela bot
start "DOMS_PREDATOR" py bot_predator.py
timeout /t 2 >nul
start "DOMS_INTEL" py bot_fundametal.py

echo   [OK] DUA JENDELA BOT SUDAH TERBUKA!
echo   [OK] SILAHKAN CEK TELEGRAM / DISCORD LU.
echo.
echo  ============================================================
echo   JANGAN TUTUP JENDELA INI UNTUK JAGA STABILITAS.
echo  ============================================================
pause
