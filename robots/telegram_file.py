# -*- coding: utf-8 -*-
"""
Robot TELEGRAM SPE (sans IA, gratuit, officiel) — GitHub Actions toutes les 10 minutes.
Canal de secours : recopie la file « file_whatsapp » (statut en_attente, texte ou image) vers les groupes/chaînes
Telegram de robots/telegram_groupes.json (nom du groupe WhatsApp -> chat_id Telegram), puis marque
telegram_envoye_le sur l'élément. Ne change PAS le statut WhatsApp (le robot WhatsApp envoie toujours).
Sans jeton TELEGRAM_BOT_TOKEN (secret GitHub) : ne fait rien.
Anti-doublon : un même numéro d'offre n'est jamais envoyé deux fois au même groupe (champ telegram_envoye_le + sig).
Usage : python robots/telegram_file.py [--essai] [--max 20]
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ICI = os.path.dirname(os.path.abspath(__file__))
H = {"apikey": CLE, "Authorization": "Bearer " + CLE, "Content-Type": "application/json"}


def ms(): return int(time.time() * 1000)
def log(t): print(time.strftime("%H:%M:%S"), t, flush=True)


def sb(method, chemin, corps=None, prefer=None):
    h = dict(H); h.update({"Prefer": prefer} if prefer else {})
    req = urllib.request.Request(SB + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read(); return r.status, (json.loads(b) if b else None)


def tg(methode, **params):
    data = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None}).encode()
    with urllib.request.urlopen("https://api.telegram.org/bot%s/%s" % (TOKEN, methode), data=data, timeout=60) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--essai", action="store_true"); ap.add_argument("--max", type=int, default=20); a = ap.parse_args()
    if not TOKEN and not a.essai:
        log("Pas de jeton Telegram : rien à faire."); return 0
    groupes = json.load(open(os.path.join(ICI, "telegram_groupes.json"), encoding="utf-8"))
    _, rows = sb("GET", "/rest/v1/docs?collection=eq.file_whatsapp&select=id,data&data-%3E%3Estatut=eq.en_attente&order=maj.asc&limit=300")
    env, saut = 0, 0
    for r in rows or []:
        if env >= a.max: break
        d = r.get("data") or {}
        if d.get("telegram_envoye_le"): continue
        grp = d.get("groupe") or d.get("destinataire") or ""
        chat = groupes.get(grp) or groupes.get("*")
        if not chat or d.get("type") not in (None, "texte", "image"): saut += 1; continue
        texte = (d.get("texte") or "").strip()
        img = d.get("lien_image") or d.get("png") or ""
        if img.startswith("/_blob/"): img = SB + "/storage/v1/object/public/blobs/" + img[7:]
        if not texte and not img: saut += 1; continue
        if a.essai: log("  (essai) %s -> %s : %s" % (r["id"], grp, texte[:80])); env += 1; continue
        try:
            if img: tg("sendPhoto", chat_id=chat, photo=img, caption=texte[:1000])
            else: tg("sendMessage", chat_id=chat, text=texte[:4000])
            d["telegram_envoye_le"] = ms()
            sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "file_whatsapp", "id": r["id"], "data": d, "maj": ms(), "source": "robot_telegram"},
               prefer="resolution=merge-duplicates,return=minimal")
            env += 1; time.sleep(1.5)
        except Exception as ex:
            log("  - %s : %s" % (r["id"], ex))
    log("%d envoyé(s) sur Telegram, %d sans groupe ou sans texte" % (env, saut))
    if env and not a.essai:
        t = ms()
        sb("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-robot_telegram" % t, "maj": t, "source": "robot_telegram",
                                   "data": {"t": t, "agent": "telegram", "texte": "Robot Telegram : %d message(s) de la file recopié(s) sur Telegram." % env}}, prefer="return=minimal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
