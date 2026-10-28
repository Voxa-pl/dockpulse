@echo off
title RampaRandevu - Yard and Dock Management System
chcp 65001 >nul
cls

echo =======================================================
echo    RAMPARANDEVU - AKILLI RAMPA VE SAHA YÖNETİM SİSTEMİ
echo    Gebze DC-01 - Port: 8080
echo =======================================================
echo.
echo Sunucu başlatılıyor...
echo.

cd /d "%~dp0backend"
set PYTHONPATH=%~dp0backend

start "" "http://127.0.0.1:8080"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080 --reload
pause
