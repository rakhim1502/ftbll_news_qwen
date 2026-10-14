@echo off
REM ============================================================
REM  Football News Bot - testlarni ishga tushirish (Windows)
REM ============================================================
setlocal

cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo XATO: .venv topilmadi. Avval "scripts\setup.bat" ni ishga tushiring.
    exit /b 1
)

".venv\Scripts\python.exe" -m pytest -q

endlocal
