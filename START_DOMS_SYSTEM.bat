@echo off
title DOMS SYSTEM LAUNCHER
color 0A

echo.
echo ============================================================
echo    FREEDOM SYNDICATE - DOMS SYSTEM LAUNCHER
echo ============================================================
echo.
[span_2](start_span)echo  Memulai kedua bot...[span_2](end_span)
echo.

timeout /t 2 /nobreak >nul

:: Menjalankan Predator V11
start "PREDATOR V11" cmd /k "color 0C && cd /d C:\DOMS_SYSTEM && python predator_v11.py"

timeout /t 3 /nobreak >nul

:: Menjalankan Supreme Radar
start "SUPREME RADAR" cmd /k "color 0B && cd /d C:\DOMS_SYSTEM && python supreme_radar.py"

echo  Kedua bot sudah berjalan!
[span_3](start_span)echo  Jangan tutup window CMD yang terbuka.[span_3](end_span)
echo.
pause
