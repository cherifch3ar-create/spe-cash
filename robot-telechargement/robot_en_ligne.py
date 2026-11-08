# -*- coding: utf-8 -*-
"""
Robot en ligne SPE — téléchargement des pièces TUNEPS sans PC et sans connexion TUNEPS.
Tourne sur GitHub Actions (toutes les heures). Aucune IA, aucun mot de passe.

Il utilise uniquement la partie publique de TUNEPS :
  liste des pièces  : /api2/ged/spShopAttachFile/getByShopNo?shopNo=S...  (consultations)
                      /api2/ged//vAttachFile/getByBidNo?bidNo=2026...       (appels d'offres)
  fichier           : /api2/ged/document/downloadFile?noderef=...
Il ne dépose, ne signe, ne paie et ne supprime rien. Il ne remplace jamais un fichier déjà en ligne.

Usage : python robot_en_ligne.py [--max 25] [--essai]
"""
import argparse
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests

ICI = Path(__file__).resolve().parent
CONFIG = json.loads((ICI / "config.json").read_text(encoding="utf-8"))
SB_URL = CONFIG["supabase_url"].rstrip("/")
SB_CLE = CONFIG["supabase_cle_publique"]
BUCKET = CONFIG.get("bucket", "appels-offres")
SB = {"apikey": SB_CLE, "Authorization": "Bearer " + SB_CLE, "Content-Type": "application/json"}
TUNEPS = "https://www.tuneps.tn"
CA = os.environ.get("TUNEPS_CA")  # chaîne de certificats complétée (TUNEPS n'envoie pas son certificat intermédiaire)
VERIF = CA if CA and Path(CA).exists() else True
TN = requests.Session()
TN.headers.update({"User-Agent": "Mozilla/5.0 (SPE robot en ligne)", "Accept": "application/json, text/plain, */*",
                   "Referer": TUNEPS + "/portail/offres"})
PAUSE = float(CONFIG.get("pause_secondes", 3))


def ms():
    return int(time.time() * 1000)


def log(t):
    print(time.strftime("%H:%M:%S"), t, flush=True)


# ------------------------------------------------------------------ Supabase
def sb_get(collection, doc_id):
    r = requests.get(SB_URL + "/rest/v1/docs", headers=SB, timeout=30,
                     params={"select": "data", "collection": "eq." + collection, "id": "eq." + doc_id})
    r.raise_for_status()
    j = r.json()
    return (j[0]["data"] or {}) if j else None


def sb_ecrire(collection, doc_id, champs, fusion=True):
    data = dict(champs)
    if fusion:
        ancien = sb_get(collection, doc_id) or {}
        ancien.update(data)
        data = ancien
    h = dict(SB, Prefer="resolution=merge-duplicates,return=minimal")
    r = requests.post(SB_URL + "/rest/v1/docs?on_conflict=collection,id", headers=h, timeout=30,
                      json={"collection": collection, "id": doc_id, "data": data, "maj": ms(), "source": "robot_en_ligne"})
    if r.status_code >= 300:
        log("Supabase refuse %s/%s : %s %s" % (collection, doc_id, r.status_code, r.text[:200]))
        return False
    return True


def event(texte, essai):
    log("EVENT : " + texte)
    if not essai:
        t = ms()
        sb_ecrire("events", "e-%d-robot_en_ligne" % t, {"t": t, "agent": "robot_telechargement", "texte": texte}, fusion=False)


def priorites():
    f = ICI / "priorites.txt"
    if not f.exists():
        return []
    L = []
    for ligne in f.read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*([A-Za-z]?\d{8,})", ligne)
        if m and not ligne.strip().startswith("#"):
            L.append(m.group(1).upper())
    return L


def offres_a_faire(maxi):
    """Priorités d'abord, puis offres actives (date limite future) non complètes, sauf fourniture seule."""
    L, vus = [], set()
    for no in priorites():
        d = sb_get("offres", no) or {"no": no}
        if ((d.get("telechargement") or {}).get("statut")) != "complet":
            L.append(no)
            vus.add(no)
    r = requests.get(SB_URL + "/rest/v1/docs", headers=SB, timeout=60,
                     params={"select": "id,data", "collection": "eq.offres", "data->>tri": "gt." + str(ms()),
                             "order": "data->tri.asc", "limit": "500"})
    r.raise_for_status()
    for row in r.json():
        d = row.get("data") or {}
        no = str(d.get("no") or row["id"]).upper()
        if no in vus or "tuneps.tn" not in (d.get("lien") or "tuneps.tn"):
            continue
        if str(d.get("nature", "")).lower().replace("_", " ").startswith("fourniture seule"):
            continue
        if ((d.get("telechargement") or {}).get("statut")) == "complet":
            continue
        L.append(no)
        vus.add(no)
    return L[:maxi]


