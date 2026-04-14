@echo off
:: SET BACKGROUND HITAM (0) TEKS PUTIH (7)
color 07
title FREEDOM SYNDICATE - PONOROGO ENGINE
cls

echo.
:: BAGIAN INI WARNA BIRU (Pake teknik PowerShell biar teks tertentu aja yang biru)
powershell -Command "Write-Host '  _______  _______  _______  _______  ______   _______ ' -ForegroundColor Cyan"
powershell -Command "Write-Host ' (  ____ \(  ____ \(  ____ \(  ____ \(  __  \ (  ___  )' -ForegroundColor Cyan"
powershell -Command "Write-Host ' | (    \/| (    \/| (    \/| (    \/| (  \  )| (   ) |' -ForegroundColor Cyan"
powershell -Command "Write-Host ' | (__    | (__    | (__    | (__    | |   ) || |   | |' -ForegroundColor Cyan"
powershell -Command "Write-Host ' |  __)   |  __)   |  __)   |  __)   | |   | || |   | |' -ForegroundColor Cyan"
powershell -Command "Write-Host ' | (      | (      | (      | (      | |   ) || |   | |' -ForegroundColor Cyan"
powershell -Command "Write-Host ' | )      | )      | )      | )      | (__/  )| (___) |' -ForegroundColor Cyan"
powershell -Command "Write-Host ' |/       |/       |/       |/       |______/ (_______)' -ForegroundColor Cyan"

echo.
echo  ============================================================
echo      [ SYSTEM POWERED BY FREEDOM SYNDICATE V10 ]
echo  ============================================================
echo.
echo   [+] STATUS   : SYSTEM ONLINE
echo   [+] LEADER   : DOMS (THE GODFATHER)
echo   [+] LOCATION : PONOROGO, INDONESIA
echo.
echo  ------------------------------------------------------------
echo   [!] MENGAKTIFKAN DUAL-RADAR (PREDATOR + OMNISCIENCE)...
echo  ------------------------------------------------------------
echo.

:: EKSEKUSI BOT (Pastikan di folder C:\DOMS_SYSTEM)
cd /d "C:\DOMS_SYSTEM"

echo  [!] Booting Predator Engine...
start "DOMS_PREDATOR" py bot_predator.py

echo  [!] Booting Fundamental Intel...
start "DOMS_INTEL" py bot_fundametal.py

echo.
echo  ============================================================
echo   SUCCESS! Bot sudah jalan di jendela terpisah.
echo   Happy Hunting, Leader!
echo  ============================================================
pause
