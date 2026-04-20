@echo off
title Freedom Syndicate - Global Predator & Supreme Radar
echo ---------------------------------------------------
echo Memulai Global Predator V11 dan Supreme Radar V1...
echo Pastikan TOR BROWSER sudah terbuka!
echo ---------------------------------------------------
pause

:: Menjalankan Predator V11 di jendela baru
start cmd /k "python predator_v11-1.py"

:: Menjalankan Supreme Radar di jendela baru
start cmd /k "python supreme_radar.py"

echo Bot sedang berjalan di jendela terpisah.
exit
