# -*- coding: utf-8 -*-
"""
Robot SUPERVISEUR SPE (sans IA, gratuit) — GitHub Actions toutes les heures.
1. Santé des robots : dernier passage de chaque robot (relevé en ligne, veille Google, pièces en ligne, robot du PC,
   affiches) ; retard ou « BESOIN » → une ligne « events » agent "superviseur" (pas plus d'une par problème et par 6 h).
2. Table agent_tasks (si elle existe et si la clé service est fournie) : relance les tâches en erreur (3 essais au plus),
   passe en « bloque » au-delà, signale les tâches « en_cours » depuis plus de 3 h.
Ne supprime rien, ne modifie aucune autre collection, n'envoie rien sur WhatsApp.
Usage : python robots/superviseur.py [--essai]
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request

SB = "https://djvygsbdwcoyldujrezq.supabase.co"
CLE = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8"
SERVICE = os.environ.get("SUPABASE_SERVICE_KEY", "")  # secret GitHub, seulement pour agent_tasks
ATTENDUS = [  # agent dans events, délai maximal sans passage (heures), libellé
    ("releve_en_ligne", 3, "Relevé TUNEPS en ligne (toutes les 2 h)"),
    ("robot_veille", 4, "Veille Google (toutes les 3 h)"),
    ("robot_telechargement", 2, "Robot des pièces (PC ou en ligne, toutes les heures)"),
    ("affiches", 3, "Robot affiches (toutes les heures)"),
]


def ms(): return int(time.time() * 1000)
def log(t): print(time.strftime("%H:%M:%S"), t, flush=True)


def sb(method, chemin, corps=None, prefer=None, cle=None):
    k = cle or CLE
    h = {"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json"}
    if prefer: h["Prefer"] = prefer
    req = urllib.request.Request(SB + chemin, data=json.dumps(corps).encode() if corps is not None else None, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        b = r.read(); return r.status, (json.loads(b) if b else None)


def events_depuis(heures):
    depuis = ms() - heures * 3600000
    _, rows = sb("GET", "/rest/v1/docs?collection=eq.events&select=id,maj,data&maj=gt.%d&order=maj.desc&limit=1000" % depuis)
    return rows or []


# Version de l'installation du PC. L'augmenter fait relancer l'installateur UNE fois sur le PC, à distance
# (le directeur travaille à distance et ne peut rien faire sur le PC : décision du 15/11/2026, « vas-y, go »).
VERSION_PC = "2026-11-15-demarrage"


def maintenance_pc():
    """Seulement sur le PC Windows : met le dépôt à jour, puis relance l'installateur si sa version a changé."""
    if os.name != "nt": return
    import subprocess
    depot = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
    shared = os.environ.get("SPE_SHARED", r"C:\Users\USER\Desktop\01_SPE\SPE_shared")
    marque = os.path.join(shared, "installe_version.txt")
    try: subprocess.run(["git", "-C", depot, "pull", "-q"], timeout=300)
    except Exception as e: log("git pull impossible : %s" % e)
    deja = open(marque, encoding="utf-8").read().strip() if os.path.exists(marque) else ""
    if deja == VERSION_PC: return
    ps1 = os.path.join(depot, "robots", "pc", "installer_serveur_spe.ps1")
    if not os.path.exists(ps1): return
    log("Installation du PC à la version %s…" % VERSION_PC)
    r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps1], timeout=1800, capture_output=True, text=True, errors="replace")
    os.makedirs(shared, exist_ok=True)
    open(marque, "w", encoding="utf-8").write(VERSION_PC)
    erreurs = [l for l in (r.stdout or "").splitlines() if "ERREUR" in l or "ATTENTION" in l]
    t = ms()
    try:
        sb("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-installation-pc" % t, "maj": t, "source": "superviseur_pc",
                                      "data": {"t": t, "agent": "superviseur", "texte": "Installation du PC faite à distance (version %s)%s" % (
                                          VERSION_PC, " — " + " | ".join(erreurs)[:600] if erreurs else " — aucune erreur.")}}, prefer="return=minimal")
    except Exception as e: log("journal impossible : %s" % e)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--essai", action="store_true"); a = ap.parse_args()
    ev = events_depuis(12)
    dernier = {}
    for r in ev:
        ag = (r.get("data") or {}).get("agent")
        if ag and ag not in dernier: dernier[ag] = r
    deja = {(r.get("data") or {}).get("texte", "")[:60] for r in ev if (r.get("data") or {}).get("agent") == "superviseur" and r["maj"] > ms() - 6 * 3600000}
    alertes = []
    for ag, maxh, lib in ATTENDUS:
        d = dernier.get(ag)
        if not d:
            alertes.append("%s : aucun passage depuis plus de 12 h." % lib)
        else:
            age = (ms() - d["maj"]) / 3600000
            txt = (d.get("data") or {}).get("texte", "")
            if age > maxh: alertes.append("%s : dernier passage il y a %.0f h (limite %d h)." % (lib, age, maxh))
            if txt.startswith("BESOIN"): alertes.append("%s : %s" % (lib, txt[:200]))
    # agent_tasks
    bilan_at = ""
    if SERVICE:
        try:
            _, taches = sb("GET", "/rest/v1/agent_tasks?statut=in.(erreur,en_cours)&select=*&limit=500", cle=SERVICE)
            rel, blo, longs = 0, 0, 0
            for t in taches or []:
                if t["statut"] == "erreur":
                    if t["essais"] < 3:
                        if not a.essai: sb("PATCH", "/rest/v1/agent_tasks?id=eq." + urllib.parse.quote(t["id"]), {"statut": "a_faire", "essais": t["essais"] + 1, "maj": "now()"}, prefer="return=minimal", cle=SERVICE)
                        rel += 1
                    else:
                        if not a.essai: sb("PATCH", "/rest/v1/agent_tasks?id=eq." + urllib.parse.quote(t["id"]), {"statut": "bloque", "maj": "now()"}, prefer="return=minimal", cle=SERVICE)
                        blo += 1; alertes.append("Tâche %s (%s) bloquée après 3 essais : %s" % (t["id"], t["agent"], (t.get("erreur") or "")[:120]))
                elif t["statut"] == "en_cours":
                    try:
                        from datetime import datetime, timezone
                        age = (datetime.now(timezone.utc) - datetime.fromisoformat(t["maj"].replace("Z", "+00:00"))).total_seconds() / 3600
                        if age > 3: longs += 1
                    except Exception: pass
            bilan_at = " Tâches d'agents : %d relancée(s), %d bloquée(s), %d en cours depuis plus de 3 h." % (rel, blo, longs)
        except Exception as ex:
            log("agent_tasks non lisible : %s" % ex)
    nouvelles = [x for x in alertes if x[:60] not in deja]
    log("%d alerte(s), %d nouvelle(s).%s" % (len(alertes), len(nouvelles), bilan_at))
    for x in alertes: log("  ! " + x)
    if a.essai: return 0
    t = ms()
    texte = ("Superviseur : tout va bien, robots à l'heure." if not alertes else "Superviseur : " + " | ".join(nouvelles or alertes)[:900]) + bilan_at
    if nouvelles or not alertes and not any((r.get("data") or {}).get("agent") == "superviseur" and r["maj"] > ms() - 6 * 3600000 for r in ev):
        sb("POST", "/rest/v1/docs", {"collection": "events", "id": "e-%d-superviseur" % t, "maj": t, "source": "robot_superviseur",
                                   "data": {"t": t, "agent": "superviseur", "texte": texte}}, prefer="return=minimal")
        log("event écrit")
    return 0


if __name__ == "__main__":
    try: maintenance_pc()
    except Exception as e: log("maintenance PC : %s" % e)
    sys.exit(main())
