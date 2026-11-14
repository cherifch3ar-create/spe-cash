# ============================================================================
#  SERVEUR LOCAL SPE — installation en une fois sur le PC du bureau (Windows 10/11)
#  Clic droit > Exécuter avec PowerShell (en administrateur). Relançable sans risque : ne supprime rien.
#  Ce que ça fait : 1) le PC ne dort jamais ; 2) Chrome SPE s'ouvre tout seul à chaque démarrage ;
#  3) les robots du PC (pièces TUNEPS, garde-session, WhatsApp Web, superviseur local) tournent en tâches
#  planifiées Windows 24 h/24 ; 4) un journal lisible dans 01_SPE\SPE_shared\serveur_journal.txt.
# ============================================================================
$ErrorActionPreference = "Continue"
$Base   = "C:\Users\USER\Desktop\01_SPE"
$Shared = "$Base\SPE_shared"
$Repo   = "$Base\spe-cash"
$Log    = "$Shared\serveur_journal.txt"
function Note($t) { $l = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm"), $t; Write-Host $l; Add-Content -Path $Log -Value $l -Encoding UTF8 }
New-Item -ItemType Directory -Force -Path $Shared | Out-Null
Note "=== Installation serveur local SPE ==="

# 1. Jamais en veille (secteur et batterie), écran peut s'éteindre, disque jamais.
powercfg /change standby-timeout-ac 0; powercfg /change standby-timeout-dc 0
powercfg /change hibernate-timeout-ac 0; powercfg /change hibernate-timeout-dc 0
powercfg /change disk-timeout-ac 0; powercfg /change monitor-timeout-ac 20
powercfg /hibernate off | Out-Null
Note "Veille et hibernation désactivées."

# 2. Dépôt spe-cash à jour sur le PC (robots + application).
if (Get-Command git -ErrorAction SilentlyContinue) {
  if (Test-Path "$Repo\.git") { git -C $Repo pull -q; Note "Dépôt spe-cash mis à jour." }
  else { git clone -q https://github.com/cherifch3ar-create/spe-cash.git $Repo; Note "Dépôt spe-cash cloné dans $Repo." }
} else { Note "ATTENTION : git absent. Installer Git for Windows (https://git-scm.com) puis relancer." }

# 3. Chrome SPE au démarrage (profil « SPE Robots », port 9222 pour le robot des pièces).
$ChromeBat = "$Shared\Lancer-Chrome-SPE.bat"
if (-not (Test-Path $ChromeBat)) {
  $chrome = @("C:\Program Files\Google\Chrome\Application\chrome.exe", "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
  @"
@echo off
rem Chrome dédié aux robots et agents SPE (profil séparé, jamais fermé par les agents)
start "" "$chrome" --remote-debugging-port=9222 --user-data-dir="$Shared\ChromeSPE" --no-first-run --restore-last-session https://www.tuneps.tn/portail/offres https://web.whatsapp.com
"@ | Set-Content -Path $ChromeBat -Encoding ASCII
  Note "Lancer-Chrome-SPE.bat créé (profil SPE Robots dans $Shared\ChromeSPE)."
}
function Tache($nom, $action, $args, $declencheur) {
  $a = New-ScheduledTaskAction -Execute $action -Argument $args -WorkingDirectory $Shared
  $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
  Register-ScheduledTask -TaskName $nom -Action $a -Trigger $declencheur -Settings $s -RunLevel Highest -Force | Out-Null
  Note "Tâche planifiée installée : $nom"
}
$user = "$env:USERDOMAIN\$env:USERNAME"
Tache "SPE Serveur - Chrome SPE au demarrage" "cmd.exe" "/c `"$ChromeBat`"" (New-ScheduledTaskTrigger -AtLogOn -User $user)

# 4. Robots du PC en tâches planifiées (Python requis : https://www.python.org, cocher « Add to PATH »).
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($py) {
  pip install -q requests playwright pillow 2>$null
  if (Test-Path "$Repo\robot-telechargement\wissem_robot.py") {
    $t = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
    Tache "SPE Robot telechargement" $py "`"$Repo\robot-telechargement\wissem_robot.py`"" $t
    $t10 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
    Tache "SPE Robot garde-session TUNEPS" $py "`"$Repo\robot-telechargement\wissem_robot.py`" --garder-session" $t10
  }
  $t1 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(27) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
  Tache "SPE Robot superviseur local" $py "`"$Repo\robots\superviseur.py`"" $t1
} else { Note "ATTENTION : Python absent. L'installer puis relancer ce script." }

# 5. Robot WhatsApp Web (Node.js requis : https://nodejs.org LTS). Tourne en continu, redémarre tout seul.
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if ($node) {
  Push-Location "$Repo\robots\whatsapp_web"; npm install --omit=dev --silent 2>$null; Pop-Location
  $wa = "$Shared\Lancer-WhatsApp-Robot.bat"
  @"
@echo off
:boucle
cd /d "$Repo\robots\whatsapp_web"
"$node" index.js >> "$Shared\whatsapp_robot_journal.txt" 2>&1
timeout /t 30 >nul
goto boucle
"@ | Set-Content -Path $wa -Encoding ASCII
  Tache "SPE Robot WhatsApp Web" "cmd.exe" "/c `"$wa`"" (New-ScheduledTaskTrigger -AtLogOn -User $user)
  Note "Premier lancement à la main pour scanner le QR (numéro dédié SPE) : cd $Repo\robots\whatsapp_web && npm start"
} else { Note "Node.js absent : le robot WhatsApp Web n'est pas installé (installer Node LTS puis relancer)." }

# 6. Mise à jour automatique du dépôt chaque nuit à 03:40.
if (Get-Command git -ErrorAction SilentlyContinue) {
  Tache "SPE Serveur - mise a jour du depot" "git.exe" "-C `"$Repo`" pull -q" (New-ScheduledTaskTrigger -Daily -At 03:40)
}
Note "=== Installation terminée. Redémarrer le PC une fois, puis vérifier dans l'application (Diagnostic) que les robots écrivent. ==="
