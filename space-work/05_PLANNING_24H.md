# 05 — Planning 24 h des agents Claude (appliqué le 14/11/2026 à 11:26, heure de Tunis)

Demande du directeur : « je vois le matin, je veux le 24 heures ; maintenant changer les dates pour tester tout ».
Contrainte réelle : la limite d'usage Claude a été atteinte aujourd'hui à ~10:30 avec seulement 5 agents passés
le matin (Rayen, Amine, Facteur, Khalil, Amira) plus la session de travail. Lancer les 52 tâches d'un coup
reproduirait la panne des 1er–2 novembre (toutes coupées « limite atteinte »). Le planning étale donc les
12 agents actifs sur 24 h, un seul à la fois, et laisse les 40 autres désactivées.

## Tâches ACTIVES — nouveau planning (heure de Tunis)
| Heure | Agent | Rôle | Modèle | Avant |
|---|---|---|---|---|
| 01:10 | Karim | développement Workspace | Fable 5.2 | 20:10 |
| 02:37 | Khalil robotisation | propose un robot (sans Chrome) | Fable 5.2 | 10:37 |
| 04:41 (lun, mer, ven) | Mounir | publicité (préparation) | défaut | 10:41 |
| 07:47 · 13:47 · 19:47 | Facteur | réponses WhatsApp + file | Sonnet 5.5 | 08:47 · 14:47 · 20:47 |
| 08:33 · 15:33 · 22:33 (lun–sam) | Rayen | recherche TUNEPS | Opus 5.5 | 09:33 · 16:33 |
| 10:17 · 17:17 · 21:17 | Amine | envoi WhatsApp + écoute | Opus 5.5 | 10:17 · 17:17 |
| 11:43 | Amira | contenu Facebook (ChatGPT) | Opus 5.5 | 10:43 |
| 12:52 (lun–sam) | Youssef | publication Facebook | Opus 5.5 | 11:52 |
| 14:13 · 17:13 (lun–sam) | Ines | études (tous domaines) | Fable 5.2 | 17:13 |
| 22:41 | Ménage léger SPE Live | archivage vérifié des PDF | Sonnet 5.5 | inchangé |
| 23:46 | Lotfi | recherche approfondie | Fable 5.2 | 15:46 |
| rappels | Eya Soft (19/11), Cash Manager (01/02/2027) | — | — | inchangés |

Couverture : passages toutes les 1 à 3 heures, jour et nuit ; jamais deux agents à la même minute ;
la nuit (01:10, 02:37, 04:41, 23:46) est réservée aux agents qui n'ont pas besoin du directeur.

## Tests lancés aujourd'hui (14/11)
- 11:26 : **Khalil** (son passage de 10:37 avait échoué : limite) et **Ines** (passage d'hier abandonné) relancés à la main.
- 11:43 : Amira ; 12:52 : Youssef ; 13:47 : Facteur ; 14:13 : Ines ; 15:33 : Rayen ; 17:17 : Amine ; 22:41 Ménage ; 23:46 Lotfi ; 01:10 Karim ; 02:37 Khalil.
- Déjà passés ce matin avec succès : Rayen 09:33, Facteur 08:47, Amine 10:17.

## Tâches DÉSACTIVÉES (40) — non touchées
Coupées « limite d'usage » les 1er–2 novembre ou mises en pause les 12–13/11 : Nour (rapport du matin), Yassine
(bureau d'études, dernier passage réussi 13/11), Wissem, Sirine (contrôle et bilan 20:00), Nabil, Salma, Eya, Sana,
Ilyes, Mourad, Walid, Hana, Fares, Selim, Nader, Mehrez, Ameni, Yosra, Rim, Bilel, Dhia, Hatem, Adam, Leila,
Yasmine, Rania, Nadia, Lina, Expert Ascenseurs, Ahmed, Mehdi, Mariem, Nizar, Hiba, Ons, Archives, Notifications,
Sami ×2, Karim (code commun), Rapport des agents, Réunion des agents.
Recommandation : en réactiver au plus 3, sur Sonnet, une seule fois par jour : **Nour** (rapport du matin 07:17),
**Yassine** (études 09:03) et **Sirine bilan** (19:57). Les « contrôleurs » (Fares, Hana, Mehrez, Yosra, Ameni,
Selim) restent à remplacer par le robot superviseur (voir 04_ARCHITECTURE_CIBLE).

## Ce qui n'a pas été changé
Les modèles (Opus 5.5 / Fable 5.2 sur 8 agents) : à décider par le directeur ; passer Rayen, Amine, Amira, Youssef
sur Sonnet diviserait la consommation par 3 environ. Les prompts : inchangés.
