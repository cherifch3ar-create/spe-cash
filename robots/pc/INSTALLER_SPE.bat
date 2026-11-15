@echo off
chcp 65001 >nul
title SPE - Installation et demarrage automatiques
echo.
echo  ============================================================
echo   SPE - Installation automatique du serveur et des robots
echo   Ne fermez pas cette fenetre. Rien a taper.
echo  ============================================================
echo.
set "URL1=https://raw.githubusercontent.com/cherifch3ar-create/spe-cash/main/robots/pc/installer_serveur_spe.ps1"
set "URL2=https://raw.githubusercontent.com/cherifch3ar-create/spe-cash/claude/keen-cannon-cw7c82/robots/pc/installer_serveur_spe.ps1"
set "PS1=%TEMP%\installer_spe.ps1"

echo  1/3  Telechargement de l'installateur...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { iwr '%URL2%' -OutFile '%PS1%' -UseBasicParsing -ErrorAction Stop } catch { iwr '%URL1%' -OutFile '%PS1%' -UseBasicParsing }"
if not exist "%PS1%" (
  echo  ERREUR : telechargement impossible. Verifiez Internet puis relancez ce fichier.
  pause & exit /b 1
)

echo  2/3  Installation des robots et des taches automatiques...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

echo.
echo  3/3  Demarrage du robot WhatsApp...
set "WA=%USERPROFILE%\Desktop\01_SPE\spe-cash\robots\whatsapp_web"
if not exist "%WA%\index.js" set "WA=C:\Users\USER\Desktop\01_SPE\spe-cash\robots\whatsapp_web"
if not exist "%WA%\index.js" (
  echo  Le dossier du robot WhatsApp est introuvable. Envoyez une photo de cette fenetre a Claude.
  pause & exit /b 1
)
where node >nul 2>nul || (
  echo  Node.js manque. Installez-le depuis https://nodejs.org ^(version LTS^), puis relancez ce fichier.
  start https://nodejs.org
  pause & exit /b 1
)
pushd "%WA%"
call npm.cmd install --omit=dev
start "Robot WhatsApp SPE - ne pas fermer" cmd /k "npm.cmd start"
popd

echo.
echo  ============================================================
echo   Termine. Une deuxieme fenetre "Robot WhatsApp SPE" est ouverte.
echo   La premiere fois : scannez le QR code qu'elle affiche avec le
echo   telephone du numero SPE (WhatsApp ^> Appareils connectes).
echo   Ensuite, ne fermez pas la fenetre du robot.
echo  ============================================================
echo.
pause
