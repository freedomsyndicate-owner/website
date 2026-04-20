@echo off
title FREEDOM SYNDICATE - PATROLI SYSTEM
color 0b

echo =======================================================
echo    FREEDOM SYNDICATE V11 - SUPREME PATROLI MODE
echo =======================================================
echo.

:: 1. Jalankan Tor Expert Bundle (Pindah IP)
echo [1/3] Menyiapkan Mesin Pindah IP (Tor)...
:: Sesuaikan path tor.exe jika kamu letakkan di folder lain
start "TOR_NETWORK" /min "C:\DOMS_SYSTEM\Tor\tor.exe"
timeout /t 10

:: 2. Jalankan Bot Predator V11
echo [2/3] Menjalankan Global Predator V11...
start "DOMS_PREDATOR" python C:\DOMS_SYSTEM\predator_v11.py
timeout /t 5

:: 3. Jalankan Bot Syndicate Radar (Atau Bot Kedua kamu)
echo [3/3] Menjalankan Syndicate Radar...
start "SYNDICATE_RADAR" python C:\DOMS_SYSTEM\syndicate_radar.py

echo.
echo -------------------------------------------------------
echo [OK] SEMUA SISTEM AKTIF 24 JAM.
echo [!] JANGAN TUTUP JENDELA CMD YANG TERBUKA.
echo -------------------------------------------------------
pause
