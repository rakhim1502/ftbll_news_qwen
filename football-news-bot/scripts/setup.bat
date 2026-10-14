@echo off
REM ============================================================
REM  Football News Bot - Windows o'rnatish skripti
REM  Ishga tushirish: scripts\setup.bat (loyiha ildizidan)
REM ============================================================
setlocal

cd /d "%~dp0.."

echo [1/4] Python tekshirilmoqda...
python --version >nul 2>&1
if errorlevel 1 (
    echo XATO: Python topilmadi. python.org saytidan 3.11+ versiyasini
    echo       "Add Python to PATH" belgisini tanlab o'rnating va qayta urining.
    exit /b 1
)

echo [2/4] Virtual muhit (.venv) yaratilmoqda...
if not exist .venv (
    python -m venv .venv
    if errorlevel 1 (
        echo XATO: venv yaratib bo'lmadi.
        exit /b 1
    )
)

echo [3/4] Kutubxonalar o'rnatilmoqda (requirements.lock.txt)...
".venv\Scripts\python.exe" -m pip install --upgrade pip >nul
".venv\Scripts\python.exe" -m pip install -r requirements.lock.txt
if errorlevel 1 (
    echo XATO: kutubxonalarni o'rnatib bo'lmadi.
    exit /b 1
)

echo [4/4] .env fayli tayyorlanmoqda...
if not exist .env (
    copy .env.example .env >nul
    echo IZOH: .env.example'dan .env nusxa olindi.
    echo       BOT_TOKEN qiymatini @BotFather'dan olingan token bilan almashtiring!
) else (
    echo IZOH: .env allaqachon mavjud, o'zgartirilmadi.
)

echo.
echo ============================================================
echo O'rnatish tugadi. Botni ishga tushirish uchun:
echo     scripts\run.bat
echo Testlarni ishga tushirish uchun:
echo     scripts\test.bat
echo ============================================================
endlocal
