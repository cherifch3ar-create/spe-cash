# SPACE WORK — l'espace de travail des robots et des agents SPE

Dossier créé le 14/11/2026 à la demande du directeur (« si quelque chose n'existe pas, crée ce dossier »).
Il n'existait aucun dépôt ni dossier nommé SPACE WORK : celui-ci devient l'endroit unique où l'on décrit
**qui travaille, quand, avec quoi, et ce que ça consomme** — pour que tout tourne PC éteint et sans
épuiser la limite d'usage Claude.

| Fichier | Contenu |
|---|---|
| `01_ETAT_REEL_2026-11-14.md` | Ce que la base Supabase montre vraiment (lu en lecture seule par le connecteur Supabase, le 14/11 à 09:50). Remplace les « non vérifié » de l'audit. |
| `02_REPONSE_WHATSAPP_SANS_PC.md` | La réponse à la question « comment WhatsApp, les affiches, les agents et leurs contrôleurs tournent sans arrêt, sans PC et sans consommer ». |
| `03_CONNECTEURS_A_DONNER.md` | Les connecteurs et MCP gratuits à donner à Claude, et ce que chacun débloque. |
| `04_ARCHITECTURE_CIBLE.md` | Qui fait quoi : robots (gratuits), superviseur, agents IA (payants, courts), table `agent_tasks`. |
| `supabase/agent_tasks.sql` | La table des tâches d'agents (à appliquer seulement après votre OK). |

Règles du dossier : rien ici ne remplace un projet existant (Workspace, SPE Live, robots) ; on y écrit
les décisions et les plans, et les robots nouveaux vont dans `robots/` du dépôt après accord.

| `../robots/affiches.py` (+ workflow `robot-affiches.yml`) | Robot affiches : une affiche en brouillon par offre active, toutes les heures. |
| `../robots/superviseur.py` (+ `robot-superviseur.yml`) | Robot superviseur : santé des robots + relance des `agent_tasks`, toutes les heures. |
| `../robots/telegram_file.py` (+ `robot-telegram.yml`) | Canal de secours Telegram (officiel, gratuit) : actif dès que le secret `TELEGRAM_BOT_TOKEN` existe et que `telegram_groupes.json` est rempli. |
| `../robots/whatsapp_web/` | Robot WhatsApp Web pour une machine toujours allumée (numéro dédié) : `install.sh`, `index.js`, `config.json`. Non testé depuis le cloud. |
