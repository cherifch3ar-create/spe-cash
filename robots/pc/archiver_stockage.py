# -*- coding: utf-8 -*-
"""
Robot ARCHIVAGE SPE (sans IA) — sur le PC du bureau, toutes les 2 heures.
Décision du directeur du 15/11/2026 : « Option A » — le PC garde TOUS les fichiers, Supabase (forfait gratuit, 1 Go)
ne garde que ce qui sert encore.

Étapes :
 1. Liste les fichiers des buckets Supabase « appels-offres » et « blobs » (clé de service obligatoire).
 2. Copie chaque fichier absent sur le PC dans SPE_shared\\Archives\\supabase\\<bucket>\\<chemin>, puis contrôle la taille.
 3. Retire de Supabase SEULEMENT des fichiers dont la copie PC est contrôlée, dans cet ordre :
      a. dossiers d'offres dont la date limite est passée depuis plus de 2 jours ;
      b. fichiers déposés il y a plus de 60 jours ;
      c. zips « archives/ » (déjà copiés sur le PC) ;
      d. si Supabase dépasse encore le plafond (800 Mo par défaut) : les plus anciens dépôts d'abord.
    Jamais retirés : bucket « images-domaines », logos, dossiers d'offres dont la date limite est dans moins de 3 jours.
 4. Note chaque retrait dans Supabase « docs » collection « archives_pc » (chemin Supabase -> chemin PC) et une ligne « events ».

Usage : python archiver_stockage.py [--essai] [--plafond-mo 800] [--copie-seule]
  --essai       : n'écrit rien, ne retire rien, affiche le plan.
  --copie-seule : copie sur le PC sans rien retirer de Supabase.
Clé : variable d'environnement Windows SUPABASE_SERVICE_KEY (Supabase > Project Settings > API > service_role).
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
PUB = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
SERVICE = os.environ.get("SUPABASE_SERVICE_KEY", "")
SHARED = os.environ.get("SPE_SHARED", r"C:\Users\USER\Desktop\01_SPE\SPE_shared")
RACINE = os.path.join(SHARED, "Archives", "supabase")
JOURNAL = os.path.join(SHARED, "archivage_journal.txt")
BUCKETS = ["appels-offres", "blobs"]
JOUR = 86400 * 1000


def ms(): return int(time.time() * 1000)


def log(t):
    l = time.strftime("%Y-%m-%d %H:%M:%S ") + t
    print(l, flush=True)
    try:
        os.makedirs(SHARED, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f: f.write(l + "\n")
    except OSError: pass


def req(method, chemin, corps=None, cle=None, brut=False, prefer=None, timeout=120):
    cle = cle or SERVICE or PUB
    h = {"apikey": cle, "Authorization": "Bearer " + cle}
    if corps is not None: h["Content-Type"] = "application/json"
    if prefer: h["Prefer"] = prefer
    r = urllib.request.Request(SB + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h, method=method)
    with urllib.request.urlopen(r, timeout=timeout) as rep:
        b = rep.read()
        return b if brut else (json.loads(b) if b else None)


def lister(bucket, prefixe=""):
    """Liste récursive : renvoie [{chemin, taille, cree_ms}]."""
    sortie, offset = [], 0
    while True:
        lot = req("POST", "/storage/v1/object/list/" + bucket,
                  {"prefix": prefixe, "limit": 1000, "offset": offset, "sortBy": {"column": "name", "order": "asc"}})
        for o in lot or []:
            chemin = (prefixe + "/" if prefixe else "") + o["name"]
            if o.get("id") is None:  # dossier
                sortie += lister(bucket, chemin)
            else:
                m = o.get("metadata") or {}
                cree = o.get("created_at") or ""
                try: cree_ms = int(time.mktime(time.strptime(cree[:19], "%Y-%m-%dT%H:%M:%S")) * 1000)
                except ValueError: cree_ms = ms()
                sortie.append({"bucket": bucket, "chemin": chemin, "taille": int(m.get("size") or 0), "cree_ms": cree_ms})
        if not lot or len(lot) < 1000: break
        offset += 1000
    return sortie


def limites_offres():
    """N° d'offre -> date limite (epoch ms) depuis Supabase docs « offres »."""
    res, debut = {}, 0
    while True:
        lot = req("GET", "/rest/v1/docs?collection=eq.offres&select=id,data->>tri&order=id&offset=%d&limit=1000" % debut, cle=PUB)
        for r in lot or []:
            try: res[r["id"]] = int(float(r.get("tri") or 0)) or None
            except (TypeError, ValueError): res[r["id"]] = None
        if not lot or len(lot) < 1000: break
        debut += 1000
    return res


def chemin_pc(f): return os.path.join(RACINE, f["bucket"], *f["chemin"].split("/"))


