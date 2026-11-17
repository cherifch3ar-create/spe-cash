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
# Polices : PC Windows d'abord (Segoe UI / Arial), puis Linux (GitHub Actions). Sans police, l'affiche serait illisible.
FONTS_GRAS = [r"C:\Windows\Fonts\seguibl.ttf", r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]
FONTS_NORMAL = [r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
FONTS_SYMB = [r"C:\Windows\Fonts\seguisym.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
FONTS = FONTS_GRAS + FONTS_NORMAL
LOGO_NOIR = os.path.join(ICI, "..", "live", "logo_noir.png")


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


def police(taille, gras=True, liste=None):
    for f in (liste or (FONTS_GRAS if gras else FONTS_NORMAL)):
        if os.path.exists(f):
            return ImageFont.truetype(f, taille)
    return ImageFont.load_default()


def sans_arabe(s):
    """Garde la partie française d'un texte bilingue ; vide si le texte est seulement en arabe."""
    s2 = re.sub(r"[\u0600-\u06FF\u0750-\u077F\uFE70-\uFEFF]+", "", str(s or ""))
    s2 = re.sub(r"\(\s*\)", "", s2)
    return re.sub(r"\s+", " ", s2).strip(" -–—:·,")


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
    mots, out, cur = [m for m in texte.split(" ") if m], [], ""  # coupe seulement sur les espaces normales (pas les insécables)
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


def composer_photo(offre):
    """Ancien modèle (photo du métier + voile). Gardé : --modele photo."""
    img_nom, categorie = metier_de(offre)
    fond = couvrir(image_metier(img_nom), W, HT)
    # voile sombre en bas pour la lisibilité (charte : texte blanc sur zone sombre)
    voile = Image.new("RGBA", (W, HT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(voile)
    for i in range(640):
        a = int(245 * (i / 640) ** 1.3)
        vd.line([(0, HT - 640 + i), (W, HT - 640 + i)], fill=(8, 20, 40, a))
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


BLEU_FONCE = (16, 42, 77); BLEU_VIF = (35, 128, 226); BLEU_CLAIR = (91, 178, 255)
ROUGE = (204, 32, 39); GRIS_FOND = (241, 244, 248); GRIS_TXT = (90, 102, 120); LIGNE = (226, 231, 238)


def _logo_boite(fond, box, rayon):
    d = ImageDraw.Draw(fond)
    d.rounded_rectangle(box, radius=rayon, fill=WHITE)
    x0, y0, x1, y1 = box
    if os.path.exists(LOGO_NOIR):
        lg = Image.open(LOGO_NOIR).convert("RGBA")
        r = min((x1 - x0 - 30) / lg.width, (y1 - y0 - 20) / lg.height)
        lg = lg.resize((int(lg.width * r), int(lg.height * r)), Image.LANCZOS)
        fond.alpha_composite(lg, (x0 + (x1 - x0 - lg.width) // 2, y0 + (y1 - y0 - lg.height) // 2))
    else:
        f = police(int((y1 - y0) * 0.45))
        d.text((x0 + 20, y0 + 10), "SPE", font=f, fill=BLEU_FONCE)


def _centre(d, y, texte, font, fill, largeur=W):
    d.text(((largeur - d.textlength(texte, font=font)) / 2, y), texte, font=font, fill=fill)


def composer(offre, modele="carte"):
    """Modèle « carte » demandé par le directeur (15/11/2026, affiche du 30/10 « je veux comme ça ») :
    en-tête bleu foncé avec logo, bandeau du domaine, titre, tableau Référence / Acheteur / Lieu / Date limite (rouge,
    « dans N jours ») / Domaine / Procédure, 4 services cochés, bouton « Répondez OUI », pied de page."""
    if modele == "photo": return composer_photo(offre)
    _, categorie = metier_de(offre)
    fond = Image.new("RGBA", (W, HT), GRIS_FOND + (255,))
    d = ImageDraw.Draw(fond)
    # en-tête
    d.rectangle([0, 0, W, 170], fill=BLEU_FONCE)
    _logo_boite(fond, (40, 28, 330, 142), 18)
    f1 = police(40); f2 = police(26, False)
    t1 = "OPPORTUNITÉ D'APPEL D'OFFRES"
    while d.textlength(t1, font=f1) > W - 380 and f1.size > 26: f1 = police(f1.size - 2)
    d.text((360, 50), t1, font=f1, fill=WHITE)
    d.text((360, 104), "MARCHÉS PUBLICS — TUNISIE", font=f2, fill=BLEU_CLAIR)
    d.rectangle([0, 170, W, 177], fill=BLEU_VIF)
    # bandeau du domaine (dégradé + rayures)
    y0, y1 = 177, 440
    for i in range(W):
        c = tuple(int(BLEU_FONCE[k] + (BLEU_VIF[k] - BLEU_FONCE[k]) * (0.35 + 0.65 * i / W)) for k in range(3))
        d.line([(i, y0), (i, y1)], fill=c)
    ray = Image.new("RGBA", (W, HT), (0, 0, 0, 0)); rd = ImageDraw.Draw(ray)
    for x in range(-400, W + 400, 26):
        rd.line([(x, y1), (x + (y1 - y0), y0)], fill=(255, 255, 255, 20), width=2)
    fond = Image.alpha_composite(fond, ray)
    d = ImageDraw.Draw(fond)
    domaine = sans_arabe(offre.get("metier") or "") or categorie.capitalize()
    fd = police(58)
    ls = lignes(d, domaine, fd, W - 140, 3)
    while len(ls) > 2 and fd.size > 36:
        fd = police(fd.size - 4); ls = lignes(d, domaine, fd, W - 140, 3)
    y = (y0 + y1) // 2 - len(ls) * (fd.size + 12) // 2
    for l in ls:
        _centre(d, y, l, fd, WHITE); y += fd.size + 12
    # titre
    titre = sans_arabe(offre.get("objet") or "")
    if len(titre) < 8: titre = "Appel d'offres — " + categorie.capitalize()
    ft = police(46)
    lt = lignes(d, titre, ft, W - 100, 3)
    while len(lt) > 2 and ft.size > 34:
        ft = police(ft.size - 2); lt = lignes(d, titre, ft, W - 100, 3)
    y = 470
    for l in lt:
        d.text((50, y), l, font=ft, fill=BLEU_FONCE); y += ft.size + 10
    # tableau
    y += 14
    no = str(offre.get("no") or "")
    lieu = offre.get("gouvernorat") or offre.get("lieu") or ""
    if not lieu or nrm(lieu).startswith("a confirmer"): lieu = "à confirmer"
    lim = str(offre.get("limite") or "")
    lim_aff = lim.replace(" ", " à ", 1) if re.match(r"\d\d/\d\d/\d{4} \d", lim) else (lim or "à confirmer")
    j = jours(offre)
    rangs = [("#", "Référence", no, None), ("⌂", "Acheteur public", sans_arabe(offre.get("acheteur") or "") or "à compléter", None),
             ("◉", "Lieu d'exécution", sans_arabe(lieu) or "à confirmer", None), ("▦", "Date limite", lim_aff, "date"),
             ("⚙", "Domaine", domaine, None), ("≡", "Procédure", (offre.get("type") or "à confirmer").capitalize(), None)]
    # place disponible jusqu'au pied de page : tableau + services (2 x 62) + bouton (86) + marges
    hr = 64
    while y + 14 + hr * 6 + 24 + 22 + 124 + 14 + 86 + 16 > HT - 96 and hr > 50: hr -= 2
    carte = (40, y, W - 40, y + hr * len(rangs) + 24)
    d.rounded_rectangle(carte, radius=22, fill=WHITE, outline=LIGNE, width=2)
    fl = police(27, False); fv = police(28, False); fs = police(28, liste=FONTS_SYMB); fb = police(24)
    yy = y + 12
    for k, (ic, lab, val, typ) in enumerate(rangs):
        cy = yy + hr // 2
        d.ellipse([70, cy - 22, 114, cy + 22], fill=(232, 241, 252))
        _w = d.textlength(ic, font=fs); d.text((92 - _w / 2, cy - 18), ic, font=fs, fill=BLEU_VIF if typ != "date" else ROUGE)
        d.text((134, cy - 17), lab, font=fl, fill=GRIS_TXT)
        vx, vmax = 400, W - 70 - 400
        if typ == "date":
            d.text((vx, cy - 18), lim_aff, font=police(30), fill=ROUGE)
            if j is not None:
                pas = "aujourd'hui" if j == 0 else ("dans %d jour%s" % (j, "s" if j > 1 else ""))
                pw = d.textlength(pas, font=fb) + 32
                d.rounded_rectangle([W - 70 - pw, cy - 22, W - 70, cy + 22], radius=22, fill=ROUGE)
                d.text((W - 70 - pw + 16, cy - 15), pas, font=fb, fill=WHITE)
        else:
            f = police(30) if k == 0 else fv
            while k and d.textlength(val, font=f) > vmax and f.size > 22: f = police(f.size - 1, False)
            v = val if d.textlength(val, font=f) <= vmax else lignes(d, val, f, vmax, 1)[0]
            d.text((vx, cy - f.size // 2 - 2), v, font=f, fill=(25, 30, 40))
        if k < len(rangs) - 1: d.line([(70, yy + hr), (W - 70, yy + hr)], fill=LIGNE, width=2)
        yy += hr
    # services cochés
    y = carte[3] + 22
    serv = ["Analyse du cahier des charges", "Étude technique et financière", "Préparation du dossier", "Accompagnement jusqu'au dépôt"]
    cw = (W - 80 - 20) // 2
    fsv = police(26)
    while max(d.textlength(t, font=fsv) for t in serv) > cw - 70 and fsv.size > 18: fsv = police(fsv.size - 1)
    for k, t in enumerate(serv):
        x = 40 + (k % 2) * (cw + 20); yb = y + (k // 2) * 62
        d.rounded_rectangle([x, yb, x + cw, yb + 50], radius=12, fill=(228, 238, 250))
        d.ellipse([x + 14, yb + 11, x + 42, yb + 39], fill=BLEU_VIF)
        d.text((x + 20, yb + 9), "✓", font=police(24, liste=FONTS_SYMB), fill=WHITE)
        f = fsv
        d.text((x + 54, yb + 25 - f.size // 2 - 2), t, font=f, fill=BLEU_FONCE)
    # bouton
    y += 2 * 62 + 14
    d.rounded_rectangle([40, y, W - 40, y + 86], radius=43, fill=BLEU_FONCE)
    fbt = police(34)
    _centre(d, y + 22, "RÉPONDEZ OUI POUR LANCER L'ÉTUDE", fbt, WHITE, W - 60)
    d.ellipse([W - 40 - 78, y + 8, W - 40 - 8, y + 78], fill=BLEU_VIF)
    d.text((W - 40 - 64, y + 12), "→", font=police(46, liste=FONTS_SYMB), fill=WHITE)
    # pied de page
    yp = HT - 96
    d.rectangle([0, yp, W, HT], fill=BLEU_FONCE)
    _logo_boite(fond, (40, yp + 16, 230, yp + 80), 12)
    d = ImageDraw.Draw(fond)
    tp = "Votre partenaire pour les marchés publics en Tunisie"; fp = police(28, False)
    while d.textlength(tp, font=fp) > W - 260 - 30 and fp.size > 18: fp = police(fp.size - 1, False)
    d.text((260, yp + 48 - fp.size // 2 - 2), tp, font=fp, fill=WHITE)
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
    doc = {"t": t, "no": no, "pdf": "", "png": "/_blob/" + pid, "png_id": pid, "statut": "brouillon", "cree_le": t, "cree_par": "robot_affiches", "modele": "carte",
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


GROUPES_WA = {"appel d'offre SPE", "AO SPE Électrique", "AO SPE Mécanique", "AO SPE Portail", "AO SPE Surveillance caméra et alarme",
              "AO SPE Métal construction", "AO SPE Peinture", "AO SPE Maritime", "AO SPE Engins, levage et hydraulique"}
GROUPE_PAR_METIER = {"Ascenseurs": "AO SPE Mécanique", "Portail": "AO SPE Portail", "Surveillance, alarme, incendie": "AO SPE Surveillance caméra et alarme",
                     "Électrique": "AO SPE Électrique", "Variateurs et équipements industriels": "AO SPE Électrique", "Mécanique": "AO SPE Mécanique",
                     "Métal construction": "AO SPE Métal construction", "Peinture": "AO SPE Peinture", "Maritime": "AO SPE Maritime",
                     "Engins, levage et hydraulique": "AO SPE Engins, levage et hydraulique"}


def groupe_wa(o):
    g = o.get("groupe")
    return g if g in GROUPES_WA else GROUPE_PAR_METIER.get(o.get("metier"), "appel d'offre SPE")


def legende_wa(o, no):
    """Modèle B (space-work/10) : légende courte sous l'affiche, comme l'exemple du directeur du 30/10."""
    objet = sans_arabe(o.get("objet") or "")
    if len(objet) > 140: objet = objet[:137].rsplit(" ", 1)[0] + "…"
    lieu = str(o.get("gouvernorat") or o.get("lieu") or "").replace("(à confirmer)", "").strip()
    j = jours(o)
    l1 = "Une belle opportunité%s : le %s, %s." % ((" à " + lieu) if lieu and not nrm(lieu).startswith("a confirmer") else "", no,
                                                   (objet[:1].lower() + objet[1:]) if objet else "voir l'affiche")
    lim = o.get("limite") or ""
    return (l1 + ("\nDate limite : %s%s." % (lim, " (J-%d)" % j if j is not None else "") if lim else "")
            + "\nTout est dans l'application SPE.\n\nRépondez 2 + N° pour lancer l'étude.")


def enfiler(o, png_id, essai):
    """Met l'affiche dans la file WhatsApp Supabase (envoyée par le robot WhatsApp Web du PC). Identifiant fixe
    « aff-<N°> » : jamais deux fois la même affiche. Seulement si l'offre a encore plus de 24 h."""
    no = str(o.get("no"))
    try:
        if int(o.get("tri") or 0) < ms() + 86400000: return False
    except (TypeError, ValueError): return False
    if essai: return True
    t = ms()
    st, _ = sb("POST", "/rest/v1/docs?on_conflict=collection,id",
               {"collection": "file_whatsapp", "id": "aff-" + no, "maj": t, "source": "robot_affiches",
                "data": {"t": t, "agent": "affiches", "no": no, "type": "image", "groupe": groupe_wa(o), "destinataire": groupe_wa(o),
                         "png": "/_blob/" + png_id, "nom_fichier": "affiche_%s.png" % no, "texte": legende_wa(o, no),
                         "priorite": 2, "statut": "en_attente", "essais": 0}},
               prefer="resolution=ignore-duplicates,return=minimal")
    return True


def enfiler_affiches_pretes(maxi, essai):
    """Affiches robot au modèle carte, pas encore dans la file : on les y met (les plus urgentes d'abord)."""
    st, aff = sb("GET", "/rest/v1/docs?collection=eq.affiches&select=id,data&data-%3E%3Emodele=eq.carte&limit=2000")
    st, file = sb("GET", "/rest/v1/docs?collection=eq.file_whatsapp&select=id&id=like.aff-*&limit=5000")
    deja = {r["id"][4:] for r in file}
    n = 0
    for r in sorted(aff, key=lambda r: (r["data"].get("donnees") or {}).get("limite_t") or 9e15):
        d = r["data"]
        if n >= maxi: break
        if r["id"] in deja or d.get("envoye_wa") or d.get("statut") not in ("brouillon", "valide"): continue
        if any(c.get("bloquant") and not c.get("ok") for c in d.get("controles") or []): continue
        st, rows = sb("GET", "/rest/v1/docs?collection=eq.offres&select=data&id=eq." + urllib.parse.quote(r["id"]))
        if not rows: continue
        o = rows[0]["data"]; o.setdefault("no", r["id"])
        if enfiler(o, d.get("png_id") or str(d.get("png", "")).rsplit("/", 1)[-1], essai): n += 1
    return n


def refaire_brouillons(maxi, essai, sortie):
    """Refait au modèle « carte » les affiches du ROBOT encore en brouillon et jamais envoyées (offre encore ouverte).
    Ne touche pas aux affiches validées, modifiées ou faites à la main ; l'ancienne image reste dans « historique »."""
    st, aff = sb("GET", "/rest/v1/docs?collection=eq.affiches&select=id,data&data-%3E%3Ecree_par=eq.robot_affiches&data-%3E%3Estatut=eq.brouillon&limit=2000")
    cibles = [r for r in aff if not r["data"].get("envoye_wa") and r["data"].get("modele") != "carte" and not r["data"].get("modifs")]
    n = 0
    for r in cibles:
        if n >= maxi: break
        st, rows = sb("GET", "/rest/v1/docs?collection=eq.offres&select=data&id=eq." + urllib.parse.quote(r["id"]))
        if not rows: continue
        o = rows[0]["data"]; o.setdefault("no", r["id"])
        try:
            if int(o.get("tri") or 0) < ms(): continue
        except (TypeError, ValueError): continue
        png, cat = composer(o)
        pid = hashlib.md5(png).hexdigest()
        if sortie:
            os.makedirs(sortie, exist_ok=True)
            open(os.path.join(sortie, re.sub(r"\W", "_", r["id"]) + ".png"), "wb").write(png)
        if not essai:
            sb("POST", "/storage/v1/object/blobs/" + pid, binaire=png, ctype="image/png")
            d = dict(r["data"]); t = ms()
            d["historique"] = (d.get("historique") or []) + [{"t": t, "par": "robot_affiches", "ancien_png": d.get("png"), "raison": "modèle carte (directeur, 15/11/2026)"}]
            d.update({"png": "/_blob/" + pid, "png_id": pid, "modele": "carte", "version": int(d.get("version") or 1) + 1})
            sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "affiches", "id": r["id"], "data": d, "maj": t, "source": "robot_affiches"},
               prefer="resolution=merge-duplicates,return=minimal")
        n += 1; log("  ~ %s refaite au modèle carte" % r["id"])
    return n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--max", type=int, default=10); ap.add_argument("--essai", action="store_true"); ap.add_argument("--sortie", default="")
    ap.add_argument("--file", type=int, default=6, help="affiches carte à mettre dans la file WhatsApp par passage (0 = aucune)")
    ap.add_argument("--refaire", type=int, default=5, help="nombre de brouillons robot à refaire au modèle carte par passage (0 = aucun)")
    a = ap.parse_args()
    if a.refaire: log("%d brouillon(s) refait(s) au modèle carte" % refaire_brouillons(a.refaire, a.essai, a.sortie))
    if a.file: log("%d affiche(s) mise(s) dans la file WhatsApp" % enfiler_affiches_pretes(a.file, a.essai))
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
