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

Les fichiers dépassent déjà le quota gratuit. Deux choix étaient proposés.

**Décision du directeur, 15/11/2026 : Option A.**

- **Option A, gratuite (recommandée)** : le PC bureau garde les PDF complets dans `SPE_shared\Archives`. Supabase ne garde que les 60 derniers jours. Le robot de téléchargement du PC le fait déjà en partie.
- **Option B, payante** : Supabase Pro, environ 25 dollars par mois, 100 Go de fichiers et 8 Go de base. Plus aucune limite pratique.

Aucune suppression dans Supabase sans accord écrit du directeur. L'accord pour l'option A a été donné le 15/11/2026.

## Mise en œuvre de l'option A : robot d'archivage du PC

Constat du 15/11 : aucun fichier n'a plus de 60 jours. Les dossiers des offres encore ouvertes pèsent à eux seuls environ 1 Go. La règle « 60 jours » seule ne suffit donc pas. Le robot applique aussi la date limite des offres et un plafond.

Le robot `robots/pc/archiver_stockage.py` tourne toutes les 2 heures sur le PC :

1. Il copie chaque fichier Supabase dans `SPE_shared\Archives\supabase\` et contrôle la taille.
2. Il retire de Supabase seulement les fichiers dont la copie PC est contrôlée, dans cet ordre :
   - dossiers des offres dont la date limite est passée depuis plus de 2 jours ;
   - fichiers de plus de 60 jours ;
   - zips d'archives déjà copiés ;
   - si Supabase dépasse encore 800 Mo, les dépôts les plus anciens.
3. Il ne retire jamais les images métier, les logos, ni les dossiers dont la date limite tombe dans les 3 jours.
4. Chaque retrait est noté dans Supabase, collection `archives_pc`, avec le chemin du fichier sur le PC.

Le robot a besoin de la clé de service Supabase sur le PC, dans la variable `SUPABASE_SERVICE_KEY`. Sans elle, il s'arrête sans rien toucher.

Premier essai conseillé sur le PC, sans rien retirer :

    python robots\pc\archiver_stockage.py --essai

## Ce qui reste à faire

- Sur le PC : coller la règle de stockage dans les consignes des agents Rayen, Ines, Amine et Youssef (le cloud ne peut pas modifier les tâches liées au PC).
- Lancer `robots/pc/installer_serveur_spe.ps1` sur le PC pour que Chrome, les robots et l'archivage local tournent 24 h/24.
- Sur le PC : définir la variable `SUPABASE_SERVICE_KEY` (clé service_role de Supabase), puis lancer l'essai ci-dessus.
