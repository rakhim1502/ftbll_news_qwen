@echo off
REM ============================================================
REM  Football News Bot - ishga tushirish skripti (Windows)
REM  Avval scripts\setup.bat bir marta bajarilgan bo'lishi kerak.
REM  To'xtatish: Ctrl+C
REM ============================================================
setlocal

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo XATO: .venv topilmadi. Avval "scripts\setup.bat" ni ishga tushiring.
    exit /b 1
)

if not exist .env (
    echo XATO: .env fayli topilmadi. ".env.example" ni ".env" ga nusxalang
    echo       va BOT_TOKEN ni kiriting.
    exit /b 1
)

echo Bot ishga tushmoqda... (to'xtatish uchun Ctrl+C)
".venv\Scripts\python.exe" -m app.main

endlocal
