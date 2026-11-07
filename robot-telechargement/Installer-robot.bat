@echo off
rem Installe le robot de telechargement SPE (1 seule fois).
cd /d "%~dp0"
python -m pip install --upgrade playwright requests
rem Tache Windows : du lundi au samedi a 13:50
schtasks /Create /F /TN "SPE Robot telechargement" /SC WEEKLY /D MON,TUE,WED,THU,FRI,SAT /ST 13:50 /TR "\"%~dp0lancer-robot.bat\""
echo.
echo Robot installe. Test sans rien telecharger :
python wissem_robot.py --essai
pause
