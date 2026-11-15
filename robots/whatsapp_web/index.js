// Robot WhatsApp Web SPE — voir LISEZMOI.md. Sans IA. Numéro dédié obligatoire.
'use strict';
const fs = require('fs'); const path = require('path');
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const CFG = JSON.parse(fs.readFileSync(path.join(__dirname, 'config.json'), 'utf8'));
const H = { apikey: CFG.supabase_cle_publique, Authorization: 'Bearer ' + CFG.supabase_cle_publique, 'Content-Type': 'application/json' };
const ENVOYES = path.join(__dirname, 'envoyes.json');
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const dodo = (ms) => new Promise(r => setTimeout(r, ms));

async function sb(method, chemin, corps, prefer) {
  const r = await fetch(CFG.supabase_url + chemin, { method, headers: prefer ? { ...H, Prefer: prefer } : H, body: corps ? JSON.stringify(corps) : undefined });
  if (!r.ok) throw new Error('Supabase ' + r.status + ' ' + (await r.text()).slice(0, 200));
  const t = await r.text(); return t ? JSON.parse(t) : null;
}
function silence() { const h = new Date().getHours(); const [a, b] = CFG.heures_silence; return a > b ? (h >= a || h < b) : (h >= a && h < b); }
function lireEnvoyes() { try { return JSON.parse(fs.readFileSync(ENVOYES, 'utf8')); } catch { return {}; } }
// Clé anti-doublon : N° + groupe + type (l'annonce écrite ET l'affiche d'une même offre partent toutes les deux ; les tests ne bloquent rien).
function cle(d, groupe) { if (d.test) return ''; const no = (d.no || (String(d.texte || '').match(/\b[S]?\d{11}\b/) || [''])[0]); return no ? no + '|' + groupe + '|' + (d.type || 'texte') : ''; }

async function fichierDepuis(d) {
  const url = d.lien_pdf || d.lien_image || (d.png && d.png.startsWith('/_blob/') ? CFG.supabase_url + '/storage/v1/object/public/blobs/' + d.png.slice(7) : d.png);
  if (!url) return null;
  const r = await fetch(url); if (!r.ok) throw new Error('fichier ' + r.status);
  const buf = Buffer.from(await r.arrayBuffer());
  const mime = r.headers.get('content-type') || (d.type === 'pdf' ? 'application/pdf' : 'image/png');
  return new MessageMedia(mime, buf.toString('base64'), d.nom_fichier || (d.type === 'pdf' ? 'document.pdf' : 'image.png'));
}