# ------------------------------------------------------------------ TUNEPS (partie publique)
def liste_pieces(no):
    adresses = ["/api2/ged/spShopAttachFile/getByShopNo?shopNo=" + no, "/api2/ged//vAttachFile/getByBidNo?bidNo=" + no]
    if not no.startswith("S"):
        adresses.reverse()
    for a in adresses:
        try:
            r = TN.get(TUNEPS + a, timeout=40, verify=VERIF)
            j = r.json()
        except (requests.RequestException, ValueError) as ex:
            log("  liste %s : %s" % (a.split("?")[0], type(ex).__name__))
            continue
        p = j.get("payload")
        if str(j.get("code")) == "200" and isinstance(p, list) and p:
            out = []
            for x in p:
                ref = next((v for k, v in x.items() if "noderef" in k.lower() and v), None)
                if ref:
                    out.append({"nom": x.get("fileNm") or "piece.pdf", "ref": ref, "type": x.get("cdNmFr") or "", "code": x.get("docCd") or ""})
            if out:
                return out
    return []


def telecharger(ref):
    r = TN.get(TUNEPS + "/api2/ged/document/downloadFile", params={"noderef": ref}, timeout=120, verify=VERIF)
    r.raise_for_status()
    return r.content


def fichier_ok(octets, nom):
    if len(octets) < 200:
        return False
    tete = octets[:8]
    if nom.lower().endswith(".pdf"):
        return tete.startswith(b"%PDF")
    return not tete.lstrip().lower().startswith((b"<!doc", b"<html", b"{"))


def envoyer(no, nom, octets):
    propre = re.sub(r"[^A-Za-z0-9._-]", "_", nom)
    cle = "%s/%s" % (re.sub(r"[^A-Za-z0-9._-]", "_", no), propre)
    pub = "%s/storage/v1/object/public/%s/%s" % (SB_URL, BUCKET, quote(cle))
    h = {"apikey": SB_CLE, "Authorization": "Bearer " + SB_CLE,
         "Content-Type": mimetypes.guess_type(propre)[0] or "application/octet-stream"}
    r = requests.post("%s/storage/v1/object/%s/%s" % (SB_URL, BUCKET, quote(cle)), headers=h, data=octets, timeout=180)
    if r.status_code < 300 or r.status_code == 409 or "exists" in r.text.lower():
        return pub
    log("  stockage refusé pour %s : %s %s" % (propre, r.status_code, r.text[:150]))
    return None


def traiter(no, essai):
    pieces = liste_pieces(no)
    if not pieces:
        log("Offre %s : aucune pièce publique" % no)
        if not essai:
            sb_ecrire("offres", no, {"telechargement": {"statut": "introuvable", "par": "robot_en_ligne", "maj": ms(),
                                                         "total": 0, "telecharges": 0, "fichiers_en_ligne": []}})
        return "introuvable", 0
    log("Offre %s : %d pièce(s)" % (no, len(pieces)))
    if essai:
        for p in pieces:
            log("  (essai) %s — %s" % (p["nom"], p["type"]))
        return "essai", 0
    en_ligne, manquants, fiche = [], [], None
    for p in pieces:
        try:
            octets = telecharger(p["ref"])
            if not fichier_ok(octets, p["nom"]):
                raise ValueError("fichier illisible (%d octets)" % len(octets))
            url = envoyer(no, p["nom"], octets)
            if not url:
                raise ValueError("copie en ligne refusée")
            en_ligne.append({"nom": p["nom"], "url": url, "type": p["type"], "octets": len(octets)})
            if "visite" in p["nom"].lower() and not fiche:
                fiche = {"url": url, "t": ms(), "par": "robot_en_ligne"}
            log("  + %s (%d Ko)" % (p["nom"], len(octets) // 1024))
        except Exception as ex:
            manquants.append(p["nom"])
            log("  - %s : %s" % (p["nom"], ex))
        time.sleep(PAUSE)
    statut = "complet" if en_ligne and not manquants else ("incomplet" if en_ligne else "erreur")
    tel = {"total": len(pieces), "telecharges": len(en_ligne), "manquants": manquants, "statut": statut,
           "verifie_par": "robot_en_ligne", "par": "robot_en_ligne", "maj": ms(), "fichiers_en_ligne": en_ligne}
    if statut == "complet":
        tel["controle"] = {"ok": True, "par": "robot_en_ligne", "t": ms()}
    champs = {"telechargement": tel, "pieces_telechargees": [f["nom"] for f in en_ligne]}
    if fiche:
        champs["fiche_visite"] = fiche
    sb_ecrire("offres", no, champs)
    return statut, len(en_ligne)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=25)
    ap.add_argument("--essai", action="store_true")
    a = ap.parse_args()
    nos = offres_a_faire(a.max)
    log("%d offre(s) à traiter" % len(nos))
    bilan = {"complet": 0, "incomplet": 0, "introuvable": 0, "erreur": 0, "essai": 0}
    fichiers = 0
    for no in nos:
        try:
            st, n = traiter(no, a.essai)
        except Exception as ex:
            log("Offre %s : %s" % (no, ex))
            st, n = "erreur", 0
        bilan[st] = bilan.get(st, 0) + 1
        fichiers += n
    if nos and not a.essai:
        event("Robot en ligne : %d fichier(s) mis en ligne pour %d offre(s) — %d complète(s), %d incomplète(s), %d sans pièce publique, %d en erreur."
              % (fichiers, len(nos), bilan["complet"], bilan["incomplet"], bilan["introuvable"], bilan["erreur"]), a.essai)
    return 0


if __name__ == "__main__":
    sys.exit(main())
