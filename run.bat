@echo off
chcp 65001 > nul
title Keldi-Ketdi Telegram Boti
color 0A

echo ============================================================
echo      DO'KON KELDI-KETDI TELEGRAM BOT VA WEBAPP TIZIMI
echo ============================================================
echo.

:: Try py launcher first, fallback to python
where py >nul 2>nul
if %errorlevel% equ 0 (
    set PY_CMD=py
) else (
    set PY_CMD=python
)

echo [*] Python orqali bot ishga tushirilmoqda (%PY_CMD%)...
echo [*] Bot to'xtatish uchun: Ctrl + C bosing
echo.

%PY_CMD% main.py

if %errorlevel% neq 0 (
    echo.
    echo [XATO] Bot ishga tushmadi. Iltimos, quyidagi xabarni o'qing:
)

pause
