@echo off
title FREEDOM SYNDICATE SYSTEM
color 0b

echo [1/4] Menghubungkan ke Jaringan Tor...
:: Ganti path di bawah sesuai lokasi instalasi Tor Browser kamu
start "" "C:\Users\%USERNAME%\Desktop\Tor Browser\Browser\firefox.exe"
timeout /t 15

echo [2/4] Menjalankan Predator V11...
start "PREDATOR" python predator_v11.py

echo [3/4] Menjalankan Fundamental Radar...
start "FUNDA" python funda_radar.py

echo [4/4] Menjalankan Syndicate Radar...
start "RADAR" python syndicate_radar.py

echo.
echo ========================================
echo SEMUA SISTEM PATROLI AKTIF 24 JAM!
echo ========================================
pause
