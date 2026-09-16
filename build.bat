@echo off
REM ============================================================
REM  Compile ClipDL en un seul fichier dist\ClipDL.exe
REM  A relancer quand YouTube casse : ca met yt-dlp a jour.
REM ============================================================
cd /d "%~dp0"

if not exist .venv (
    echo [1/3] Creation de l'environnement virtuel...
    py -3 -m venv .venv || goto :err
)

echo [2/3] Installation / mise a jour des dependances...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
python -m pip install --upgrade -r requirements.txt || goto :err

echo [3/3] Compilation de l'exe...
pyinstaller --noconfirm --onefile --name ClipDL ^
  --add-data "templates;templates" ^
  --collect-all yt_dlp ^
  --collect-all yt_dlp_ejs ^
  --collect-data imageio_ffmpeg ^
  app.py || goto :err

echo.
echo  OK : dist\ClipDL.exe est pret.
pause
exit /b 0

:err
echo.
echo  ECHEC de la compilation (voir le message ci-dessus).
pause
exit /b 1
