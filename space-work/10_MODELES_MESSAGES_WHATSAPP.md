# Modèles définitifs des messages WhatsApp SPE

Décision du directeur, 15/11/2026 : « créer un modèle test pour tous les messages WhatsApp pour finir ce travail définitivement ».

## Le chemin unique

1. Les agents et les robots déposent un message dans la file WhatsApp de Supabase (`docs`, collection `file_whatsapp`, statut `en_attente`).
2. Le robot WhatsApp Web du PC (`robots/whatsapp_web`) lit cette file toutes les 10 minutes et envoie dans le groupe indiqué.
3. Il marque le message `envoye`. Il n'envoie jamais deux fois la même offre du même type dans le même groupe.

Règles du robot : silence de 23 h à 7 h, 10 messages au plus par passage, une minute entre deux messages, seulement les groupes listés dans `robots/whatsapp_web/config.json`.

Le pont vers l'ancienne boîte d'envoi du PC n'est installé que si Node.js est absent.

## Les six modèles

| Modèle | Quand | Qui le dépose | Groupe | Type |
|---|---|---|---|---|
| A. Annonce écrite des nouvelles offres | à chaque nouvelle offre | Rayen | groupe du métier, copie « appel d'offre SPE » | texte |
| B. Affiche de l'offre | après chaque nouvelle offre | robot des affiches | groupe du métier | image + légende |
| C. Alerte date limite proche | moins de 48 h | Rayen ou superviseur | groupe du métier | texte |
| D. Étude terminée | étude PDF prête | bureau d'études | groupe du métier ou « SPE Réunion agents » | PDF + légende |
| E. Bilan quotidien | 20 h | Sirine | « SPE Réunion agents » | texte |
| F. Réponse à une commande | après « 1 à 5 + N° » | Amine | le groupe où la commande a été écrite | texte |

### A. Annonce écrite

```
Rayen (Recherche) — Nouvelles annonces — <métier> (<jj/mm/aaaa hh:mm>)

[NATURE] <acheteur> — <objet> (<N°>)
Date limite : <jj/mm/aaaa hh:mm> (J-<n>)
<lien TUNEPS>

Répondez avec le chiffre + N° : 1 fiche de visite · 2 étudier · 3 cahier des charges · 4 sûr ou non · 5 rappel demain
```

### B. Affiche

Image au modèle « carte », comme l'exemple du directeur du 30/10. Elle contient l'en-tête SPE, le bandeau du domaine, le titre et le tableau. Le tableau donne la référence, l'acheteur, le lieu, la date limite en rouge avec « dans N jours », le domaine et la procédure. Viennent ensuite les 4 services, le bouton « Répondez OUI » et le pied de page. Légende :

```
Une belle opportunité à <lieu> : le <N°>, <objet>.
Date limite : <date> (J-<n>).
Tout est dans l'application SPE.

Répondez 2 + N° pour lancer l'étude.
```

### C. Alerte

```
ALERTE — date limite proche
<N°> : <objet>
Date limite : <date> (J-<n>).
Répondez 2 + <N°> pour lancer l'étude tout de suite, ou 5 + <N°> pour un rappel demain.
```

### D. Étude

PDF joint, légende :

```
Bureau d'études — Étude de l'offre <N°> (<acheteur>).
Résumé : faisable / à vérifier / prix estimé. Le PDF complet est joint.
Répondez 4 + <N°> pour l'avis « sûr ou non ».
```

### E. Bilan quotidien

```
Sirine (Directrice IA) — Bilan du <jj/mm>
Terminé : …
Résultats importants : …
Bloqué : …
Décisions à prendre par vous : 1. … (répondre OUI 1 / NON 1)
Améliorations du jour : …
État : base, robot WhatsApp, sauvegardes.
```

### F. Réponse à une commande

```
Amine — Commande reçue : « 2 <N°> ». L'étude de l'offre <N°> est lancée ; vous recevrez le PDF dans ce groupe.
```

## Le test

```
python robots/test_messages_whatsapp.py --envoyer
```

Le script met un exemple de chaque modèle, avec une vraie offre ouverte, dans la file pour « SPE Réunion agents », marqué [TEST 1/6] à [TEST 6/6]. Le robot WhatsApp Web les envoie en premier.

Premier test déposé le 15/11/2026 : 6 messages, dont l'affiche et le PDF, vérifiés lisibles.

## Ménage fait le 15/11/2026

110 anciens messages en attente depuis le 5-7/11 (104 affiches de l'ancien modèle et 6 messages d'agents) sont passés au statut `perime`. Leur contenu et leur ancien statut restent dans chaque document. Sans cela, le robot les aurait envoyés en masse dès sa connexion.
