# -*- coding: utf-8 -*-
"""
Pont AFFICHES -> WhatsApp (via la file d'Amine dans SPE Live).
Demande du directeur (15/11/2026) : « s'il y a des appels d'offres, les annonces par message écrit
et les affiches par WhatsApp » — sur le téléphone, pas seulement dans l'application.

Constat : le robot des affiches crée bien les affiches dans Supabase (collection « affiches »), mais Amine,
qui envoie sur WhatsApp, ne lit que la file « file_whatsapp » de SPE Live. Ce script fait le lien.

  python pont_affiches_spelive.py preparer [--max 5] [--sortie DOSSIER]
      Choisit les affiches à envoyer, télécharge chaque PNG, le réduit en JPEG léger (~200 Ko),
      découpe le base64 en parties de 180 000 caractères et écrit dans DOSSIER :
        lot_<k>.json   : liste d'écritures prêtes pour ArtifactData « batch » (3 affiches, 9 écritures par lot)
        plan.json      : [{no, doc_id, groupe, parts, octets}]
  python pont_affiches_spelive.py marquer --sortie DOSSIER
      Après écriture réussie dans SPE Live : note dans Supabase affiches/<N°>.envoye_wa = "en_file".

Règles : heures de silence 23 h - 7 h (Tunis) ; affiche robot sans contrôle bloquant en échec, ou affiche validée ;
offre encore ouverte (date limite dans plus de 24 h) ; jamais deux fois la même affiche (champ envoye_wa) ;
5 affiches au plus par passage, les dates limites les plus proches d'abord.
"""
import argparse, base64, io, json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
H = {"apikey": CLE, "Authorization": "Bearer " + CLE}
PART = 180000
TUNIS = timezone(timedelta(hours=1))
GROUPES = {"appel d'offre SPE", "AO SPE Électrique", "AO SPE Mécanique", "AO SPE Portail", "AO SPE Surveillance caméra et alarme",
           "AO SPE Métal construction", "AO SPE Peinture", "AO SPE Maritime", "AO SPE Engins, levage et hydraulique"}
PAR_METIER = {"Ascenseurs": "AO SPE Mécanique", "Portail": "AO SPE Portail", "Surveillance, alarme, incendie": "AO SPE Surveillance caméra et alarme",
              "Électrique": "AO SPE Électrique", "Variateurs et équipements industriels": "AO SPE Électrique", "Mécanique": "AO SPE Mécanique",
              "Métal construction": "AO SPE Métal construction", "Peinture": "AO SPE Peinture", "Maritime": "AO SPE Maritime",
              "Engins, levage et hydraulique": "AO SPE Engins, levage et hydraulique"}
DEFAUT = "appel d'offre SPE"


def ms(): return int(time.time() * 1000)


def get(chemin, brut=False):
    r = urllib.request.Request(SB + chemin, headers=H)
    with urllib.request.urlopen(r, timeout=120) as rep:
        b = rep.read()
        return b if brut else json.loads(b)


def patch_affiche(no, data):
    h = dict(H, **{"Content-Type": "application/json", "Prefer": "return=minimal"})
    # fusion jsonb côté client : relire, compléter, réécrire
    rows = get("/rest/v1/docs?collection=eq.affiches&id=eq.%s&select=data" % urllib.parse.quote(no))
    if not rows: return False
    d = rows[0]["data"]; d.update(data)
    r = urllib.request.Request(SB + "/rest/v1/docs?collection=eq.affiches&id=eq." + urllib.parse.quote(no),
                               data=json.dumps({"data": d, "maj": ms()}).encode(), headers=h, method="PATCH")
    urllib.request.urlopen(r, timeout=60).read()
    return True


def jpeg(png):
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if im.width > 1080: im = im.resize((1080, round(im.height * 1080 / im.width)))
    for q in (82, 72, 62):
        out = io.BytesIO(); im.save(out, "JPEG", quality=q, optimize=True, progressive=True)
        if out.tell() <= 330000: break
    return out.getvalue()


