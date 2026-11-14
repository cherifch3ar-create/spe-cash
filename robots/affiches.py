# -*- coding: utf-8 -*-
"""
Robot AFFICHES SPE (sans IA, gratuit) — GitHub Actions toutes les heures, PC éteint.
Pour chaque offre active sans affiche, compose une affiche 1080×1350 (charte space-work/06) :
image du métier (stockage images-domaines), logo SPE, titre, acheteur, lieu, date limite, J-x.
La met en ligne dans le stockage « blobs » et crée « affiches »/<N°> en BROUILLON (même format que
l'application : png "/_blob/<id>", sig, texte, donnees, controles). La validation reste humaine.
Ne supprime rien, n'écrase jamais une affiche existante, n'envoie rien sur WhatsApp.
Usage : python robots/affiches.py [--max 10] [--essai] [--sortie dossier]
"""
import argparse, hashlib, io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
H = {"apikey": CLE, "Authorization": "Bearer " + CLE, "Content-Type": "application/json"}
ICI = os.path.dirname(os.path.abspath(__file__))
LOGO = os.path.join(ICI, "..", "live", "logo_blanc.png")
W, HT = 1080, 1350
NAVY = (14, 42, 71); GOLD = (201, 162, 39); WHITE = (255, 255, 255)

# métier (champ metier de l'offre, normalisé) -> image du stockage images-domaines + catégorie affichée
METIERS = [
    (("ascenseur", "monte-charge", "escalier mecanique"), "metier_ascenseurs.jpg", "ASCENSEURS ET MONTE-CHARGES"),
    (("portail", "porte automatique", "barriere", "rideau"), "metier_portails_automatiques.jpg", "PORTAILS ET BARRIÈRES"),
    (("surveillance", "camera", "alarme", "incendie", "interphone"), "metier_surveillance_alarme_incendie.jpg", "VIDÉOSURVEILLANCE ET ALARME"),
    (("variateur", "automate", "equipements industriels"), "metier_variateurs_equipements_industriels.jpg", "ÉQUIPEMENTS INDUSTRIELS"),
    (("electri", "eclairage", "cablage", "tableau"), "metier_electrique.jpg", "ÉLECTRICITÉ"),
    (("maritime", "navire", "port", "remorqueur"), "metier_maritime.jpg", "MARITIME"),
    (("engin", "levage", "hydraulique", "verin", "grue", "nacelle"), "metier_levage_hydraulique.jpg", "ENGINS, LEVAGE ET HYDRAULIQUE"),
    (("metal", "soudure", "serrurerie", "charpente"), "metier_construction_metallique.jpg", "CONSTRUCTION MÉTALLIQUE"),
    (("peinture", "revetement"), "metier_peinture.jpg", "PEINTURE"),
    (("blanchisserie", "buanderie"), "metier_blanchisserie.jpg", "BLANCHISSERIE"),
    (("mecanique", "moteur", "pompe", "compresseur", "froid", "climatisation", "voiture"), "metier_mecanique.jpg", "MÉCANIQUE"),
]
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def log(t): print(time.strftime("%H:%M:%S"), t, flush=True)
def ms(): return int(time.time() * 1000)
def nrm(s): return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()


def sb(method, chemin, corps=None, prefer=None, binaire=None, ctype=None):
    h = dict(H)
    if prefer: h["Prefer"] = prefer
    if ctype: h["Content-Type"] = ctype
    data = binaire if binaire is not None else (json.dumps(corps).encode("utf-8") if corps is not None else None)
    req = urllib.request.Request(SB + chemin, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read()
        return r.status, (json.loads(b) if b and b[:1] in (b"[", b"{") else b)


def police(taille, gras=True):
    for f in (FONTS if gras else FONTS[::-1]):
        if os.path.exists(f):
            return ImageFont.truetype(f, taille)
    return ImageFont.load_default()


def sans_arabe(s):
    """Garde la partie française d'un objet bilingue (« Objet (الموضوع) »)."""
    s = re.sub(r"[؀-ۿݐ-ݿ]+", "", str(s or ""))
    s = re.sub(r"\(\s*\)", "", s)
    return re.sub(r"\s+", " ", s).strip(" -–—:") or str(s or "")


def metier_de(offre):
    t = nrm((offre.get("metier") or "") + " " + (offre.get("groupe") or "") + " " + (offre.get("objet") or ""))
    for cles, img, cat in METIERS:
        if any(c in t for c in cles):
            return img, cat
    return "metier_mecanique.jpg", "APPEL D'OFFRES"


def image_metier(nom, cache={}):
    if nom in cache: return cache[nom].copy()
    url = SB + "/storage/v1/object/public/images-domaines/" + nom
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SPE-affiches"}), timeout=60) as r:
        im = Image.open(io.BytesIO(r.read())).convert("RGB")
    cache[nom] = im
    return im.copy()


def couvrir(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))


