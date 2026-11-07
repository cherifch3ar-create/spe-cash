@echo off
rem Installe le robot de telechargement SPE (1 seule fois).
cd /d "%~dp0"
python -m pip install --upgrade playwright requests
rem Tache Windows : toutes les heures, 24 h sur 24, 7 jours sur 7
schtasks /Create /F /TN "SPE Robot telechargement" /SC HOURLY /MO 1 /ST 00:05 /TR "\"%~dp0lancer-robot.bat\""
schtasks /Create /F /TN "SPE Robot garde-session TUNEPS" /SC MINUTE /MO 10 /TR "\"%~dp0lancer-robot.bat\" --garder-session"
echo.
echo Robot installe. Test sans rien telecharger :
python wissem_robot.py --essai
pause
