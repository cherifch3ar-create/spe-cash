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
    ("Ascenseurs", "appel d'offres ascenseur Tunisie"),
    ("Ascenseurs", "maintenance ascenseurs Tunisie"),
    ("Ascenseurs", "projet résidence immeuble Tunisie ascenseurs"),
    ("Électrique", "appel d'offres éclairage public Tunisie"),
    ("Électrique", "STEG appel d'offres travaux"),
    ("Surveillance, alarme, incendie", "appel d'offres vidéosurveillance Tunisie"),
    ("Portail", "portail automatique barrière appel d'offres Tunisie"),
    ("Chaud, froid, climatisation", "appel d'offres climatisation chauffage Tunisie"),
    ("Maritime", "port Tunisie travaux maintenance appel d'offres OMMP"),
    ("Mécanique", "maintenance industrielle Tunisie appel d'offres"),
    ("Nouveautés", "hôtel clinique hôpital nouveau projet Tunisie 2026"),
]


def rss(q):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": q + " when:7d", "hl": "fr", "gl": "TN", "ceid": "TN:fr"})
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


def main(essai=False):
    t = int(time.time() * 1000)
    trouves, erreurs = {}, 0
    for metier, q in RECHERCHES:
        try:
            for a in articles(rss(q)):
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
        for v in nouveaux.values():
            par.setdefault(v["metier"], []).append(v["titre"])
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
