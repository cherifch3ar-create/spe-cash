# 08 — Croissance : les agents suivants (comptabilité, achats, recouvrement…)

Principe fixé par le directeur : « après on va grandir avec des agents de comptabilité, responsable achats, recouvrement ».
Règle d'or pour chaque nouvel agent : **un robot fait le mécanique, l'agent IA ne fait que ce qui demande de réfléchir,
le directeur décide**. Chaque agent a : une table ou collection à lui, un passage par jour, un rapport d'une ligne dans
`events`, et jamais de paiement, de signature ni d'envoi sans OUI.

| Ordre | Agent | Ce qu'il fait (IA) | Ce que le robot fait (gratuit) | Données | Existe déjà ? |
|---|---|---|---|---|---|
| 1 | **Recouvrement « Hatem »** | relit les factures en retard, rédige la relance polie, propose l'échéancier | liste les factures dont l'échéance est passée, calcule les retards, met la relance dans la file WhatsApp/e-mail (envoi après OUI) | `factures`, `paiements` (déjà dans le Workspace : Comptabilité) | tâche désactivée depuis le 02/11, à réactiver 1×/jour sur Sonnet |
| 2 | **Comptabilité** | classe les dépenses, prépare la déclaration mensuelle, signale les écarts | importe les relevés (CSV) et les factures, totalise par mois, rapproche encaissements et factures | `factures`, `paiements`, `depenses` (Workspace) + le Cash Manager archivé (rappel du 01/02/2027) | module Comptabilité du Workspace ; agent à créer |
| 3 | **Achats / responsable achats** | compare 3 devis, conseille le moins cher conforme (Lotfi fait déjà la recherche), prépare le bon de commande | tient la liste des fournisseurs et des prix vérifiés (mémoire « Compétence agent SPE »), alerte quand une pièce de dossier manque | `fournisseurs`, `bons_commande` (cycle V3 de Karim : devis → bon de commande) | Lotfi (recherche) ; agent achats à créer |
| 4 | Chantiers et réception | rapport de travaux, bon de réception, fiche de visite avec photos | range les photos du groupe « employé » (Facteur le fait déjà), calcule l'avancement | `chantiers`, `visites` | Mehdi (visites), cycle V3 |
| 5 | Facturation | génère la facture à partir du bon de réception | numérotation, PDF, dépôt dans la file | `factures` | module Workspace |

Chaque agent nouveau = un prompt court (15 lignes), un seul passage par jour, sur Sonnet, créé seulement quand le robot
qui lui prépare le travail tourne déjà. Ordre proposé : Hatem (déjà écrit) dès que le serveur local est installé, puis
Comptabilité en décembre avec la reprise du Cash Manager, puis Achats.
