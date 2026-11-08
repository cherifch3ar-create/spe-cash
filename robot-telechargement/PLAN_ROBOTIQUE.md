# Plan robotique SPE — robots 24 h/24, agents IA pour réfléchir, équipe humaine pour décider

**Règle** : tout ce qui est mécanique est fait par un robot (gratuit, 24 h/24). Les agents IA ne font que ce qui demande de réfléchir. L'équipe humaine lit et décide dans l'application.

| # | Robot (sans IA, PC bureau) | Rythme | Remplace | État |
|---|---|---|---|---|
| 1 | Relevé TUNEPS (nouvelles offres) | toutes les 2 h, 24/24 | recherche mécanique de Rayen | en service |
| 2 | WhatsApp (envoi de la file) | permanent | envoi d'Amine | en service |
| 3 | **Téléchargement** des cahiers des charges + fiches de visite, copie en ligne | **toutes les heures, 24/24** | Wissem | prêt — à installer |
| 4 | **Garde-session TUNEPS** (rafraîchit, clique « Annuler ») | **en continu (toutes les 45 s), 24/24** | reconnexions manuelles | prêt — à installer |
| 5 | Copie SPE Live → application (Supabase) | 2 fois/jour (12h47, 18h47) | — | en service |
| 6+ | Un nouveau robot par jour ouvrable, proposé par Khalil | — | tâches répétitives repérées dans les events | Khalil : 10h37 lun–sam |

**Agents IA (réflexion seulement)** : Yassine et Ines (études à partir des pièces en ligne), Rayen (choix des offres intéressantes), Youssef (statut Facebook), Amine (réponses aux messages).

**Équipe humaine (lecture)** : application SPE Workspace sur PC et téléphone : Appels d'offres → fiche de l'offre → « 📄 Ouvrir les pièces ». Aucun compte nécessaire pour l'instant (accès par le lien, décision du directeur).

**Parallèle** : les robots tournent sur le PC bureau en même temps que les agents ; ils ne se gênent pas (verrou : un seul passage du robot à la fois ; onglet séparé ; Chrome du robot séparé).

**Sécurité (dans le code)** : jamais de mot de passe, PIN ou clé TnTrust ; jamais de dépôt, signature, paiement ; jamais de suppression ; pause entre les fichiers pour ne pas charger TUNEPS.
