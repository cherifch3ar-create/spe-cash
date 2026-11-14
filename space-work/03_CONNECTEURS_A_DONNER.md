# 03 — Les connecteurs et MCP gratuits à donner à Claude (et ce que chacun débloque)

Tout ce qui suit est gratuit. « Déjà donné » = vérifié le 14/11/2026 dans cette session.

| Connecteur / accès | État | Ce que ça débloque | Comment le donner |
|---|---|---|---|
| **Supabase (MCP)** | **Déjà donné et il marche** : j'ai lu toute la base en lecture seule ce matin | Audit réel, superviseur, contrôle des files, règles RLS, création de `agent_tasks` | Rien à faire. Il reste à dire si j'ai le droit d'ÉCRIRE (migrations) : par défaut je ne fais que lire |
| **Réseau du cloud → hôte `djvygsbdwcoyldujrezq.supabase.co`** | **Refusé** (CONNECT 403) : les scripts Python des robots ne peuvent pas être testés d'ici, et l'agent Ines a écrit « BLOQUÉ » pour cette raison le 07/11 | Tester les robots avant de les publier ; les tâches planifiées cloud (Ménage, Khalil) peuvent écrire dans la base | Une demande d'autorisation vous est envoyée par cette session (environnement « Asfour Stah 3D ») : accepter. Aussi possible dans claude.ai → Paramètres → Code → Environnements → hôtes autorisés |
| **Réseau → `www.tuneps.tn`** | Non autorisé dans cet environnement | Tester le relevé et le robot en ligne d'ici | Même demande d'autorisation |
| **GitHub (MCP + dépôt spe-cash)** | Déjà donné | Robots GitHub Actions (gratuit : illimité sur dépôt public, 2 000 min/mois sur dépôt privé), PR, fusion | Rien à faire |
| **Gmail** | Déjà connecté | Lire les alertes TUNEPS/e-mails d'acheteurs ; envoyer seulement avec votre accord | Rien à faire |
| **Google Drive / Sheets / Agenda** | Déjà connectés (plugin) | Tableau des offres partagé, planning des visites, archives | Rien à faire |
| **Canva** | Connecté, mais quota d'images IA épuisé | Affiches « jolies » à la main | Pas nécessaire : le robot affiches utilise vos 22 images métier |
| **Telegram Bot** (gratuit, officiel) | À créer | Publication texte + image + PDF dans des groupes/chaînes, sans PC, sans risque | Sur votre téléphone : ouvrir `@BotFather`, taper `/newbot`, copier le jeton ; me le donner par le formulaire sécurisé « request_credential » (jamais dans la conversation) ; ajouter le bot comme admin des groupes |
| **Facebook Page (Graph API, officiel, gratuit)** | À créer | L'agent Facebook (Youssef) devient un robot : publication automatique des affiches sur la page SPE, 0 crédit Claude | Meta for Developers → créer une app → jeton de page longue durée ; me le donner par le formulaire sécurisé |
| **WhatsApp Cloud API (Meta)** | Facultatif | Envois 1 à 1 officiels aux clients abonnés (pas de groupes) | Meta Business → WhatsApp → numéro dédié ; jeton par formulaire sécurisé |
| **Machine toujours allumée** (Oracle Always Free ou mini-PC au bureau) | À créer | Le robot WhatsApp Web (groupes) et la session TUNEPS/Chrome sans le PC du bureau | Oracle : créer le compte gratuit ; je prépare le script d'installation. Mini-PC : me dire quand il est branché |
| **PC du bureau via Remote Control** | Jamais réussi depuis le cloud | Lire `01_SPE`, les tâches Windows, Chrome | Alternative qui marche : ouvrir Claude Desktop → onglet Code sur le PC et coller `11_PROMPT_PC_BUREAU.md` |

Ce que je ne demande PAS : mots de passe TUNEPS/TnTrust, WhatsApp du directeur, carte bancaire. Les jetons passent
toujours par le formulaire sécurisé, jamais par le chat.
