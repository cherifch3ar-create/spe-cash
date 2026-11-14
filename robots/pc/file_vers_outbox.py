# -*- coding: utf-8 -*-
"""
Robot PONT SPE (sans IA) — sur le PC du bureau, toutes les 10 minutes.
Lit la file « file_whatsapp » de Supabase (statut en_attente) et dépose des fichiers dans l'OUTBOX du robot WhatsApp
du PC (C:\\Users\\USER\\Desktop\\01_SPE\\SPE_shared\\outbox), qui les envoie en quelques secondes.
Pourquoi : les agents Amine/Facteur lisent l'ancienne base SPE Live (pleine, file vide) ; les 110 messages en attente
sont dans Supabase et personne ne les envoyait (constat du 14/11/2026).
Règles du directeur appliquées : un seul message regroupé par groupe toutes les 3 h, 5 offres au plus, pas d'offre
expirée, menu des commandes en bas, heures de silence 23 h–7 h, jamais deux fois la même offre dans le même groupe.
Usage : python file_vers_outbox.py [--essai] [--max 10]
"""
import argparse, base64, json, os, re, sys, time, urllib.request
from datetime import datetime

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
H = {"apikey": CLE, "Authorization": "Bearer " + CLE, "Content-Type": "application/json"}
OUTBOX = os.environ.get("SPE_OUTBOX", r"C:\Users\USER\Desktop\01_SPE\SPE_shared\outbox")
MEMO = os.path.join(os.path.dirname(OUTBOX), "pont_envoyes.json")  # anti-doublon local
GROUPES = {"appel d'offre SPE", "AO SPE Électrique", "AO SPE Mécanique", "AO SPE Portail", "AO SPE Surveillance caméra et alarme",
           "AO SPE Métal construction", "AO SPE Peinture", "AO SPE Maritime", "AO SPE Engins, levage et hydraulique", "SPE Réunion agents"}
DEFAUT = "appel d'offre SPE"
MENU = "Répondez avec le chiffre + N° : 1 fiche de visite · 2 étudier · 3 cahier des charges · 4 sûr ou non · 5 rappel demain"


def ms(): return int(time.time() * 1000)
def log(t): print(time.strftime("%H:%M:%S"), t, flush=True)


