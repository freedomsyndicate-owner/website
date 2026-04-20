@echo off
title DOMS SYSTEM LAUNCHER
color 0A

echo.
echo ============================================================
echo    FREEDOM SYNDICATE - DOMS SYSTEM LAUNCHER
echo ============================================================
echo.
echo  Memulai kedua bot...
echo.

timeout /t 2 /nobreak >nul

start "PREDATOR V11" cmd /k "color 0C && cd C:\DOMS_SYSTEM && python predator_v11.py"

timeout /t 3 /nobreak >nul

start "SUPREME RADAR" cmd /k "color 0B && cd C:\DOMS_SYSTEM && python supreme_radar.py"

echo  Kedua bot sudah berjalan!
echo  Jangan tutup window CMD yang terbuka.
echo.
pause