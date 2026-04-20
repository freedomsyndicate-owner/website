@echo off
:: Berpindah ke folder tempat file berada agar tidak error path
cd /d "%~dp0"

title Freedom Syndicate - System Runner
echo ---------------------------------------------------
echo Memulai Global Predator V11 dan Supreme Radar V1...
echo Pastikan TOR BROWSER sudah terbuka!
echo ---------------------------------------------------
pause

:: Menjalankan Predator V11 di jendela baru
:: Gunakan tanda kutip agar aman jika ada spasi
start "Predator Engine" cmd /k "python predator_v11-1.py"

:: Menjalankan Supreme Radar di jendela baru
start "Supreme Radar" cmd /k "python supreme_radar.py"

echo.
echo Bot sedang berjalan di jendela terpisah.
echo Jangan tutup jendela ini sebelum bot selesai.
exit
