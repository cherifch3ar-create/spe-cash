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
# NB : ne jamais appeler un paramètre « $args » (variable réservée de PowerShell : la tâche n'était pas créée, 15/11/2026).
# Administrateur ? Sinon les tâches sont créées pour l'utilisateur courant (niveau normal) : elles marchent pareil
# pour les robots SPE (« Accès refusé » observé le 15/11/2026 dans une fenêtre non administrateur).
$EstAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$Niveau = if ($EstAdmin) { "Highest" } else { "Limited" }
Note "Mode : $(if ($EstAdmin) { 'administrateur' } else { 'utilisateur (sans administrateur)' })"
function Tache([string]$nom, [string]$action, [string]$arguments, $declencheur) {
  try {
    $a = New-ScheduledTaskAction -Execute $action -Argument $arguments -WorkingDirectory $Shared -ErrorAction Stop
    $s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
    Register-ScheduledTask -TaskName $nom -Action $a -Trigger $declencheur -Settings $s -RunLevel $Niveau -Force -ErrorAction Stop | Out-Null
    Note "Tâche planifiée installée : $nom"
  } catch { Note "ERREUR tâche « $nom » : $($_.Exception.Message)" }
}
$user = "$env:USERDOMAIN\$env:USERNAME"
Tache "SPE Serveur - Chrome SPE au demarrage" "cmd.exe" "/c `"$ChromeBat`"" (New-ScheduledTaskTrigger -AtLogOn -User $user)
# Vérification complète à chaque ouverture de session (Chrome SPE, Chrome WhatsApp, application Claude, robots, journal).
Tache "SPE Serveur - demarrage" "powershell.exe" "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Repo\robots\pc\demarrage_spe.ps1`"" (New-ScheduledTaskTrigger -AtLogOn -User $user)
# Raccourci sur le Bureau + ouverture tout de suite si Chrome SPE (port 9222) n'est pas déjà ouvert
# (sinon les robots TUNEPS attendent le prochain redémarrage : constaté le 15/11/2026).
try {
  $lnk = (New-Object -ComObject WScript.Shell).CreateShortcut("$env:USERPROFILE\Desktop\Chrome TUNEPS SPE.lnk")
  $lnk.TargetPath = $ChromeBat; $lnk.WorkingDirectory = $Shared; $lnk.Save()
  Note "Raccourci « Chrome TUNEPS SPE » créé sur le Bureau."
} catch { Note "Raccourci Bureau impossible : $($_.Exception.Message)" }
$port = Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue
if (-not $port) { Start-Process -FilePath $ChromeBat -WorkingDirectory $Shared; Note "Chrome SPE ouvert (TUNEPS + WhatsApp Web)." }
else { Note "Chrome SPE déjà ouvert." }

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
  # Les robots en ligne tournent AUSSI ici : GitHub Actions retarde ou saute souvent les horaires (observé le 14/11 : veille toutes les 8 h au lieu de 3 h).
  $t2 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(41) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
  # Les affiches sont aussi gardées sur le PC (SPE_shared\affiches) : le pont WhatsApp les prend là, sans repasser par Internet.
  Tache "SPE Robot affiches local" $py "`"$Repo\robots\affiches.py`" --max 10 --sortie `"$Shared\affiches`"" $t2
  $t3 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(23) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
  Tache "SPE Robot pieces en ligne local" $py "`"$Repo\robot-telechargement\robot_en_ligne.py`" --max 40" $t3
  $t4 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(17) -RepetitionInterval (New-TimeSpan -Hours 3) -RepetitionDuration (New-TimeSpan -Days 3650)
  Tache "SPE Robot veille Google local" $py "`"$Repo\robots\veille_google.py`"" $t4
  # Pont file Supabase -> outbox du robot WhatsApp du PC (les agents lisent l'ancienne base, pleine : sans ce pont rien ne part).
  $t5 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(3) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)
  # Chemin unique (15/11/2026) : file Supabase -> robot WhatsApp Web (Node). Le pont vers l'ancienne outbox ne sert
  # que si Node est absent ; sinon il marquerait « envoyé » des messages que le robot WhatsApp Web n'aurait pas vus.
  if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Tache "SPE Robot pont WhatsApp" $py "`"$Repo\robots\pc\file_vers_outbox.py`"" $t5
  } else {
    Unregister-ScheduledTask -TaskName "SPE Robot pont WhatsApp" -Confirm:$false -ErrorAction SilentlyContinue
    Note "Pont outbox non installé : le robot WhatsApp Web envoie directement la file Supabase."
  }
  # Archivage (Option A du directeur, 15/11/2026) : le PC garde tous les fichiers, Supabase reste sous 800 Mo.
  # Nécessite la variable d'environnement SUPABASE_SERVICE_KEY (sinon le robot s'arrête sans rien toucher).
  $t6 = New-ScheduledTaskTrigger -Once -At (Get-Date).Date.AddMinutes(51) -RepetitionInterval (New-TimeSpan -Hours 2) -RepetitionDuration (New-TimeSpan -Days 3650)
  Tache "SPE Robot archivage PC" $py "`"$Repo\robots\pc\archiver_stockage.py`"" $t6
  if (-not $env:SUPABASE_SERVICE_KEY -and -not [Environment]::GetEnvironmentVariable("SUPABASE_SERVICE_KEY", "User")) {
    Note "A FAIRE : définir SUPABASE_SERVICE_KEY (Supabase > Project Settings > API > service_role) pour activer l'archivage."
  }
} else { Note "ATTENTION : Python absent. L'installer puis relancer ce script." }

# 5. Robot WhatsApp Web (Node.js requis : https://nodejs.org LTS). Tourne en continu, redémarre tout seul.
$node = (Get-Command node -ErrorAction SilentlyContinue).Source
if ($node) {
  Push-Location "$Repo\robots\whatsapp_web"; npm.cmd install --omit=dev --silent 2>$null; Pop-Location
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
  Note "Premier lancement à la main pour scanner le QR (numéro dédié SPE) : cd $Repo\robots\whatsapp_web ; npm.cmd start"
} else { Note "Node.js absent : le robot WhatsApp Web n'est pas installé (installer Node LTS puis relancer)." }

# 6. Mise à jour automatique du dépôt chaque nuit à 03:40.
if (Get-Command git -ErrorAction SilentlyContinue) {
  Tache "SPE Serveur - mise a jour du depot" "git.exe" "-C `"$Repo`" pull -q" (New-ScheduledTaskTrigger -Daily -At 03:40)
}
Note "=== Installation terminée. Redémarrer le PC une fois, puis vérifier dans l'application (Diagnostic) que les robots écrivent. ==="
