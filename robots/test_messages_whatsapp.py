# -*- coding: utf-8 -*-
"""
TEST de tous les modèles de messages WhatsApp SPE (demande du directeur, 15/11/2026 :
« créer un modèle test pour tous les messages WhatsApp pour finir ce travail définitivement »).

Met dans la file WhatsApp Supabase UN exemple de chaque modèle (space-work/10_MODELES_MESSAGES_WHATSAPP.md),
avec une vraie offre ouverte, adressé à UN seul groupe (par défaut « SPE Réunion agents »), marqué [TEST].
Le robot WhatsApp Web du PC les envoie en premier (priorité 0). Rien n'est envoyé dans les groupes d'appels d'offres.

  python robots/test_messages_whatsapp.py            -> affiche les 6 messages sans rien écrire
  python robots/test_messages_whatsapp.py --envoyer  -> les met dans la file
"""
import argparse, io, json, os, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import affiches as A  # même dessin, mêmes règles de légende et de groupe

MENU = "Répondez avec le chiffre + N° : 1 fiche de visite · 2 étudier · 3 cahier des charges · 4 sûr ou non · 5 rappel demain"


def offres_ouvertes(n):
    st, rows = A.sb("GET", "/rest/v1/docs?collection=eq.offres&select=id,data&data-%3E%3Etri=gt." + str(A.ms() + 2 * 86400000)
                    + "&order=data-%3Etri.asc&limit=60")
    out = []
    for r in rows:
        d = r["data"]; d.setdefault("no", r["id"])
        if A.sans_arabe(d.get("objet") or "") and "expir" not in str(d.get("statut", "")).lower(): out.append(d)
    return out[:n]


def court(t, n):
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"


def ligne_offre(o):
    nat = {"fourniture_et_pose": "[FOURNITURE ET POSE]", "fourniture_seule": "[FOURNITURE SEULE]", "service": "[SERVICE / RÉPARATION]"}.get(o.get("nature"), "[À CONFIRMER]")
    j = A.jours(o)
    return "%s %s — %s (%s)\nDate limite : %s%s\n%s" % (nat, o.get("acheteur") or "Acheteur à compléter", court(A.sans_arabe(o.get("objet") or ""), 150), o["no"],
                                                       o.get("limite") or "à confirmer", " (J-%d)" % j if j is not None else "", o.get("lien") or "")


def pdf_test(o):
    """Une page « Étude » d'exemple (pas une vraie étude), en PDF, mise dans le stockage public blobs."""
    from PIL import Image, ImageDraw
    png, _ = A.composer(o)
    im = Image.open(io.BytesIO(png)).convert("RGB")
    page = Image.new("RGB", (1240, 1754), "white"); d = ImageDraw.Draw(page)
    d.text((80, 70), "ÉTUDE — EXEMPLE DE TEST (pas une vraie étude)", font=A.police(40), fill=A.BLEU_FONCE)
    d.text((80, 130), "Offre %s — modèle D des messages WhatsApp" % o["no"], font=A.police(28, False), fill=A.GRIS_TXT)
    page.paste(im.resize((864, 1080)), (188, 220))
    d.text((80, 1360), "Contenu réel d'une étude : synthèse, fournitures, prix, risques, décision proposée.", font=A.police(26, False), fill=(30, 30, 30))
    out = io.BytesIO(); page.save(out, "PDF", resolution=150)
    b = out.getvalue()
    import hashlib
    pid = "test-etude-" + hashlib.md5(b).hexdigest()[:16]
    A.sb("POST", "/storage/v1/object/blobs/" + pid, binaire=b, ctype="application/pdf")
    return A.SB + "/storage/v1/object/public/blobs/" + pid


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--envoyer", action="store_true"); ap.add_argument("--groupe", default="SPE Réunion agents")
    a = ap.parse_args()
    offres = offres_ouvertes(3)
    if len(offres) < 2: print("Pas assez d'offres ouvertes pour le test."); return 1
    o1, o2 = offres[0], offres[1]
    t = A.ms()
    msgs = [
        ("A", "texte", "Rayen (Recherche) — Nouvelles annonces — %s (%s)\n\n%s\n\n%s\n\n%s" % (
            o1.get("metier") or "Appels d'offres", time.strftime("%d/%m/%Y %H:%M"), ligne_offre(o1), ligne_offre(o2), MENU), {}),
        ("B", "image", A.legende_wa(o1, o1["no"]), {"png_test": o1}),
        ("C", "texte", "ALERTE — date limite proche\n%s : %s\nDate limite : %s (J-%s).\nRépondez 2 + %s pour lancer l'étude tout de suite, ou 5 + %s pour un rappel demain." % (
            o2["no"], court(A.sans_arabe(o2.get("objet") or ""), 120), o2.get("limite") or "à confirmer", A.jours(o2), o2["no"], o2["no"]), {}),
        ("D", "pdf", "Bureau d'études — Étude de l'offre %s (%s).\nRésumé : faisable / à vérifier / prix estimé. Le PDF complet est joint.\nRépondez 4 + %s pour l'avis « sûr ou non »." % (
            o1["no"], A.sans_arabe(o1.get("acheteur") or ""), o1["no"]), {"pdf_test": o1}),
        ("E", "texte", "Sirine (Directrice IA) — Bilan du %s\nTerminé : …\nRésultats importants : …\nBloqué : …\nDécisions à prendre par vous : 1. … (répondre OUI 1 / NON 1)\nAméliorations du jour : …\nÉtat : base OK, robot WhatsApp connecté, sauvegardes OK." % time.strftime("%d/%m"), {}),
        ("F", "texte", "Amine — Commande reçue : « 2 %s ». L'étude de l'offre %s est lancée ; vous recevrez le PDF dans ce groupe." % (o1["no"], o1["no"]), {}),
    ]
    ecrits = 0
    for k, (code, typ, texte, extra) in enumerate(msgs):
        data = {"t": t + k, "agent": "test", "test": True, "type": typ, "groupe": a.groupe, "destinataire": a.groupe,
                "texte": "[TEST %d/6 — modèle %s]\n%s" % (k + 1, code, texte), "priorite": 0, "statut": "en_attente", "essais": 0}
        if "png_test" in extra:
            png, _ = A.composer(extra["png_test"]); import hashlib
            pid = hashlib.md5(png).hexdigest()
            if a.envoyer: A.sb("POST", "/storage/v1/object/blobs/" + pid, binaire=png, ctype="image/png")
            data.update({"png": "/_blob/" + pid, "nom_fichier": "affiche_%s.png" % extra["png_test"]["no"], "no": extra["png_test"]["no"]})
        if "pdf_test" in extra:
            data.update({"lien_pdf": pdf_test(extra["pdf_test"]) if a.envoyer else "(lien PDF créé à l'envoi)", "nom_fichier": "Etude_TEST_%s.pdf" % extra["pdf_test"]["no"]})
        print("— %s (%s) —\n%s\n" % (code, typ, data["texte"]))
        if a.envoyer:
            A.sb("POST", "/rest/v1/docs?on_conflict=collection,id", {"collection": "file_whatsapp", "id": "test-%d-%s" % (t, code), "maj": t + k,
                                                                    "source": "test_messages", "data": data}, prefer="resolution=ignore-duplicates,return=minimal")
            ecrits += 1
    print("%d message(s) de test mis dans la file pour « %s »." % (ecrits, a.groupe) if a.envoyer else "(essai : rien écrit — ajouter --envoyer)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
