# -*- coding: utf-8 -*-
"""
Vidéo REEL « Blidi Ascenseurs » (gratuit, sans IA) : 15 s, verticale 1080×1920, 30 i/s, MP4 prêt pour Facebook/Instagram.
Demande du directeur (16-17/11/2026) : « vidéo comme cette vidéo, tu peux créer gratuitement ».
Scènes : photo en mouvement + logo Blidi → titre → 3 points → carte de fin (logo, services, « Écrivez-nous en message privé »).
Pas de musique (à ajouter au moment de publier, Facebook propose des musiques libres).

  python robots/reel_blidi.py --titre "..." --points "a|b|c" --theme 0..3 --sens 1|-1 --sortie reel.mp4
"""
import argparse, os, shutil, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import affiches as A, pub_blidi as P

W, H, FPS, DUREE = 1080, 1920, 30, 15


def ease(x):
    x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3


def fabriquer(titre, points, theme, sens, sortie):
    fonce, accent = P.THEMES[theme % len(P.THEMES)]
    photo = P.photo(theme)
    if sens < 0: photo = photo.transpose(Image.FLIP_LEFT_RIGHT)
    base = A.couvrir(photo, 1400, 1920)
    tmp = tempfile.mkdtemp(prefix="reel_")
    titre = titre.replace(" ?", "\u00a0?").replace(" !", "\u00a0!").replace(" :", "\u00a0:")  # pas de « ? » seul en début de ligne
    m = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    ft = A.police(78); fs = A.police(36, liste=A.FONTS_SYMB)
    lt = A.lignes(m, titre, ft, W - 140, 3)
    fp = A.police(54)
    while max(m.textlength(p, font=fp) for p in points[:3]) > W - 70 - 75 - 50 and fp.size > 34: fp = A.police(fp.size - 2)
    for i in range(DUREE * FPS):
        t = i / FPS
        z = 1.0 + 0.08 * t / DUREE; bw, bh = int(1400 * z), int(1920 * z)
        b = base.resize((bw, bh), Image.BILINEAR)
        pos = (0.15 + 0.7 * t / DUREE) if sens > 0 else (0.85 - 0.7 * t / DUREE)
        ox = int((bw - W) * pos); oy = (bh - H) // 2
        im = b.crop((ox, oy, ox + W, oy + H)).convert("RGBA")
        v = Image.new("RGBA", (W, H), (0, 0, 0, 0)); vd = ImageDraw.Draw(v)
        for y in range(900, H): vd.line([(0, y), (W, y)], fill=fonce + (int(235 * ((y - 900) / (H - 900)) ** 1.2),))
        im = Image.alpha_composite(im, v)
        P.logo_blidi(im, (60, 120, 520, 280), fonce, accent); d = ImageDraw.Draw(im)
        a = ease((t - 0.5) / 1.2)
        if a > 0:
            y = 1180 + int((1 - a) * 60)
            for l in lt: d.text((70, y), l, font=ft, fill=(255, 255, 255, int(255 * a))); y += 92
        for k, p in enumerate(points[:3]):
            a = ease((t - 4 - 1.5 * k) / 0.8)
            if a <= 0: continue
            y = 1500 + k * 95; x = 70 - int((1 - a) * 80)
            d.ellipse([x, y + 6, x + 50, y + 56], fill=accent + (int(255 * a),))
            d.text((x + 13, y + 6), "✓", font=fs, fill=fonce)
            d.text((x + 75, y), p, font=fp, fill=(240, 244, 250, int(255 * a)))
        a = ease((t - 11) / 1)
        if a > 0:
            im = Image.alpha_composite(im, Image.new("RGBA", (W, H), fonce + (int(255 * a),))); d = ImageDraw.Draw(im)
            if a > 0.5:
                P.logo_blidi(im, (240, 620, 840, 830), fonce, accent); d = ImageDraw.Draw(im)
                for k, (txt, f, col) in enumerate([("Installation · Maintenance · Modernisation", A.police(44), (255, 255, 255)),
                                                   ("Partout en Tunisie", A.police(48), accent),
                                                   ("Écrivez-nous en message privé", A.police(52), (255, 255, 255))]):
                    d.text(((W - d.textlength(txt, font=f)) / 2, 940 + k * 110), txt, font=f, fill=col)
        im.convert("RGB").save(os.path.join(tmp, "%04d.jpg" % i), quality=90)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", os.path.join(tmp, "%04d.jpg"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "21", "-movflags", "+faststart", sortie], check=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return sortie


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--titre", required=True); ap.add_argument("--points", required=True)
    ap.add_argument("--theme", type=int, default=0); ap.add_argument("--sens", type=int, default=1)
    ap.add_argument("--sortie", default="reel_blidi.mp4")
    a = ap.parse_args()
    print(fabriquer(a.titre, [p.strip() for p in a.points.split("|") if p.strip()], a.theme, a.sens, a.sortie))
