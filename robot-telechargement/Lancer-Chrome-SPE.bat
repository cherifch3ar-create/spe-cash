@echo off
rem Ouvre le Chrome du robot (profil separe, exige par Chrome pour la porte 9222).
rem La premiere fois : le directeur se connecte lui-meme a TUNEPS dans cette fenetre, puis la laisse ouverte.
set CHROME="C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist %CHROME% set CHROME="C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
start "" %CHROME% --remote-debugging-port=9222 --user-data-dir="C:\Users\USER\Desktop\01_SPE\Chrome_robot" https://www.tuneps.tn/
