@echo off
chcp 65001 >nul
rem GuildByMorricette (GBM) Manager : fabrique GBM_Manager.exe (dossier dist) avec PyInstaller.
rem Il faut Python 3 pour Windows (python.org, case "Add python.exe to PATH" cochee a l'installation).
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py
%PY% --version || (echo Python introuvable : installez-le depuis https://www.python.org/downloads/ & pause & exit /b 1)
%PY% -m pip install --upgrade pyinstaller || (echo Installation de PyInstaller impossible. & pause & exit /b 1)
%PY% -m PyInstaller --noconfirm --onefile --noconsole --name GBM_Manager --icon icone.ico --add-data "icone.ico;." GBM_Manager.py || (echo La fabrication a echoue. & pause & exit /b 1)
echo.
echo Termine : le programme est dist\GBM_Manager.exe
pause
