# -*- coding: utf-8 -*-
"""
Robot de veille SPE (sans IA, gratuit) — tourne sur GitHub Actions toutes les 3 heures, 24 h/24, même PC éteint.
Lit les fils publics Google Actualités (RSS) sur les métiers de SPE en Tunisie, garde les nouveautés,
les écrit dans l'application (Supabase : collection « opportunites », un point dans « journal », une ligne dans « events »).
Ne contacte personne, ne se connecte à rien, ne supprime rien.
"""
import hashlib, html, json, re, sys, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
H = {"apikey": CLE, "Authorization": "Bearer " + CLE, "Content-Type": "application/json"}

RECHERCHES = [
    # (métier, recherche, langue) — recherches courtes = plus de résultats
    ("Ascenseurs", "ascenseur Tunisie", "fr"),
    ("Ascenseurs", "ascenseurs maintenance Tunisie", "fr"),
    ("Appels d'offres", "appel d'offres Tunisie", "fr"),
    ("Appels d'offres", "طلب عروض تونس", "ar"),
    ("Appels d'offres", "صفقة عمومية صيانة تونس", "ar"),
    ("Électrique", "éclairage public Tunisie", "fr"),
    ("Électrique", "STEG travaux", "fr"),
    ("Surveillance, alarme, incendie", "vidéosurveillance Tunisie", "fr"),
    ("Portail", "portail automatique Tunisie", "fr"),
    ("Chaud, froid, climatisation", "climatisation Tunisie projet", "fr"),
    ("Maritime", "port Radès travaux", "fr"),
    ("Maritime", "OMMP Tunisie", "fr"),
    ("Nouveautés", "projet immobilier Tunisie", "fr"),
    ("Nouveautés", "nouvel hôpital Tunisie", "fr"),
    ("Nouveautés", "hôtel Tunisie rénovation", "fr"),
    ("Nouveautés", "مشروع بناء تونس مصعد", "ar"),
]


def rss(q, lang="fr"):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q + " when:14d", "hl": lang, "gl": "TN", "ceid": "TN:" + lang})
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SPE-veille)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def articles(xml_bytes):
    out = []
    root = ET.fromstring(xml_bytes)
    for it in root.iter("item"):
        titre = (it.findtext("title") or "").strip()
        lien = (it.findtext("link") or "").strip()
        date = (it.findtext("pubDate") or "").strip()
        src = it.find("source")
        source = (src.text or "").strip() if src is not None else ""
        resume = re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))
        resume = re.sub(r"\s+", " ", resume).strip()[:400]
        if titre and lien:
            out.append({"titre": titre, "lien": lien, "date_publication": date, "media": source, "resume": resume})
    return out