def lignes(draw, texte, font, largeur, maxl=3):
    mots, out, cur = texte.split(), [], ""
    for m in mots:
        t = (cur + " " + m).strip()
        if draw.textlength(t, font=font) <= largeur: cur = t
        else:
            if cur: out.append(cur)
            cur = m
    if cur: out.append(cur)
    if len(out) > maxl:
        out = out[:maxl]; out[-1] = out[-1][:max(0, len(out[-1]) - 1)].rstrip() + "…"
    return out


def jours(offre):
    tri = offre.get("tri")
    try: return max(0, int((int(tri) - ms()) / 86400000 + 0.999)) if tri else None
    except Exception: return None


def composer(offre):
    img_nom, categorie = metier_de(offre)
    fond = couvrir(image_metier(img_nom), W, HT)
    # voile sombre en bas pour la lisibilité (charte : texte blanc sur zone sombre)
    voile = Image.new("RGBA", (W, HT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(voile)
    for i in range(520):
        a = int(230 * (i / 520) ** 1.6)
        vd.line([(0, HT - 520 + i), (W, HT - 520 + i)], fill=(8, 20, 40, a))
    fond = Image.alpha_composite(fond.convert("RGBA"), voile)
    d = ImageDraw.Draw(fond)
    # panneau logo bleu arrondi en haut à gauche (charte critère 5)
    d.rounded_rectangle([44, 44, 44 + 360, 44 + 150], radius=22, fill=NAVY + (235,))
    if os.path.exists(LOGO):
        lg = Image.open(LOGO).convert("RGBA")
        r = min(300 / lg.width, 110 / lg.height)
        lg = lg.resize((int(lg.width * r), int(lg.height * r)), Image.LANCZOS)
        fond.alpha_composite(lg, (44 + (360 - lg.width) // 2, 44 + (150 - lg.height) // 2))
    else:
        d.text((70, 80), "SPE", font=police(72), fill=WHITE)
        d.text((70, 150), "SOFT POWER ELEVATION", font=police(22, False), fill=WHITE)
    # bandeau date limite / J-x en haut à droite
    j = jours(offre)
    etiq = ("J-%d" % j) if j is not None else "DATE À CONFIRMER"
    f = police(44)
    tw = d.textlength(etiq, font=f)
    d.rounded_rectangle([W - 44 - tw - 48, 60, W - 44, 60 + 84], radius=16, fill=(201, 162, 39, 240) if (j is not None and j <= 7) else NAVY + (235,))
    d.text((W - 44 - tw - 24, 76), etiq, font=f, fill=NAVY if (j is not None and j <= 7) else WHITE)
    # textes du bas (charte critère 6) : titre, acheteur · lieu, catégorie soulignée d'or
    titre = sans_arabe(offre.get("objet") or "")
    if len(titre) < 8:  # objet en arabe seulement : titre français générique (pas de rendu arabe sans police adaptée)
        titre = "Appel d'offres — " + categorie.capitalize()
    lieu = offre.get("gouvernorat") or offre.get("lieu") or ""
    if nrm(lieu).startswith("a confirmer") or not lieu: lieu = "Tunisie"
    y = HT - 470
    ft = police(50)
    for l in lignes(d, titre, ft, W - 120, 3):
        d.text(((W - d.textlength(l, font=ft)) / 2, y), l, font=ft, fill=WHITE); y += 62
    y += 10
    fs = police(34, False)
    sous = " · ".join([x for x in [sans_arabe(offre.get("acheteur") or "") or "Acheteur public", lieu] if x])
    for l in lignes(d, sous, fs, W - 140, 2):
        d.text(((W - d.textlength(l, font=fs)) / 2, y), l, font=fs, fill=(230, 236, 245)); y += 44
    lim = offre.get("limite") or ""
    if lim:
        fl = police(36)
        t = "Date limite : " + str(lim).replace(" ", " à ", 1) if re.match(r"\d\d/\d\d/\d{4} \d", str(lim)) else "Date limite : " + str(lim)
        d.text(((W - d.textlength(t, font=fl)) / 2, y + 6), t, font=fl, fill=(255, 226, 150)); y += 60
    fc = police(30)
    cat = " ".join(categorie)  # capitales espacées
    cw = d.textlength(cat, font=fc)
    d.text(((W - cw) / 2, HT - 118), cat, font=fc, fill=WHITE)
    d.line([((W - cw) / 2, HT - 70), ((W + cw) / 2, HT - 70)], fill=GOLD, width=4)
    out = io.BytesIO(); fond.convert("RGB").save(out, "PNG", optimize=True)
    return out.getvalue(), categorie


def offres_sans_affiche(maxi):
    st, offres = sb("GET", "/rest/v1/docs?collection=eq.offres&select=id,data&data-%3E%3Etri=gt." + str(ms()) + "&order=data-%3Etri.asc&limit=400")
    st, aff = sb("GET", "/rest/v1/docs?collection=eq.affiches&select=id&limit=2000")
    deja = {a["id"] for a in aff}
    out = []
    for row in offres:
        d = row.get("data") or {}
        no = str(d.get("no") or row["id"])
        if no in deja or no.lower() in deja: continue
        if nrm(d.get("nature", "")).replace("_", " ").startswith("fourniture seule"): continue
        if "expir" in nrm(d.get("statut", "")) or d.get("exclu"): continue
        out.append(d if d.get("no") else dict(d, no=no))
    return out[:maxi]


def publier(offre, png, categorie, essai, sortie):
    no = str(offre["no"])
    pid = hashlib.md5(png).hexdigest()
    if sortie:
        os.makedirs(sortie, exist_ok=True)
        open(os.path.join(sortie, re.sub(r"\W", "_", no) + ".png"), "wb").write(png)
    if essai: return "essai"
    st, _ = sb("POST", "/storage/v1/object/blobs/" + pid, binaire=png, ctype="image/png")
    t = ms(); j = jours(offre)
    lim = offre.get("limite") or ""
    texte = ("Opportunité d'appel d'offres — %s\n%s\nRéférence : %s\nLieu : %s\nDate limite : %s\nDomaine : %s\n"
             "SPE vous accompagne : analyse du cahier des charges, étude technique et financière, préparation du dossier et accompagnement jusqu'au dépôt.\n"
             "Répondez OUI pour lancer l'étude.\nSoft Power Elevation — votre partenaire pour les marchés publics en Tunisie."
             % (offre.get("acheteur", ""), offre.get("objet", ""), no, offre.get("gouvernorat") or offre.get("lieu") or "à compléter", lim, offre.get("metier") or categorie.title()))
    doc = {"t": t, "no": no, "pdf": "", "png": "/_blob/" + pid, "png_id": pid, "statut": "brouillon", "cree_le": t, "cree_par": "robot_affiches",
           "version": 1, "bloquant": False, "modifs": {}, "historique": [], "valide_le": 0, "valide_par": "",
           "sig": "|".join([no, str(offre.get("objet", "")), str(offre.get("acheteur", "")), str(offre.get("gouvernorat", "")), "", lim, str(offre.get("type", "")), str(offre.get("metier", ""))]),
           "texte": texte,
           "donnees": {"no": no, "titre": offre.get("objet", ""), "acheteur": offre.get("acheteur", ""), "lieu": offre.get("gouvernorat") or offre.get("lieu") or "",
                        "limite": lim, "limite_t": offre.get("tri"), "domaine": offre.get("metier") or categorie.title(), "procedure": offre.get("type", ""), "verifie": True, "modifs": []},
           "controles": [{"k": "logo", "ok": True, "txt": "Logo SPE sur l'affiche", "bloquant": True},
                         {"k": "offre", "ok": True, "txt": "Affiche liée à l'offre N° %s uniquement" % no, "bloquant": False},
                         {"k": "date", "ok": j is not None, "txt": "Date limite %s" % (lim or "à confirmer"), "bloquant": False},
                         {"k": "photo", "ok": True, "txt": "Image du métier (stockage images-domaines)", "bloquant": False}]}
    sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "affiches", "id": no, "data": doc, "maj": t, "source": "robot_affiches"},
       prefer="resolution=ignore-duplicates,return=minimal")
    return "brouillon"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max", type=int, default=10); ap.add_argument("--essai", action="store_true"); ap.add_argument("--sortie", default="")
    a = ap.parse_args()
    L = offres_sans_affiche(a.max)
    log("%d offre(s) sans affiche à traiter" % len(L))
    n, err = 0, 0
    for o in L:
        try:
            png, cat = composer(o)
            r = publier(o, png, cat, a.essai, a.sortie)
            log("  + %s — %s (%s, %d Ko)" % (o["no"], cat, r, len(png) // 1024)); n += 1
        except Exception as ex:
            err += 1; log("  - %s : %s" % (o.get("no"), ex))
        time.sleep(1)
    if L and not a.essai:
        t = ms()
        sb("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-robot_affiches" % t, "maj": t, "source": "robot_affiches",
                                   "data": {"t": t, "agent": "affiches", "texte": "Robot affiches : %d affiche(s) créée(s) en brouillon (à valider dans le Centre d'approbation), %d erreur(s)." % (n, err)}},
           prefer="return=minimal")
    return 0


if __name__ == "__main__":
    sys.exit(main())
