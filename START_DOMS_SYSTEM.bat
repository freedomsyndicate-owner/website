@echo off
title DOMS SYSTEM LAUNCHER
color 0A

echo.
echo ============================================================
echo    FREEDOM SYNDICATE — DOMS SYSTEM LAUNCHER
echo ============================================================
echo.
echo  [1] Memulai PREDATOR V11 (ICT Signal + SL/TP)
echo  [2] Memulai SUPREME RADAR (Fundamental Alarm)
echo  [3] Kedua Bot berjalan bersamaan...
echo ============================================================
echo.

:: ── Jalankan Predator V11 di window terpisah ──────────────────────
start "🦅 PREDATOR V11" cmd /k "cd /d C:\DOMS_SYSTEM && color 0C && echo. && echo ============================================================ && echo    PREDATOR V11 — ICT SUPREME ENGINE && echo ============================================================ && echo. && python predator_v11.py"

:: Jeda 3 detik sebelum buka window kedua
timeout /t 3 /nobreak >nul

:: ── Jalankan Supreme Radar di window terpisah ─────────────────────
start "📡 SUPREME RADAR" cmd /k "cd /d C:\DOMS_SYSTEM && color 0B && echo. && echo ============================================================ && echo    SUPREME RADAR V1 — FUNDAMENTAL + SYNDICATE && echo ============================================================ && echo. && python supreme_radar.py"

echo.
echo  ✅ Kedua bot sudah berjalan di window masing-masing!
echo  ✅ Jangan tutup window CMD yang terbuka.
echo.
echo  Tekan tombol apapun untuk menutup launcher ini...
pause >nul
