# ============================================================================
#  DÉMARRAGE SPE — lancé à chaque ouverture de session Windows (tâche « SPE Serveur - demarrage »).
#  Demande du directeur (15/11/2026) : « garantissez ça à chaque démarrage ou redémarrage du PC ».
#  Ne supprime rien, ne tape aucun mot de passe. Écrit le résultat dans le journal SPE (Supabase « events »).
# ============================================================================
$ErrorActionPreference = "Continue"
$Base   = "C:\Users\USER\Desktop\01_SPE"
$Shared = "$Base\SPE_shared"
$Log    = "$Shared\serveur_journal.txt"
$SB     = "https://djvygsbdwcoyldujrezq.supabase.co"
$CLE    = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
function Note($t) { $l = "{0}  {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm"), $t; Add-Content -Path $Log -Value $l -Encoding UTF8 }
$ok = @(); $besoin = @()
Start-Sleep -Seconds 60   # laisser Windows et le réseau démarrer

# 1. Chrome SPE des robots (port 9222 : TUNEPS, garde-session, cahiers des charges)
if (-not (Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue)) {
  if (Test-Path "$Shared\Lancer-Chrome-SPE.bat") { Start-Process "$Shared\Lancer-Chrome-SPE.bat" -WorkingDirectory $Shared; Start-Sleep 15 }
}
if (Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue) { $ok += "Chrome SPE ouvert" } else { $besoin += "Chrome SPE ne s'ouvre pas" }

# 2. Chrome habituel avec WhatsApp Web (session d'Amine) : rouvrir les onglets si Chrome n'est pas lancé
$chrome = @("C:\Program Files\Google\Chrome\Application\chrome.exe", "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
$principal = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -and $_.CommandLine -notmatch "ChromeSPE" }
if (-not $principal -and $chrome) { Start-Process $chrome -ArgumentList "--restore-last-session", "https://web.whatsapp.com"; Start-Sleep 10; $ok += "Chrome habituel rouvert (WhatsApp Web)" }
elseif ($principal) { $ok += "Chrome habituel déjà ouvert" }

# 3. Application Claude (les agents passent par elle pour le PC et Chrome)
$claude = @("$env:LOCALAPPDATA\AnthropicClaude\claude.exe", "$env:LOCALAPPDATA\Programs\Claude\Claude.exe", "$env:LOCALAPPDATA\Claude\Claude.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not (Get-Process -Name "claude" -ErrorAction SilentlyContinue)) {
  if ($claude) { Start-Process $claude; Start-Sleep 10; $ok += "application Claude lancée" } else { $besoin += "application Claude introuvable : l'ouvrir à la main" }
} else { $ok += "application Claude ouverte" }

# 4. Robot WhatsApp Web (s'il a été connecté un jour) et tâches SPE présentes
$taches = Get-ScheduledTask -TaskName "SPE *" -ErrorAction SilentlyContinue
$ok += "$($taches.Count) tâches SPE planifiées"
if (Test-Path "$Base\spe-cash\robots\whatsapp_web\.wwebjs_auth") {
  if (-not (Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match "index.js" })) {
    Start-ScheduledTask -TaskName "SPE Robot WhatsApp Web" -ErrorAction SilentlyContinue; $ok += "robot WhatsApp Web relancé"
  }
}

# 5. Mise à jour du dépôt (robots à jour)
if (Get-Command git -ErrorAction SilentlyContinue) { git -C "$Base\spe-cash" pull -q 2>$null; $ok += "robots à jour" }

# 6. Journal
$texte = "Démarrage PC : " + ($ok -join ", ") + $(if ($besoin.Count) { ". BESOIN : " + ($besoin -join " ; ") } else { ". Tout est prêt." })
Note $texte
try {
  $t = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  $corps = @{ collection = "events"; id = "e-$t-demarrage"; maj = $t; source = "demarrage_pc"; data = @{ t = $t; agent = "demarrage"; texte = $texte } } | ConvertTo-Json -Depth 4
  Invoke-RestMethod -Method Post -Uri "$SB/rest/v1/docs" -Headers @{ apikey = $CLE; Authorization = "Bearer $CLE"; Prefer = "return=minimal" } -ContentType "application/json; charset=utf-8" -Body ([Text.Encoding]::UTF8.GetBytes($corps)) | Out-Null
} catch { Note "Journal en ligne impossible : $($_.Exception.Message)" }