async function passage(client, chats) {
  if (silence()) { log('heures de silence : rien envoyé'); return; }
  const rows = await sb('GET', '/rest/v1/docs?collection=eq.file_whatsapp&select=id,data&data-%3E%3Estatut=eq.en_attente&order=data-%3Epriorite.asc,maj.asc&limit=100');
  const envoyes = lireEnvoyes(); let n = 0;
  for (const row of rows || []) {
    if (n >= CFG.max_par_passage) break;
    const d = row.data || {}; const groupe = d.groupe || d.destinataire || CFG.groupe_par_defaut;
    if (!CFG.groupes[groupe]) { log('groupe non autorisé, ignoré :', groupe); continue; }
    const chat = chats[groupe]; if (!chat) { log('groupe introuvable sur ce numéro :', groupe); continue; }
    const k = cle(d, groupe);
    if (k && envoyes[k]) { // doublon : marquer sans envoyer
      await sb('POST', '/rest/v1/docs?on_conflict=collection,id', { collection: 'file_whatsapp', id: row.id, data: { ...d, statut: 'doublon', mode: 'robot_web', maj_robot: Date.now() }, maj: Date.now(), source: 'robot_whatsapp_web' }, 'resolution=merge-duplicates,return=minimal');
      log('doublon ignoré', row.id, groupe); continue;
    }
    try {
      const texte = String(d.texte || '').slice(0, 4000);
      const media = (d.type === 'pdf' || d.type === 'image') ? await fichierDepuis(d) : null;
      if (media) await chat.sendMessage(media, { caption: texte }); else if (texte) await chat.sendMessage(texte); else { log('vide', row.id); continue; }
      if (k) { envoyes[k] = Date.now(); fs.writeFileSync(ENVOYES, JSON.stringify(envoyes)); }
      await sb('POST', '/rest/v1/docs?on_conflict=collection,id', { collection: 'file_whatsapp', id: row.id, data: { ...d, statut: 'envoye', envoye_le: Date.now(), mode: 'robot_web', wa_envoye: k || true }, maj: Date.now(), source: 'robot_whatsapp_web' }, 'resolution=merge-duplicates,return=minimal');
      n++; log('envoyé', row.id, '->', groupe); await dodo(CFG.pause_secondes * 1000);
    } catch (e) {
      const essais = (d.essais || 0) + 1;
      await sb('POST', '/rest/v1/docs?on_conflict=collection,id', { collection: 'file_whatsapp', id: row.id, data: { ...d, essais, statut: essais >= 3 ? 'echec' : 'en_attente', erreur_robot: String(e.message).slice(0, 200) }, maj: Date.now(), source: 'robot_whatsapp_web' }, 'resolution=merge-duplicates,return=minimal');
      log('erreur', row.id, e.message);
    }
  }
  const t = Date.now();
  await sb('POST', '/rest/v1/docs', { collection: 'events', id: 'e-' + t + '-robot_whatsapp_web', maj: t, source: 'robot_whatsapp_web', data: { t, agent: 'amine', texte: 'Robot WhatsApp Web : ' + n + ' message(s) envoyé(s), connecté oui.' } }, 'return=minimal');
}

(async () => {
  const client = new Client({ authStrategy: new LocalAuth({ dataPath: path.join(__dirname, '.wwebjs_auth') }), puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] } });
  // Connexion : QR à scanner, OU code à 8 caractères (utile quand on regarde le PC à distance depuis le téléphone).
  let demande = false;
  client.on('qr', async qr => {
    log('Scanner ce QR avec le numéro dédié SPE :'); qrcode.generate(qr, { small: true });
    if (demande) return; demande = true;
    let num = String(CFG.numero_pairage || process.env.SPE_NUMERO || '').replace(/\D/g, '');
    if (!num) {
      const rl = require('readline').createInterface({ input: process.stdin, output: process.stdout });
      num = await new Promise(r => rl.question('\nOU BIEN, sans scanner : tapez le numéro WhatsApp SPE avec 216 devant (ex. 21612345678) puis Entrée : ', x => { rl.close(); r(String(x).replace(/\D/g, '')); }));
    }
    if (num.length < 8) { log('Pas de numéro : scannez le QR.'); return; }
    try {
      const code = await client.requestPairingCode(num);
      log('================================================');
      log('CODE DE CONNEXION : ' + code);
      log('Sur le téléphone SPE : WhatsApp > Appareils connectés > Connecter un appareil >');
      log('« Connecter avec le numéro de téléphone » puis tapez ce code.');
      log('================================================');
    } catch (e) { log('Code impossible (' + e.message + ') : scannez le QR.'); }
  });
  client.on('ready', async () => {
    log('WhatsApp connecté');
    const tous = await client.getChats(); const chats = {};
    for (const c of tous) if (c.isGroup && CFG.groupes[c.name]) chats[c.name] = c;
    log('groupes trouvés :', Object.keys(chats).join(', ') || 'aucun');
    for (;;) { try { await passage(client, chats); } catch (e) { log('passage en erreur :', e.message); } await dodo(CFG.intervalle_minutes * 60000); }
  });
  client.on('disconnected', r => { log('déconnecté :', r); process.exit(1); });
  await client.initialize();
})();
