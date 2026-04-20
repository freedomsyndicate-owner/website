@echo off
:: Berpindah ke folder sistem agar path sesuai
cd /d "C:\DOMS_SYSTEM"

title Freedom Syndicate - Global Runner
echo ---------------------------------------------------
echo Memulai Global Predator V11 dan Supreme Radar V1...
echo Status: IP Stealth via Tor Browser Aktif
echo ---------------------------------------------------
pause

:: Menjalankan Predator V11 (pastikan nama file sesuai foto)
start "Predator Engine" cmd /k "python predator_v11-1.py"

:: Menjalankan Supreme Radar (pastikan nama file sesuai foto)
start "Supreme Radar" cmd /k "python supreme_radar.py"

echo.
echo Kedua bot sedang berjalan. JANGAN tutup jendela ini.
exit
