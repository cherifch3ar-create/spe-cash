# 07 — Le PC du bureau = serveur local SPE (décision du directeur, 14/11/2026)

« Je ne veux pas en parler tous les jours. Le PC est ouvert, tous les agents et tous les robots sont ouverts :
c'est un serveur local pour l'application, le logiciel, les appels d'offres et tout ce qui est nécessaire à la société. »

## Ce que ça change
- La « machine toujours allumée » du plan 02 **est le PC du bureau**, pas un serveur loué. Pas de compte Oracle.
- Tout ce qui demande Chrome, WhatsApp ou TUNEPS connecté tourne sur ce PC ; ce qui n'en a pas besoin reste sur
  GitHub Actions (veille, pièces en ligne, affiches, Telegram, superviseur) : double sécurité si le PC redémarre.
- Les agents Claude continuent de tourner dans le cloud sur leur planning 24 h, et pilotent le Chrome du PC.

## Installation : un seul script, une seule fois
`robots/pc/installer_serveur_spe.ps1` (clic droit → Exécuter avec PowerShell, en administrateur) :
1. PC jamais en veille ni en hibernation (l'écran peut s'éteindre).
2. Chrome SPE (profil séparé « SPE Robots », port 9222) s'ouvre tout seul à chaque démarrage : plus jamais de « BESOIN — Chrome n'est pas ouvert ».
3. Tâches planifiées Windows : robot des pièces (chaque heure), garde-session TUNEPS (10 min), superviseur local (chaque heure), robot WhatsApp Web (en continu, redémarre seul), mise à jour du dépôt chaque nuit.
4. Journal lisible : `01_SPE\SPE_shared\serveur_journal.txt`.
Prérequis à installer une fois s'ils manquent : Git for Windows, Python 3 (« Add to PATH »), Node.js LTS.
Puis, une seule fois : `npm start` dans `robots\whatsapp_web` pour scanner le QR avec le numéro dédié SPE.

## Les gestes humains qui restent (et seulement ceux-là)
| Quand | Geste | Pourquoi aucun robot ne peut le faire |
|---|---|---|
| Une fois par jour, heure fixe | Code TnTrust si TUNEPS le demande | Clé personnelle, interdit aux robots |
| Matin et après-midi | Valider les affiches et les décisions dans le Centre d'approbation ; répondre OUI/NON | Décision du directeur |
| Au redémarrage du PC (rare) | Se connecter à la session Windows | Les tâches « à l'ouverture de session » démarrent alors toutes seules |
| Si WhatsApp se déconnecte | Rescanner le QR | Sécurité WhatsApp |
Tout le reste est écrit dans `events` et visible dans l'application (Diagnostic) ; le superviseur signale ce qui est en retard.

## Sécurité du serveur local
Un seul profil Chrome pour les robots, jamais celui du directeur ; aucun mot de passe dans les scripts ; le PC ne sert
que SPE ; sauvegarde quotidienne de `01_SPE` (zip daté) à ajouter dans `_SAUVEGARDES` (Nabil, gardien des sauvegardes).

## Constat du 14/11 (15:20 Tunis) : GitHub Actions n'est pas ponctuel
Les horaires GitHub (« schedule ») sont retardés ou sautés quand le dépôt est peu actif : la veille Google est passée à
01:28, 10:37 puis plus rien jusqu'à 14:20 au lieu de toutes les 3 h ; les nouveaux robots (affiches, superviseur,
Telegram, pièces en ligne) n'ont eu aucun passage automatique dans les 3 heures qui ont suivi leur fusion. Les
lancements manuels, eux, marchent à chaque fois. Conséquence : **le serveur local (PC) est la voie principale** pour
tous les robots, y compris ceux « en ligne » ; GitHub reste la roue de secours. Le script d'installation installe donc
aussi les robots affiches, pièces en ligne et veille Google en tâches Windows (double passage sans risque : chaque robot
ignore ce qui est déjà fait).
