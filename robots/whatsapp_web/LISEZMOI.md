# Robot WhatsApp Web SPE — sur une machine toujours allumée (sans Claude, sans PC du bureau)

Envoie la file « file_whatsapp » (Supabase) dans les groupes WhatsApp par métier, texte + image + PDF,
avec la bibliothèque `whatsapp-web.js` (méthode non officielle : utiliser un NUMÉRO DÉDIÉ à SPE, jamais celui du
directeur ; au plus un message par minute). Anti-doublon : un numéro d'offre déjà envoyé dans un groupe n'y est
jamais renvoyé (champ `wa_envoye` sur l'élément + collection locale `envoyes.json`).

## Installation (Oracle Cloud « Always Free », Ubuntu 22.04, ou mini-PC Linux au bureau)
```bash
curl -fsSL https://raw.githubusercontent.com/cherifch3ar-create/spe-cash/main/robots/whatsapp_web/install.sh | bash
```
Puis `npm start` une première fois : un QR code s'affiche dans le terminal → le scanner avec WhatsApp du numéro dédié
(Appareils connectés). La session est gardée dans `.wwebjs_auth/`. Ensuite le service systemd `spe-whatsapp` tourne 24 h/24.

## Réglages (`config.json`)
- `groupes` : nom exact du groupe WhatsApp -> true (seuls ces groupes reçoivent des messages) ;
- `pause_secondes` (60 par défaut), `max_par_passage` (10), `heures_silence` (23 → 7 : rien n'est envoyé la nuit).

## Ce que le robot ne fait jamais
Répondre à quelqu'un, écrire hors des groupes de la liste, supprimer un message, saisir un code, envoyer la nuit,
envoyer deux fois la même offre au même groupe, envoyer les éléments `statut` différent de `en_attente`.

État : écrit et relu, NON testé (aucun WhatsApp disponible depuis le cloud). Premier test à faire avec un seul groupe d'essai.