def sb(method, chemin, corps=None, prefer=None):
    h = dict(H); h.update({"Prefer": prefer} if prefer else {})
    req = urllib.request.Request(SB + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read(); return json.loads(b) if b else None


def groupe_de(d, offres):
    g = d.get("groupe") or d.get("destinataire")
    if g in GROUPES: return g
    no = d.get("no") or (re.search(r"\b[S]?\d{11}\b", d.get("texte", "") or "") or [None])[0]
    if no and no in offres and offres[no].get("groupe") in GROUPES: return offres[no]["groupe"]
    return DEFAUT


def numero(d): return d.get("no") or (re.search(r"\b[S]?\d{11}\b", d.get("texte", "") or "") or [""])[0]


def deposer(nom, obj, essai):
    if essai: log("  (essai) %s -> %s : %s" % (nom, obj["groupe"], (obj.get("texte") or obj.get("legende") or "")[:90])); return
    os.makedirs(OUTBOX, exist_ok=True)
    tmp = os.path.join(OUTBOX, nom + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(OUTBOX, nom))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--essai", action="store_true"); ap.add_argument("--max", type=int, default=10); a = ap.parse_args()
    h = datetime.now().hour
    if h >= 23 or h < 7: log("heures de silence : rien envoyé"); return 0
    memo = json.load(open(MEMO, encoding="utf-8")) if os.path.exists(MEMO) else {}
    offres = {r["id"]: (r.get("data") or {}) for r in sb("GET", "/rest/v1/docs?collection=eq.offres&select=id,data&limit=1500")}
    rows = sb("GET", "/rest/v1/docs?collection=eq.file_whatsapp&select=id,data&data-%3E%3Estatut=eq.en_attente&order=maj.asc&limit=300") or []
    par_groupe = {}
    for r in rows:
        d = r.get("data") or {}
        g = groupe_de(d, offres); no = numero(d)
        if no and no in offres:
            tri = offres[no].get("tri")
            if tri and int(tri) < ms() + 3 * 86400000: continue  # expirée ou à moins de 3 jours
        if no and memo.get(no + "|" + g): continue  # déjà envoyée dans ce groupe
        if (d.get("t") or 0) and int(d["t"]) < ms() - 7 * 86400000: continue  # message de plus de 7 jours : périmé
        par_groupe.setdefault(g, []).append((r, d, no))
    t = ms(); envoyes = 0; faits = []
    for g, items in par_groupe.items():
        if memo.get("_grp|" + g, 0) > t - 3 * 3600000: log("groupe %s : message regroupé envoyé il y a moins de 3 h" % g); continue
        textes = [x for x in items if (x[1].get("type") in (None, "texte")) and x[1].get("texte")]
        images = [x for x in items if x[1].get("type") == "image" and (x[1].get("lien_image") or x[1].get("png"))]
        if textes:
            lignes = []
            for r, d, no in textes[:5]:
                tx = re.sub(r"https?://\S+", "", d["texte"]).strip()
                lignes.append(tx[:400])
            reste = len(textes) - 5
            texte = "\n\n".join(lignes) + ("\n\n… et %d autres dans l'application SPE." % reste if reste > 0 else "") + ("\n\n" + MENU if g != "SPE Réunion agents" else "")
            deposer("pont_%d_%s.json" % (t, re.sub(r"\W", "_", g)), {"groupe": g, "texte": texte, "agent": "amine"}, a.essai)
            faits += textes[:5]; envoyes += 1
        for r, d, no in images[:a.max]:
            url = d.get("lien_image") or d.get("png") or ""
            if url.startswith("/_blob/"): url = SB + "/storage/v1/object/public/blobs/" + url[7:]
            try:
                with urllib.request.urlopen(url, timeout=60) as rr: png = rr.read()
            except Exception as ex: log("  image illisible %s : %s" % (r["id"], ex)); continue
            deposer("pont_%d_%s.json" % (ms(), r["id"]), {"groupe": g, "fichier_base64": base64.b64encode(png).decode(), "nom_fichier": d.get("nom_fichier") or ("affiche_%s.png" % (no or r["id"])),
                                                           "legende": (d.get("texte") or "")[:900], "agent": "amine"}, a.essai)
            faits.append((r, d, no)); envoyes += 1; time.sleep(2)
        memo["_grp|" + g] = t
    # Affiches VALIDÉES dans le Centre d'approbation et pas encore envoyées : une image par offre dans le groupe du métier.
    try:
        aff = sb("GET", "/rest/v1/docs?collection=eq.affiches&select=id,data&data-%3E%3Estatut=eq.valide&order=maj.desc&limit=100") or []
    except Exception as ex:
        aff = []; log("affiches non lisibles : %s" % ex)
    n_aff = 0
    for r in aff:
        if n_aff >= a.max: break
        d = r.get("data") or {}
        if d.get("envoye_wa") or memo.get("aff|" + r["id"]): continue
        no = d.get("no") or r["id"]; o = offres.get(no, {})
        if o.get("tri") and int(o["tri"]) < ms() + 3 * 86400000: continue
        g = o.get("groupe") if o.get("groupe") in GROUPES else DEFAUT
        if memo.get(no + "|" + g): continue
        url = d.get("png") or ""
        if url.startswith("/_blob/"): url = SB + "/storage/v1/object/public/blobs/" + url[7:]
        if not url: continue
        try:
            with urllib.request.urlopen(url, timeout=60) as rr: png = rr.read()
        except Exception as ex: log("  affiche illisible %s : %s" % (r["id"], ex)); continue
        legende = (d.get("texte") or "")[:900] + ("\n\n" + MENU if g != "SPE Réunion agents" else "")
        deposer("pont_%d_aff_%s.json" % (ms(), re.sub(r"\W", "_", no)), {"groupe": g, "fichier_base64": base64.b64encode(png).decode(), "nom_fichier": "affiche_%s.png" % no, "legende": legende, "agent": "amine"}, a.essai)
        memo["aff|" + r["id"]] = t; memo[no + "|" + g] = t; n_aff += 1; envoyes += 1
        if not a.essai:
            sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "affiches", "id": r["id"], "data": dict(d, envoye_wa=t), "maj": t, "source": "robot_pont"}, prefer="resolution=merge-duplicates,return=minimal")
        time.sleep(2)
    if n_aff: log("%d affiche(s) validée(s) déposée(s)" % n_aff)
    for r, d, no in faits:
        if no: memo[no + "|" + groupe_de(d, offres)] = t
        if not a.essai:
            d2 = dict(d, statut="envoye", envoye_le=t, mode="pont_outbox")
            sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "file_whatsapp", "id": r["id"], "data": d2, "maj": t, "source": "robot_pont"}, prefer="resolution=merge-duplicates,return=minimal")
    if not a.essai:
        json.dump(memo, open(MEMO, "w", encoding="utf-8"))
        if envoyes:
            sb("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-robot_pont" % t, "maj": t, "source": "robot_pont",
                                       "data": {"t": t, "agent": "amine", "texte": "Robot pont : %d fichier(s) déposé(s) dans l'outbox WhatsApp (%d élément(s) de la file marqués envoyés)." % (envoyes, len(faits))}}, prefer="return=minimal")
    log("%d dépôt(s) outbox, %d élément(s) de file traités, %d en attente lus" % (envoyes, len(faits), len(rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
