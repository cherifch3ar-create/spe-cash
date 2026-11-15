# Solution : la limite de 100 Mo de SPE Live ne doit plus jamais bloquer

Date : 15/11/2026 — demande du directeur : « je veux trouver une solution pour ça ».

## Ce qui s'est passé

- SPE Live (l'artifact claude.ai) a une base limitée à 100 Mo. Cette limite ne peut pas être augmentée.
- Les agents y stockaient les PDF en base64 (collection `pdf_parts`). Une seule pièce pèse 100 à 300 Ko.
- La base s'est remplie, et tous les agents travaillaient sans pouvoir écrire (Rayen avait trouvé 82 offres).

## Ce qui a été fait le 14/11/2026 (autorisé : « Oui »)

- 525 pièces PDF copiées dans Supabase, contrôlées, puis retirées de SPE Live.
- Archives : `appels-offres/archives/pdf_parts_20261114_1706_1.zip` et `pdf_parts_retire_20261114_1716_1..4.zip`, avec leurs manifestes JSON.
- SPE Live accepte de nouveau les écritures (test « events/menage-… » réussi). `shared/sauvegardes` mis à jour.

## La solution durable : trois étages

| Étage | Rôle | Limite | Ce qu'on y met |
|---|---|---|---|
| SPE Live (artifact) | Écran et file de travail des agents | 100 Mo, fixe | Textes courts : offres, tâches, statut, file WhatsApp, liens |
| Supabase base (`public.docs`) | Mémoire complète | 500 Mo gratuit, extensible | Copie de tout, historique, journal |
| Supabase Storage + PC bureau | Fichiers | 1 Go gratuit, puis payant ; disque du PC illimité | PDF, images, affiches, études |

## Règle de stockage pour tous les agents (à appliquer dès maintenant)

1. Jamais de fichier en base64 dans SPE Live. Un PDF ou une image va dans Supabase Storage ou dans `SPE_shared` du PC. SPE Live garde seulement le nom et le lien.
2. Un document SPE Live ne dépasse pas 50 Ko.
3. `events` et `statut` de plus de 30 jours : copiés dans Supabase puis retirés de SPE Live (ménage mensuel, avec sauvegarde vérifiée avant retrait).
4. Si l'écriture échoue pour « quota », l'agent écrit dans Supabase `public.docs` (même structure : collection, id, data) et crée un événement d'alerte. Il ne s'arrête pas.

La règle est aussi enregistrée dans SPE Live : `shared/regle_stockage`.

## Point d'attention : Supabase Storage

Relevé du 15/11/2026 :

| Élément | Utilisé | Gratuit |
|---|---|---|
| Base Supabase | 148 Mo | 500 Mo |
| Fichiers Supabase | 1 366 Mo | 1 024 Mo |

Les fichiers dépassent déjà le quota gratuit. Deux choix, à décider par le directeur :

- **Option A, gratuite (recommandée)** : le PC bureau garde les PDF complets dans `SPE_shared\Archives`. Supabase ne garde que les 60 derniers jours. Le robot de téléchargement du PC le fait déjà en partie.
- **Option B, payante** : Supabase Pro, environ 25 dollars par mois, 100 Go de fichiers et 8 Go de base. Plus aucune limite pratique.

Aucune suppression dans Supabase sans accord écrit du directeur.

## Ce qui reste à faire

- Sur le PC : coller la règle de stockage dans les consignes des agents Rayen, Ines, Amine et Youssef (le cloud ne peut pas modifier les tâches liées au PC).
- Lancer `robots/pc/installer_serveur_spe.ps1` sur le PC pour que Chrome, les robots et l'archivage local tournent 24 h/24.
- Choisir l'option A ou B pour les fichiers Supabase.