def sb(method, chemin, corps=None, extra=None):
    h = dict(H, **(extra or {}))
    data = json.dumps(corps).encode() if corps is not None else None
    req = urllib.request.Request(SB + chemin, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        t = r.read()
        return json.loads(t) if t else None


def deja_vus(ids):
    if not ids:
        return set()
    lst = ",".join('"%s"' % i for i in ids)
    rows = sb("GET", "/rest/v1/docs?select=id&collection=eq.opportunites&id=in.(" + urllib.parse.quote(lst, safe='",()') + ")")
    return {r["id"] for r in rows or []}


def ecrire(rows):
    for i in range(0, len(rows), 50):
        sb("POST", "/rest/v1/docs?on_conflict=collection,id", rows[i:i + 50],
           {"Prefer": "resolution=merge-duplicates,return=minimal"})


import os


def gemini_trier(articles_dict):
    """Si la clé GEMINI_API_KEY est présente (secret GitHub du directeur), Gemini note chaque nouveauté
    (pertinence 0-100 pour SPE) et écrit un résumé d'une ligne en français. Sans clé ou en cas d'erreur : rien ne change."""
    cle = os.environ.get("GEMINI_API_KEY", "").strip()
    if not cle or not articles_dict:
        return
    modele = os.environ.get("GEMINI_MODELE", "gemini-flash-latest")
    items = list(articles_dict.items())
    for i in range(0, len(items), 25):
        lot = items[i:i + 25]
        liste = "\n".join("%d. [%s] %s — %s" % (n, v["metier"], v["titre"], v.get("resume", "")[:200]) for n, (k, v) in enumerate(lot))
        consigne = ("Tu aides Soft Power Elevation (SPE), PME tunisienne de service : ascenseurs, électricité et éclairage public, "
                    "portails automatiques, vidéosurveillance et alarmes, climatisation, mécanique, maritime, construction métallique, peinture. "
                    "Pour chaque article, donne la pertinence pour trouver du travail ou des appels d'offres pour SPE (0 à 100) "
                    "et un résumé d'une ligne en français. Réponds UNIQUEMENT en JSON : [{\"n\":0,\"pertinence\":80,\"resume\":\"...\"}].\n\n" + liste)
        corps = {"contents": [{"parts": [{"text": consigne}]}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
        url = "https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent" % modele
        try:
            req = urllib.request.Request(url, data=json.dumps(corps).encode(), method="POST",
                                         headers={"Content-Type": "application/json", "x-goog-api-key": cle})
            with urllib.request.urlopen(req, timeout=60) as r:
                rep = json.loads(r.read())
            texte = rep["candidates"][0]["content"]["parts"][0]["text"]
            for e in json.loads(texte):
                k, v = lot[int(e["n"])]
                v["pertinence"] = int(e.get("pertinence", 0))
                v["resume_ia"] = str(e.get("resume", ""))[:300]
        except Exception as ex:
            print("Gemini indisponible pour ce lot :", type(ex).__name__)
            return


def main(essai=False):
    t = int(time.time() * 1000)
    trouves, erreurs = {}, 0
    for metier, q, lang in RECHERCHES:
        try:
            for a in articles(rss(q, lang)):
                k = "G-" + hashlib.sha1(a["lien"].encode()).hexdigest()[:16]
                if k not in trouves:
                    a.update({"metier": metier, "recherche": q})
                    trouves[k] = a
        except Exception as ex:  # une recherche en panne n'arrête pas les autres
            erreurs += 1
            print("recherche en échec :", q, ex)
        time.sleep(2)
    vus = deja_vus(list(trouves)) if trouves and not essai else set()
    nouveaux = {k: v for k, v in trouves.items() if k not in vus}
    gemini_trier(nouveaux)
    if any("pertinence" in v for v in nouveaux.values()):
        avant = len(nouveaux)
        nouveaux = {k: v for k, v in nouveaux.items() if v.get("pertinence", 100) >= int(os.environ.get("PERTINENCE_MIN", "40"))}
        print("Gemini : %d gardés sur %d" % (len(nouveaux), avant))
    print("articles lus :", len(trouves), "nouveaux :", len(nouveaux), "erreurs :", erreurs)
    if essai:
        for k, v in list(nouveaux.items())[:10]:
            print(" -", v["metier"], "|", v["titre"])
        return 0
    rows = [{"collection": "opportunites", "id": k, "maj": t, "source": "robot",
             "data": dict(v, t=t, titre=v["titre"], source="robot veille Google Actualités", statut="nouvelle",
                          type="veille_google")} for k, v in nouveaux.items()]
    if nouveaux:
        par = {}
        for v in sorted(nouveaux.values(), key=lambda x: -x.get("pertinence", 0)):
            par.setdefault(v["metier"], []).append(v.get("resume_ia") or v["titre"])
        lignes = ["🔎 Veille du %s : %d nouveauté(s) trouvée(s) par le robot" % (time.strftime("%d/%m %H:%M", time.gmtime(t / 1000 + 3600)), len(nouveaux))]
        for m, ts in par.items():
            lignes.append("• %s : %s" % (m, ts[0][:110] + (" (+%d)" % (len(ts) - 1) if len(ts) > 1 else "")))
        lignes.append("Détails dans Opportunités.")
        rows.append({"collection": "journal", "id": "J-veille-%d" % t, "maj": t, "source": "robot",
                     "data": {"t": t, "agent": "robot_veille", "type": "publication", "texte": "\n".join(lignes)}})
    rows.append({"collection": "events", "id": "e-%d-robot_veille" % t, "maj": t, "source": "robot",
                 "data": {"t": t, "agent": "robot_veille",
                          "texte": "Robot veille Google : %d articles lus, %d nouveautés, %d recherche(s) en échec" % (len(trouves), len(nouveaux), erreurs)}})
    ecrire(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main("--essai" in sys.argv))