def legende(a, o):
    d = a.get("donnees") or {}
    lim = d.get("limite") or o.get("limite") or ""
    t = d.get("limite_t") or o.get("tri")
    j = ""
    if t:
        n = int((int(t) - ms()) // 86400000)
        j = " (J-%d)" % max(n, 0)
    lignes = ["Affiches SPE — Nouvel appel d'offres",
              (d.get("titre") or o.get("objet") or "").strip()[:220],
              "Acheteur : %s — %s" % (d.get("acheteur") or o.get("acheteur") or "à compléter", d.get("lieu") or o.get("gouvernorat") or "à compléter"),
              "Date limite : %s%s" % (lim or "à confirmer", j),
              "N° %s" % a.get("no")]
    if o.get("lien"): lignes.append(o["lien"])
    lignes.append("Répondez 2 + N° pour lancer l'étude.")
    return "\n".join(l for l in lignes if l)


def preparer(a):
    h = datetime.now(TUNIS).hour
    os.makedirs(a.sortie, exist_ok=True)
    for f in os.listdir(a.sortie):
        if f.startswith("lot_") or f == "plan.json": os.remove(os.path.join(a.sortie, f))
    if h >= 23 or h < 7:
        json.dump([], open(os.path.join(a.sortie, "plan.json"), "w")); print("heures de silence : rien à préparer"); return 0
    aff = get("/rest/v1/docs?collection=eq.affiches&select=id,data&limit=3000")
    nos = [r["id"] for r in aff]
    offres = {}
    for i in range(0, len(nos), 150):
        q = ",".join('"%s"' % n for n in nos[i:i + 150])
        for r in get("/rest/v1/docs?collection=eq.offres&select=id,data&id=in.(%s)" % urllib.parse.quote(q)):
            offres[r["id"]] = r["data"]
    maint, choix = ms(), []
    for r in aff:
        d = r["data"]; o = offres.get(r["id"], {})
        if d.get("envoye_wa"): continue
        ok_robot = d.get("cree_par") == "robot_affiches" and d.get("statut") == "brouillon" and \
            not any(c.get("bloquant") and not c.get("ok") for c in d.get("controles") or [])
        if not (ok_robot or d.get("statut") == "valide"): continue
        t = (d.get("donnees") or {}).get("limite_t") or o.get("tri")
        try: t = int(t)
        except (TypeError, ValueError): continue
        if t < maint + 86400000: continue
        if "expir" in str(o.get("statut", "")).lower() or o.get("exclu"): continue
        pid = d.get("png_id") or str(d.get("png", "")).rsplit("/", 1)[-1]
        if not pid: continue
        choix.append((t, r["id"], d, o, pid))
    choix.sort(key=lambda x: x[0])
    ecritures, plan = [], []
    for k, (t, no, d, o, pid) in enumerate(choix[:a.max]):
        try:
            png = get("/storage/v1/object/public/blobs/" + pid, brut=True)
            img = jpeg(png)
        except Exception as e:
            print("  affiche %s ignorée : %s" % (no, e)); continue
        b64 = base64.b64encode(img).decode()
        parts = [b64[i:i + PART] for i in range(0, len(b64), PART)]
        doc_id = "f-%d-affiches" % (maint + k)
        g = o.get("groupe") if o.get("groupe") in GROUPES else PAR_METIER.get(o.get("metier") or (d.get("donnees") or {}).get("domaine"), DEFAUT)
        for i, p in enumerate(parts, 1):
            ecritures.append({"op": "set", "collection": "pdf_parts", "doc_id": "%s_p%d" % (doc_id, i),
                              "data": {"base64": p, "partie": i, "total": len(parts)}})
        ecritures.append({"op": "set", "collection": "file_whatsapp", "doc_id": doc_id,
                          "data": {"t": maint + k, "agent": "affiches", "destinataire": g, "groupe": g, "copie": "",
                                   "type": "image", "nom_fichier": "%s.jpg" % no, "parts": len(parts),
                                   "url": SB + "/storage/v1/object/public/blobs/" + pid, "no": no,
                                   "texte": legende(dict(d, no=no), o), "priorite": 2, "statut": "en_attente", "essais": 0}})
        plan.append({"no": no, "doc_id": doc_id, "groupe": g, "parts": len(parts), "octets": len(img)})
    # 9 écritures = 3 affiches par lot : reste sous la limite de 1 Mo d'un « batch » ArtifactData
    for i in range(0, len(ecritures), 9):
        json.dump(ecritures[i:i + 9], open(os.path.join(a.sortie, "lot_%d.json" % (i // 9)), "w"), ensure_ascii=False)
    json.dump(plan, open(os.path.join(a.sortie, "plan.json"), "w"), ensure_ascii=False, indent=1)
    print("%d affiches candidates, %d préparées (%d écritures) dans %s" % (len(choix), len(plan), len(ecritures), a.sortie))
    return 0


def marquer(a):
    plan = json.load(open(os.path.join(a.sortie, "plan.json")))
    n = 0
    for p in plan:
        if patch_affiche(p["no"], {"envoye_wa": "en_file", "file_whatsapp": p["doc_id"], "en_file_le": ms()}): n += 1
    print("%d affiches marquées en_file" % n)
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["preparer", "marquer"])
    ap.add_argument("--max", type=int, default=5)
    ap.add_argument("--sortie", default="pont_affiches")
    a = ap.parse_args()
    sys.exit(preparer(a) if a.action == "preparer" else marquer(a))
