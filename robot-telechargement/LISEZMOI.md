# Robot de téléchargement SPE (« Wissem-Robot »)

Télécharge les pièces des appels d'offres TUNEPS directement, **sans IA** (aucune consommation Claude).

1. **Installer (une fois)** : double-cliquer `Installer-robot.bat` (installe Playwright et crée la tâche Windows : toutes les heures, 24 h sur 24, 7 jours sur 7).
2. **Chrome du robot** (le robot « garde-session » le garde connecté à TUNEPS jour et nuit : rafraîchit toutes les 10 minutes et clique « Annuler » sur la fenêtre d'inactivité) : double-cliquer `Lancer-Chrome-SPE.bat`. La première fois, **vous** vous connectez à TUNEPS dans cette fenêtre (le robot ne tape jamais de code). Laissez la fenêtre ouverte.
3. **Lancer à la main** : `lancer-robot.bat` (ou `lancer-robot.bat --essai` pour voir sans rien télécharger).
4. **Priorités** : écrire les N° dans `priorites.txt` (une ligne « N° lien »).

Résultat : pièces dans `SPE_shared\Appels_offres\<N°>\` et copie en ligne (ouvrable depuis le téléphone, fiche de l'offre → Ouvrir les pièces), fichier `_pieces.json`, état écrit dans l'offre (Supabase), une ligne dans le rapport des agents.
Si TUNEPS demande une connexion, le robot s'arrête et écrit « BESOIN » : se reconnecter dans la fenêtre du robot puis relancer.
Interdits dans le code : mot de passe, PIN, TnTrust, dépôt, signature, paiement, suppression ou écrasement de fichier.

## Robot en ligne (sans PC) — recommandé
`robot_en_ligne.py` tourne sur GitHub Actions **toutes les heures**, sans PC, sans connexion TUNEPS et sans IA.
Il lit la liste publique des pièces de chaque offre active (sauf fourniture seule), télécharge les fichiers,
les copie dans le stockage `appels-offres` et met à jour la fiche de l'offre (« Ouvrir les pièces »).
Priorités : `priorites.txt` est lu en premier. Lancement à la main : GitHub → Actions → « Robot en ligne » → Run workflow.
Le robot du PC (ci-dessus) reste utile seulement pour les pièces qui exigeraient une connexion TUNEPS.
