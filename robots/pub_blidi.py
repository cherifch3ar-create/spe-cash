# -*- coding: utf-8 -*-
"""
Affiches PUBLICITÉ « Blidi Ascenseurs » (sans IA, gratuit) — utilisé par l'agent Publicité Blidi Ascenseurs.
Demande du directeur (16/11/2026) : un agent Publicité et Facebook pour Blidi Ascenseurs.

Fabrique une affiche 1080×1350 (photo d'ascenseur, logo SPE, titre, 3 points, bandeau « Blidi Ascenseurs »),
la réduit en JPEG léger et prépare son envoi pour validation au directeur dans « SPE Réunion agents »
(file « file_whatsapp » de SPE Live, envoyée par Amine). Rien n'est publié sur Facebook sans validation.

  python robots/pub_blidi.py --titre "..." --points "a|b|c" --legende-fichier legende.txt --sortie /tmp/pub [--theme 0..3]
Sortie : affiche.jpg, lot.json (écritures ArtifactData avec file_path), plan.json.
"""
import argparse, base64, io, json, os, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import affiches as A

PHOTOS = ["metier_ascenseurs.jpg", "fiche_ascenseurs.jpg"]
THEMES = [((16, 42, 77), (201, 162, 39)), ((22, 60, 110), (91, 178, 255)), ((40, 30, 70), (236, 108, 172)), ((14, 70, 70), (240, 200, 90))]


def photo(i):
    for n in PHOTOS[i % len(PHOTOS):] + PHOTOS:
        try:
            with urllib.request.urlopen(A.SB + "/storage/v1/object/public/images-domaines/" + n, timeout=60) as r:
                return Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception:
            continue
    return Image.new("RGB", (1080, 900), (60, 80, 110))


def composer(titre, points, theme):
    W, H = 1080, 1350
    fonce, accent = THEMES[theme % len(THEMES)]
    im = Image.new("RGBA", (W, H), fonce + (255,))
    ph = A.couvrir(photo(theme), W, 760)
    if theme % 2: ph = ph.transpose(Image.FLIP_LEFT_RIGHT)
    im.paste(ph, (0, 0))
    voile = Image.new("RGBA", (W, H), (0, 0, 0, 0)); vd = ImageDraw.Draw(voile)
    for y in range(420, 780): vd.line([(0, y), (W, y)], fill=fonce + (int(255 * ((y - 420) / 360) ** 1.4),))
    im = Image.alpha_composite(im, voile); d = ImageDraw.Draw(im)
    A._logo_boite(im, (40, 36, 330, 150), 18); d = ImageDraw.Draw(im)
    fb = A.police(34); tag = "BLIDI ASCENSEURS"
    tw = d.textlength(tag, font=fb); d.rounded_rectangle([W - 60 - tw - 40, 60, W - 60, 120], radius=30, fill=accent)
    d.text((W - 60 - tw - 20, 70), tag, font=fb, fill=fonce)
    ft = A.police(64); lt = A.lignes(d, titre, ft, W - 120, 3)
    while len(lt) > 2 and ft.size > 46: ft = A.police(ft.size - 4); lt = A.lignes(d, titre, ft, W - 120, 3)
    y = 800
    for l in lt: d.text((60, y), l, font=ft, fill=(255, 255, 255)); y += ft.size + 12
    y += 18; fp = A.police(38, False)
    for p in points[:3]:
        d.ellipse([60, y + 8, 92, y + 40], fill=accent)
        d.text((68, y + 4), "✓", font=A.police(28, liste=A.FONTS_SYMB), fill=fonce)
        for k, l in enumerate(A.lignes(d, p, fp, W - 200, 2)): d.text((112, y + k * 46), l, font=fp, fill=(232, 238, 248))
        y += 46 * min(2, len(A.lignes(d, p, fp, W - 200, 2))) + 22
    d.rectangle([0, H - 110, W, H], fill=accent)
    pied = "Installation · Maintenance · Modernisation — partout en Tunisie"
    f2 = A.police(34)
    while d.textlength(pied, font=f2) > W - 80 and f2.size > 22: f2 = A.police(f2.size - 1)
    d.text(((W - d.textlength(pied, font=f2)) / 2, H - 76), pied, font=f2, fill=fonce)
    out = io.BytesIO(); im.convert("RGB").save(out, "JPEG", quality=82, optimize=True, progressive=True)
    return out.getvalue()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--titre", required=True); ap.add_argument("--points", default="")
    ap.add_argument("--legende-fichier", required=True); ap.add_argument("--sortie", default="/tmp/pub")
    ap.add_argument("--theme", type=int, default=int(time.time() // 86400) % 4)
    ap.add_argument("--groupe", default="SPE Réunion agents")
    a = ap.parse_args()
    os.makedirs(a.sortie, exist_ok=True)
    jpg = composer(a.titre, [p.strip() for p in a.points.split("|") if p.strip()], a.theme)
    open(os.path.join(a.sortie, "affiche.jpg"), "wb").write(jpg)
    leg = open(a.legende_fichier, encoding="utf-8").read().strip()
    t = A.ms(); doc = "f-%d-blidi_pub" % t
    b64 = base64.b64encode(jpg).decode(); parts = [b64[i:i + 180000] for i in range(0, len(b64), 180000)]
    ecr = []
    for i, p in enumerate(parts, 1):
        f = os.path.join(a.sortie, "w_%s_p%d.json" % (doc, i)); json.dump({"base64": p, "partie": i, "total": len(parts)}, open(f, "w"))
        ecr.append({"op": "set", "collection": "pdf_parts", "doc_id": "%s_p%d" % (doc, i), "file_path": f})
    texte = "Publicité Blidi Ascenseurs — À VALIDER (répondez OUI pub pour publier)\n\n" + leg
    f = os.path.join(a.sortie, "w_%s.json" % doc)
    json.dump({"t": t, "agent": "blidi_pub", "destinataire": a.groupe, "groupe": a.groupe, "copie": "", "type": "image",
               "nom_fichier": "pub_blidi_%d.jpg" % t, "parts": len(parts), "texte": texte, "priorite": 2, "statut": "en_attente", "essais": 0},
              open(f, "w"), ensure_ascii=False)
    ecr.append({"op": "set", "collection": "file_whatsapp", "doc_id": doc, "file_path": f})
    json.dump(ecr, open(os.path.join(a.sortie, "lot.json"), "w"), indent=0)
    json.dump({"doc_id": doc, "octets": len(jpg), "parts": len(parts)}, open(os.path.join(a.sortie, "plan.json"), "w"))
    print("Affiche %d Ko prête : %s/affiche.jpg — lot.json à écrire dans SPE Live" % (len(jpg) // 1024, a.sortie))


if __name__ == "__main__":
    sys.exit(main())
