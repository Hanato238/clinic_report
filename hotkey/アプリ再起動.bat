@echo off
taskkill /IM vectra.exe /F

python "C:\Users\admin\workspace\clinic_report\init_setter\autosetting.py"

timeout /t 2 /nobreak >nul

start "" "C:\Vectra\bin\vectra.exe"

pause
