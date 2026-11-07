# -*- coding: utf-8 -*-
"""
Wissem-Robot — téléchargement direct des cahiers des charges TUNEPS (sans IA).
Soft Power Elevation (SPE). Décision du directeur, 07/11/2026.

Le robot se branche sur le Chrome du PC bureau, déjà connecté à TUNEPS par le directeur
(Chrome ouvert avec Lancer-Chrome-SPE.bat). Il ne se connecte JAMAIS lui-même :
aucun mot de passe, aucun code PIN, jamais la clé TnTrust. Il ne dépose, ne signe et ne paie rien.

Usage :
  python wissem_robot.py              passage normal (priorites.txt puis offres de Supabase)
  python wissem_robot.py --essai      montre ce qu'il ferait, sans rien télécharger ni écrire
  python wissem_robot.py --max 5      limite le nombre d'offres
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import requests

ICI = Path(__file__).resolve().parent
CONFIG = json.loads((ICI / "config.json").read_text(encoding="utf-8"))
RACINE = Path(CONFIG["dossier_appels_offres"])
JOURNAL = Path(CONFIG["journal"])
SB_URL = CONFIG["supabase_url"].rstrip("/")
SB_CLE = CONFIG["supabase_cle_publique"]
SB_ENTETES = {"apikey": SB_CLE, "Authorization": "Bearer " + SB_CLE, "Content-Type": "application/json"}

EXTENSIONS = (".pdf", ".zip", ".rar", ".7z", ".doc", ".docx", ".xls", ".xlsx", ".odt", ".ods", ".jpg", ".jpeg", ".png", ".dwg")
MOTS_TELECHARGER = ("télécharger", "telecharger", "download", "تحميل", "cahier", "fiche de visite", "fiche visite", "avis", "dossier", "pièce", "piece", "annexe")
MOTS_CONNEXION = ("mot de passe", "password", "code pin", "tntrust", "certificat", "se connecter", "connexion", "authentification", "login")
MOTS_INACTIVITE = ("inactivité", "inactivite", "session va expirer", "session expire")


def maintenant_ms():
    return int(time.time() * 1000)


def journal(texte):
    ligne = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "  " + texte
    print(ligne)
    try:
        JOURNAL.parent.mkdir(parents=True, exist_ok=True)
        with open(JOURNAL, "a", encoding="utf-8") as f:
            f.write(ligne + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------- Supabase
def sb_lire_offre(no):
    r = requests.get(SB_URL + "/rest/v1/docs", headers=SB_ENTETES, timeout=30,
                     params={"select": "id,data", "collection": "eq.offres", "id": "eq." + no})
    r.raise_for_status()
    rows = r.json()
    return rows[0]["data"] if rows else None


def sb_offres_a_telecharger(maxi):
    """Offres actives (date limite dans le futur), pas fourniture seule, pas encore complètes."""
    r = requests.get(SB_URL + "/rest/v1/docs", headers=SB_ENTETES, timeout=60,
                     params={"select": "id,data", "collection": "eq.offres",
                             "data->>tri": "gt." + str(maintenant_ms()), "order": "data->tri.asc", "limit": "400"})
    r.raise_for_status()
    L = []
    for row in r.json():
        d = row.get("data") or {}
        lien = d.get("lien") or ""
        if "tuneps.tn" not in lien:
            continue
        if str(d.get("nature", "")).lower().startswith("fourniture"):
            continue
        if ((d.get("telechargement") or {}).get("statut")) == "complet":
            continue
        L.append({"no": d.get("no") or row["id"], "lien": lien, "limite": d.get("limite", "")})
        if len(L) >= maxi:
            break
    return L


def sb_ecrire(collection, doc_id, data, fusion=True):
    """Écrit un document dans public.docs (fusion avec l'existant si demandé)."""
    if fusion:
        try:
            r = requests.get(SB_URL + "/rest/v1/docs", headers=SB_ENTETES, timeout=30,
                             params={"select": "data", "collection": "eq." + collection, "id": "eq." + doc_id})
            r.raise_for_status()
            if r.json():
                ancien = r.json()[0]["data"] or {}
                ancien.update(data)
                data = ancien
        except requests.RequestException:
            pass
    corps = {"collection": collection, "id": doc_id, "data": data, "maj": maintenant_ms(), "source": "robot"}
    h = dict(SB_ENTETES, Prefer="resolution=merge-duplicates,return=minimal")
    r = requests.post(SB_URL + "/rest/v1/docs?on_conflict=collection,id", headers=h, json=corps, timeout=30)
    if r.status_code >= 300:
        journal("Supabase refuse l'écriture %s/%s : %s %s" % (collection, doc_id, r.status_code, r.text[:200]))
        return False
    return True


def event(texte, essai):
    journal("EVENT : " + texte)
    if not essai:
        t = maintenant_ms()
        sb_ecrire("events", "e-%d-robot_telechargement" % t, {"t": t, "agent": "robot_telechargement", "texte": texte}, fusion=False)


# ---------------------------------------------------------------- liste de travail
def lire_priorites():
    f = ICI / "priorites.txt"
    L = []
    if not f.exists():
        return L
    for ligne in f.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        morceaux = ligne.split()
        no = morceaux[0]
        lien = morceaux[1] if len(morceaux) > 1 else ""
        if not lien:
            try:
                d = sb_lire_offre(no) or {}
                lien = d.get("lien", "")
            except requests.RequestException:
                pass
        if lien:
            L.append({"no": no, "lien": lien, "limite": ""})
        else:
            journal("Priorité %s ignorée : lien TUNEPS inconnu (ajouter le lien sur la même ligne)" % no)
    return L


# ---------------------------------------------------------------- fichiers
def nom_libre(dossier, nom):
    nom = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", nom).strip() or "piece"
    p = dossier / nom
    if not p.exists():
        return p
    base, ext = os.path.splitext(nom)
    i = 2
    while (dossier / ("%s_%d%s" % (base, i, ext))).exists():
        i += 1
    return dossier / ("%s_%d%s" % (base, i, ext))


def fichier_ok(p):
    try:
        if p.stat().st_size == 0:
            return False
        tete = p.read_bytes()[:8]
        if p.suffix.lower() == ".pdf":
            return tete.startswith(b"%PDF")
        if p.suffix.lower() == ".zip":
            with zipfile.ZipFile(p) as z:
                return z.testzip() is None
        return True
    except (OSError, zipfile.BadZipFile):
        return False


def deja_presents(dossier):
    return {p.name for p in dossier.iterdir() if p.is_file() and not p.name.startswith("_")} if dossier.exists() else set()


# ---------------------------------------------------------------- TUNEPS
class Deconnecte(Exception):
    pass


def texte_page(page):
    try:
        return (page.inner_text("body", timeout=5000) or "").lower()
    except Exception:
        return ""


def fermer_inactivite(page):
    """Fenêtre d'inactivité : cliquer « Annuler » pour rester connecté."""
    t = texte_page(page)
    if any(m in t for m in MOTS_INACTIVITE):
        for nom in ("Annuler", "annuler", "Cancel"):
            try:
                b = page.get_by_role("button", name=nom)
                if b.count():
                    b.first.click(timeout=3000)
                    journal("Fenêtre d'inactivité : « Annuler » cliqué")
                    page.wait_for_timeout(1000)
                    return
            except Exception:
                pass


def verifier_connexion(page):
    """S'arrête si TUNEPS demande une connexion (jamais de saisie)."""
    try:
        if page.locator("input[type=password]").count():
            raise Deconnecte("TUNEPS demande un mot de passe")
    except Deconnecte:
        raise
    except Exception:
        pass
    url = page.url.lower()
    if any(m in url for m in ("login", "connexion", "authentification", "/auth")):
        raise Deconnecte("TUNEPS affiche la page de connexion")


def liens_pieces(page):
    """Repère les liens ou boutons qui téléchargent une pièce."""
    js = """() => Array.from(document.querySelectorAll('a,button,[onclick]')).map((e, i) => {
        e.setAttribute('data-spe-robot', String(i));
        return {i: String(i), tag: e.tagName.toLowerCase(), href: e.getAttribute('href') || '',
                txt: (e.innerText || e.getAttribute('title') || e.getAttribute('aria-label') || '').trim().slice(0, 160),
                dl: e.hasAttribute('download')};
    })"""
    cand = []
    for e in page.evaluate(js):
        href = e["href"].lower()
        txt = e["txt"].lower()
        if href.startswith("mailto:") or href.startswith("tel:"):
            continue
        par_ext = any(href.split("?")[0].endswith(x) for x in EXTENSIONS)
        par_mot = any(m in txt for m in MOTS_TELECHARGER) or "download" in href or "telecharg" in href or "fichier" in href
        if e["dl"] or par_ext or par_mot:
            # ne jamais cliquer sur ce qui ressemble à une action de dépôt, de connexion ou de paiement
            if any(m in txt for m in ("déposer", "deposer", "soumettre", "signer", "payer", "connexion", "se connecter", "inscription")):
                continue
            cand.append(e)
    return cand


def telecharger_offre(page, offre, essai, pause_s):
    no, lien = offre["no"], offre["lien"]
    dossier = RACINE / no
    journal("Offre %s : %s" % (no, lien))
    if essai:
        return {"statut": "essai"}
    page.goto(lien, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(2500)
    fermer_inactivite(page)
    verifier_connexion(page)

    cand = liens_pieces(page)
    dossier.mkdir(parents=True, exist_ok=True)
    presents = deja_presents(dossier)
    fichiers, manquants, fiche = [], [], None
    for e in cand:
        fermer_inactivite(page)
        verifier_connexion(page)
        loc = page.locator('[data-spe-robot="%s"]' % e["i"])
        try:
            with page.expect_download(timeout=45000) as attente:
                loc.first.click(timeout=10000)
            d = attente.value
            nom = d.suggested_filename or (e["txt"] or "piece") + ".pdf"
            if nom in presents:  # déjà téléchargé lors d'un passage précédent : ne pas écraser
                cible = dossier / nom
                d.cancel()
            else:
                cible = nom_libre(dossier, nom)
                d.save_as(str(cible))
            ok = fichier_ok(cible)
            fichiers.append({"nom": cible.name, "octets": cible.stat().st_size if cible.exists() else 0, "ok": ok, "lien_texte": e["txt"]})
            if re.search(r"visite", (e["txt"] + " " + cible.name).lower()):
                fiche = {"dossier_pc": str(cible), "t": maintenant_ms()}
            journal("  + %s (%s)" % (cible.name, "OK" if ok else "illisible"))
        except Deconnecte:
            raise
        except Exception as ex:
            # lien qui ouvre une page au lieu d'un fichier : on essaie de suivre le lien direct
            href = e["href"]
            if href and any(href.lower().split("?")[0].endswith(x) for x in EXTENSIONS):
                try:
                    url = urljoin(page.url, href)
                    rep = page.context.request.get(url, timeout=60000)
                    if rep.ok:
                        cible = nom_libre(dossier, url.split("/")[-1].split("?")[0])
                        cible.write_bytes(rep.body())
                        ok = fichier_ok(cible)
                        fichiers.append({"nom": cible.name, "octets": cible.stat().st_size, "ok": ok, "lien_texte": e["txt"]})
                        journal("  + %s (lien direct, %s)" % (cible.name, "OK" if ok else "illisible"))
                        continue
                except Exception:
                    pass
            manquants.append(e["txt"] or e["href"])
            journal("  - pas de fichier pour « %s » (%s)" % (e["txt"][:60], type(ex).__name__))
        time.sleep(pause_s)

    bons = [f for f in fichiers if f["ok"]]
    if not fichiers:
        statut = "introuvable"
        (dossier / "_page_tuneps.html").write_text(page.content(), encoding="utf-8")
    elif manquants or len(bons) < len(fichiers):
        statut = "incomplet"
    else:
        statut = "complet"
    resume = {"no": no, "lien": lien, "fichiers": fichiers, "manquants": manquants, "fiche_visite": fiche,
              "total": len(fichiers) + len(manquants), "telecharges": len(bons), "statut": statut, "t": maintenant_ms(), "par": "robot"}
    (dossier / "_pieces.json").write_text(json.dumps(resume, ensure_ascii=False, indent=2), encoding="utf-8")

    tel = {"total": resume["total"], "telecharges": len(bons), "manquants": manquants, "dossier_pc": str(dossier), "lien": lien,
           "statut": statut, "verifie_par": "robot", "maj": maintenant_ms()}
    if statut == "complet":
        tel["controle"] = {"ok": True, "par": "robot", "t": maintenant_ms()}
    champs = {"telechargement": tel, "pieces_telechargees": [f["nom"] for f in bons]}
    if fiche:
        champs["fiche_visite"] = fiche
    sb_ecrire("offres", no, champs)
    return resume


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--essai", action="store_true", help="ne télécharge et n'écrit rien")
    ap.add_argument("--max", type=int, default=CONFIG.get("max_offres", 15))
    args = ap.parse_args()

    liste = lire_priorites()
    vus = {o["no"] for o in liste}
    try:
        for o in sb_offres_a_telecharger(args.max * 3):
            if o["no"] not in vus:
                liste.append(o)
                vus.add(o["no"])
    except requests.RequestException as ex:
        journal("Supabase injoignable (%s) : seulement priorites.txt" % ex)
    liste = liste[: args.max]
    journal("Robot téléchargement : %d offre(s) à traiter%s" % (len(liste), " (ESSAI)" if args.essai else ""))
    if not liste:
        event("Robot téléchargement : aucune offre à télécharger", args.essai)
        return 0

    if args.essai:
        for o in liste:
            journal("  serait téléchargée : %s %s" % (o["no"], o["lien"]))
        return 0

    from playwright.sync_api import sync_playwright
    bilan = {"complet": 0, "incomplet": 0, "introuvable": 0, "fichiers": 0, "fiches": 0}
    with sync_playwright() as pw:
        try:
            navigateur = pw.chromium.connect_over_cdp("http://localhost:%d" % CONFIG.get("port_chrome", 9222), timeout=15000)
        except Exception:
            event("BESOIN — Robot téléchargement : Chrome n'est pas ouvert avec Lancer-Chrome-SPE.bat sur le PC bureau. "
                  "Geste : fermer Chrome, double-cliquer Lancer-Chrome-SPE.bat, puis relancer le robot.", False)
            return 2
        contexte = navigateur.contexts[0] if navigateur.contexts else navigateur.new_context()
        page = contexte.new_page()
        try:
            for o in liste:
                try:
                    r = telecharger_offre(page, o, False, CONFIG.get("pause_secondes", 3))
                    bilan[r["statut"]] += 1
                    bilan["fichiers"] += r["telecharges"]
                    bilan["fiches"] += 1 if r["fiche_visite"] else 0
                except Deconnecte as ex:
                    event("BESOIN — Robot téléchargement : %s. Geste : se reconnecter à TUNEPS dans la fenêtre Chrome du robot (Lancer-Chrome-SPE.bat) "
                          "(vous tapez vous-même le code), puis relancer le robot. Offres restantes : %s"
                          % (ex, ", ".join(x["no"] for x in liste[liste.index(o):])), False)
                    break
                except Exception as ex:
                    bilan["introuvable"] += 1
                    journal("Offre %s : erreur %s" % (o["no"], ex))
        finally:
            try:
                page.close()  # seulement notre onglet : Chrome reste ouvert
            except Exception:
                pass
    event("Robot téléchargement : %d offres, %d fichiers, %d complètes, %d incomplètes, %d introuvables, %d fiches de visite"
          % (len(liste), bilan["fichiers"], bilan["complet"], bilan["incomplet"], bilan["introuvable"], bilan["fiches"]), False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