def copier(f, essai):
    dest = chemin_pc(f)
    if os.path.exists(dest) and os.path.getsize(dest) == f["taille"]: return True
    if essai: return False
    q = urllib.parse.quote(f["chemin"])
    try:
        data = req("GET", "/storage/v1/object/%s/%s" % (f["bucket"], q), brut=True, timeout=600)
    except Exception as e:
        log("  copie impossible %s/%s : %s" % (f["bucket"], f["chemin"], e)); return False
    if len(data) != f["taille"]:
        log("  taille différente %s/%s (%d au lieu de %d)" % (f["bucket"], f["chemin"], len(data), f["taille"])); return False
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    with open(tmp, "wb") as h: h.write(data)
    os.replace(tmp, dest)
    return os.path.getsize(dest) == f["taille"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true")
    ap.add_argument("--copie-seule", action="store_true")
    ap.add_argument("--plafond-mo", type=int, default=800)
    a = ap.parse_args()
    if not SERVICE:
        log("ARRÊT : variable SUPABASE_SERVICE_KEY absente sur ce PC (nécessaire pour lister et retirer les fichiers).")
        return 2

    fichiers = []
    for b in BUCKETS: fichiers += lister(b)
    total = sum(f["taille"] for f in fichiers)
    log("Supabase : %d fichiers, %.0f Mo (plafond %d Mo)" % (len(fichiers), total / 1e6, a.plafond_mo))

    # 1-2. copie PC
    copies = 0
    for f in fichiers:
        f["pc_ok"] = copier(f, a.essai)
        copies += f["pc_ok"]
    log("Copie PC contrôlée : %d / %d fichiers dans %s" % (copies, len(fichiers), RACINE))
    if a.copie_seule: return 0

    # 3. choix des retraits
    lim, maint = limites_offres(), ms()
    def no_offre(f): return f["chemin"].split("/")[0] if f["bucket"] == "appels-offres" else None
    def protege(f):
        n = no_offre(f); t = lim.get(n) if n else None
        return bool(t and t > maint - 2 * JOUR and t < maint + 3 * JOUR) or "logo" in f["chemin"].lower()
    retraits, vus = [], set()
    def ajouter(f, raison):
        k = (f["bucket"], f["chemin"])
        if k in vus or not f["pc_ok"] or protege(f): return
        vus.add(k); f["raison"] = raison; retraits.append(f)
    for f in fichiers:
        n = no_offre(f); t = lim.get(n) if n else None
        if t and t < maint - 2 * JOUR: ajouter(f, "date limite passée")
    for f in fichiers:
        if f["cree_ms"] < maint - 60 * JOUR: ajouter(f, "plus de 60 jours")
    for f in fichiers:
        if f["bucket"] == "appels-offres" and f["chemin"].startswith("archives/"): ajouter(f, "zip d'archive copié sur le PC")
    reste = total - sum(f["taille"] for f in retraits)
    for f in sorted(fichiers, key=lambda x: x["cree_ms"]):
        if reste <= a.plafond_mo * 1e6: break
        if (f["bucket"], f["chemin"]) in vus: continue
        n = len(retraits); ajouter(f, "au-dessus du plafond")
        if len(retraits) > n: reste -= f["taille"]
    libere = sum(f["taille"] for f in retraits)
    log("Plan : retirer %d fichiers (%.0f Mo) ; Supabase passerait à %.0f Mo" % (len(retraits), libere / 1e6, (total - libere) / 1e6))
    if a.essai:
        for f in retraits[:40]: log("  (essai) %s/%s — %s" % (f["bucket"], f["chemin"], f["raison"]))
        return 0

    # 4. retrait par lots, puis trace
    faits = []
    for b in BUCKETS:
        lot = [f for f in retraits if f["bucket"] == b]
        for i in range(0, len(lot), 100):
            part = lot[i:i + 100]
            try:
                req("DELETE", "/storage/v1/object/" + b, {"prefixes": [f["chemin"] for f in part]})
                faits += part
            except Exception as e:
                log("  retrait impossible (%s, lot %d) : %s" % (b, i // 100, e))
    t = maint
    for i in range(0, len(faits), 200):
        lignes = [{"collection": "archives_pc", "id": (f["bucket"] + "/" + f["chemin"])[:200], "maj": t, "source": "robot_archivage",
                   "data": {"bucket": f["bucket"], "chemin": f["chemin"], "taille": f["taille"], "pc": chemin_pc(f),
                            "raison": f["raison"], "retire_le": t}} for f in faits[i:i + 200]]
        try: req("POST", "/rest/v1/docs", lignes, prefer="resolution=merge-duplicates,return=minimal")
        except Exception as e: log("  trace archives_pc impossible : %s" % e)
    texte = "Archivage PC — %d fichiers (%.0f Mo) copiés sur le PC puis retirés de Supabase ; Supabase : %.0f Mo." % (
        len(faits), sum(f["taille"] for f in faits) / 1e6, (total - sum(f["taille"] for f in faits)) / 1e6)
    try:
        req("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-archivage" % t, "maj": t, "source": "robot_archivage",
                                      "data": {"t": t, "agent": "archivage", "texte": texte}}, prefer="return=minimal")
    except Exception as e: log("  event impossible : %s" % e)
    log(texte)
    return 0


if __name__ == "__main__":
    sys.exit(main())
