# 02 — Réponse : WhatsApp, affiches, agents et contrôleurs qui tournent sans arrêt, sans PC et sans consommer

Question du directeur (14/11/2026) : « Je veux que le WhatsApp tourne avec les images des appels d'offres,
avec les agents, les contrôleurs des agents, et tous les agents qui travaillent sans arrêt, sans consommer. »

## La réponse courte
1. **Tout ce qui est mécanique devient un robot gratuit** (script sans IA) : lecture TUNEPS, pièces, affiches, file WhatsApp, Facebook, superviseur. Un robot ne consomme **aucun crédit Claude**. Il tourne sur GitHub Actions (gratuit, déjà en place) ou sur une « machine qui ne dort jamais ».
2. **Claude ne fait plus que réfléchir** : études, choix des offres, textes. Deux passages courts par jour, sur Sonnet (pas Fable), au lieu d'agents qui tournent sans arrêt. C'est ce qui épuise la limite d'usage aujourd'hui : 7 tâches cloud ont été coupées « limite atteinte » les 1er–2 novembre, et Khalil tourne chaque jour sur le modèle le plus cher.
3. **WhatsApp est le seul point qui ne peut pas être 100 % gratuit ET 100 % officiel ET sans PC en même temps.** Il faut choisir (tableau ci-dessous). Ma recommandation : garder la méthode actuelle (WhatsApp Web piloté par un robot, **pas par Claude**), mais la faire tourner sur une petite machine toujours allumée au lieu du PC du bureau, avec un **numéro dédié** à SPE.

## Pourquoi ça s'arrête aujourd'hui (preuves dans `01_ETAT_REEL`)
- Les envois WhatsApp, les études et les affiches sont faits par **des agents Claude du PC** : arrêtés depuis le **09/11 11:50** (PC/application fermés, limite d'usage, Chrome SPE pas ouvert). 104 images d'appels d'offres attendent dans la file depuis le 07/11.
- Les seuls qui tournent sans arrêt sont les **robots** : relevé en ligne (toutes les 2 h), veille Google, et depuis ce matin le robot en ligne des pièces. Aucun ne consomme Claude.
- Le robot de téléchargement du PC tourne mais crie « BESOIN : Chrome n'est pas ouvert » toutes les heures depuis hier 16:05 : un seul geste humain manque.

## WhatsApp : les 4 façons, avec leur vrai prix
| Façon | Groupes WhatsApp ? | Prix | Sans PC ? | Risque | Avis |
|---|---|---|---|---|---|
| **A. Robot WhatsApp Web** (bibliothèque type whatsapp-web.js / Baileys, sans IA) sur une machine toujours allumée | Oui (poste dans les groupes par métier, texte + image) | 0 DT | Oui si la machine est un mini-serveur gratuit ou un petit boîtier au bureau | Non officiel : Meta peut bloquer le numéro. Utiliser un **numéro dédié**, pas celui du directeur ; au plus ~1 message/minute | **Recommandé** : c'est déjà le principe du « robot WhatsApp du PC », on le déplace et on retire Claude de la boucle |
| **B. API officielle WhatsApp Cloud (Meta)** | **Non** : l'API ne poste pas dans les groupes. Elle envoie 1 à 1 à des numéros qui ont accepté | Gratuit pour répondre dans les 24 h ; les messages « marketing » envoyés en premier sont payants (quelques centimes par message, facturés par Meta) | Oui (GitHub Actions) | Aucun (officiel) | Bon pour une **liste d'abonnés** (chaque client reçoit l'affiche en privé) ; pas pour vos groupes actuels |
| **C. Chaîne WhatsApp (Channel)** | Diffusion à des abonnés | 0 DT | Non : pas d'API, il faut poster à la main ou via un robot Web (= A) | — | Complément possible |
| **D. Telegram (Bot API officielle)** | Oui : groupes et chaînes, sans limite, texte + image + PDF | 0 DT | Oui (GitHub Actions, 20 lignes de Python) | Aucun | **Canal de secours gratuit et officiel** : les mêmes affiches partent sur Telegram même quand WhatsApp est bloqué |

## Les affiches (images des appels d'offres) sans IA
Les 22 images par métier sont déjà en ligne (`images-domaines`). Un robot Python (Pillow) sur GitHub Actions peut
composer chaque affiche : image du métier + titre + acheteur + lieu + date limite + QR vers la fiche, puis
l'enregistrer en brouillon dans `affiches` (comme `affAuto` le fait aujourd'hui, mais sans que l'application
soit ouverte sur le PC). La validation reste humaine (Centre d'approbation) ou automatique après 2 h si vous le décidez.

## Les agents et leurs contrôleurs sans consommer
- **Superviseur = un robot**, pas un agent IA : un passage GitHub Actions toutes les heures lit `agent_tasks`,
  relance ce qui est en erreur (3 essais), marque « bloqué » et écrit une ligne `events`. Coût 0.
- **Contrôle qualité = des règles**, pas des agents : doublon (même numéro d'offre déjà envoyé), affiche sans date limite,
  offre expirée, fourniture seule → refusé par le robot avant envoi. Les 6 agents « contrôleurs » coupés le 02/11
  (Selim, Nader, Mehrez, Ameni, Yosra…) faisaient ce travail avec Claude : c'est la cause des limites atteintes.
- **Agents IA gardés** (consomment, mais peu) : Bureau d'étude (Yassine/Ines) 2 fois par jour, 15 minutes, modèle Sonnet,
  sur les seules offres nouvelles avec pièces ; Rapport du matin pour le directeur, 1 fois par jour.
- Khalil (Fable 5.2, chaque jour) : passer sur Sonnet ou 2 fois par semaine.

## Ce qu'il faut pour que ça tourne PC éteint
1. Une « machine qui ne dort jamais » pour le robot WhatsApp Web (choix A) : soit un **mini-serveur gratuit** (Oracle Cloud « Always Free » : 4 cœurs ARM, 24 Go, 0 DT, carte bancaire demandée pour l'identité, jamais débitée), soit un **mini-PC/Raspberry Pi au bureau** (≈ 250–400 DT une fois, 3 W, jamais en veille). Je prépare l'installation ; vous créez le compte ou achetez le boîtier.
2. Tout le reste sur **GitHub Actions** (déjà gratuit, déjà en place) et **Supabase** (déjà en place).
3. Claude seulement pour les études et le rapport : 2 à 3 passages courts par jour.
4. Un numéro WhatsApp dédié à SPE (carte SIM à 5 DT) pour ne jamais risquer le numéro du directeur.

## Ce que je peux faire dès votre OK (ordre)
1. Robot affiches (GitHub Actions, sans IA) → les 104 images en attente et les 86 brouillons repartent.
2. Robot superviseur + table `agent_tasks` (SQL fourni dans `supabase/agent_tasks.sql`).
3. Robot Telegram (canal de secours, officiel, gratuit).
4. Robot WhatsApp Web déplacé sur la machine toujours allumée, avec les règles anti-doublon.
5. Réduction des tâches Claude : Khalil sur Sonnet, bureau d'étude 2×/jour, rapport 1×/jour.
Aucune de ces étapes ne supprime un projet existant ; chacune commence par une sauvegarde.
