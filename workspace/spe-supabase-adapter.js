/*
 * Adaptateur SPE Workspace -> Supabase
 * L'application SPE Workspace a été écrite pour claude.ai (window.claude.use("db"), "user", "assets"...).
 * Ce fichier fournit la même interface en s'appuyant sur la table Supabase public.docs
 * (colonnes : collection, id, data jsonb, maj, source), déjà synchronisée avec SPE Live par le PC.
 * Accès direct avec le lien (décision du directeur, 06/11/2026) : pas de connexion pour le moment.
 */
(function () {
  "use strict";
  const URL_SB = "https://djvygsbdwcoyldujrezq.supabase.co";
  const CLE_PUB = "sb_publishable_c_LW07RXjWmU_KctUhrg6w_m8Kg6AJ8";
  const IMG = URL_SB + "/storage/v1/object/public/images-domaines/";
  const POLL_MS = 30000;
  const sb = window.supabase.createClient(URL_SB, CLE_PUB, { auth: { persistSession: false } });
  window.SPE_SB = sb;

  // ---------- fichiers /_blob/ de claude.ai -> Supabase ----------
  // Les images des domaines sont copiées dans Supabase ; les autres fichiers seront migrés plus tard.
  const BLOBS = {};
  const blobUrl = (u) => {
    if (typeof u !== "string") return u;
    const m = u.match(/\/_blob\/([0-9a-f]{32})/);
    if (!m) return u;
    return BLOBS[m[1]] || (URL_SB + "/storage/v1/object/public/blobs/" + m[1]);
  };
  window.SPE_blobUrl = blobUrl;
  // réécrit les <img src="/_blob/..."> et les liens au fil de l'affichage
  const reecrire = (el) => {
    if (!el || el.nodeType !== 1) return;
    const fix = (n) => {
      for (const a of ["src", "href"]) {
        const v = n.getAttribute && n.getAttribute(a);
        if (v && v.indexOf("/_blob/") !== -1) n.setAttribute(a, blobUrl(v));
      }
      const st = n.getAttribute && n.getAttribute("style");
      if (st && st.indexOf("/_blob/") !== -1) n.setAttribute("style", st.replace(/\/_blob\/[0-9a-f]{32}/g, (x) => blobUrl(x)));
    };
    fix(el);
    el.querySelectorAll && el.querySelectorAll("[src*='/_blob/'],[href*='/_blob/'],[style*='/_blob/']").forEach(fix);
  };
  // image pas encore copiée dans Supabase : on met l'image du domaine (ou le logo SPE) au lieu d'une image cassée
  const SECOURS = "icon-512.png";
  document.addEventListener("error", (ev) => {
    const t = ev.target;
    if (!t || t.tagName !== "IMG" || t.dataset.speSecours) return;
    t.dataset.speSecours = "1";
    t.src = SECOURS; t.style.objectFit = "contain"; t.style.background = "#0E2A47";
  }, true);
  new MutationObserver((ms) => ms.forEach((m) => {
    if (m.type === "attributes") reecrire(m.target);
    m.addedNodes && m.addedNodes.forEach(reecrire);
  })).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["src", "href", "style"] });

  // ---------- outils ----------
  const nouvelId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  const copie = (o) => JSON.parse(JSON.stringify(o === undefined ? null : o));
  const fusion = (cible, src) => {
    const out = Object.assign({}, cible || {});
    for (const [k, v] of Object.entries(src || {})) {
      if (v && typeof v === "object" && v.__delete__ === true) { delete out[k]; continue; }
      if (k.indexOf(".") > 0) { // chemin pointé : "a.b.c"
        const ps = k.split("."); let o = out;
        for (let i = 0; i < ps.length - 1; i++) { o[ps[i]] = (o[ps[i]] && typeof o[ps[i]] === "object") ? Object.assign({}, o[ps[i]]) : {}; o = o[ps[i]]; }
        o[ps[ps.length - 1]] = v; continue;
      }
      out[k] = v;
    }
    return out;
  };
  const snapDoc = (id, data) => ({ id, exists: data != null, data: () => (data == null ? undefined : copie(data)), get: (f) => (data || {})[f], ref: null });
  const snapListe = (rows) => {
    const docs = rows.map((r) => snapDoc(r.id, r.data));
    return { docs, size: docs.length, empty: !docs.length, forEach: (f) => docs.forEach(f), docChanges: () => docs.map((d) => ({ type: "added", doc: d })) };
  };
  const ecouteurs = new Set();
  const relancer = () => ecouteurs.forEach((f) => { try { f(); } catch (e) {} });
  document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") relancer(); });
  setInterval(() => { if (document.visibilityState === "visible") relancer(); }, POLL_MS);

  // ---------- références ----------
  class DocRef {
    constructor(coll, id) { this.coll = coll; this.id = id; this.path = coll + "/" + id; }
    collection(sous) { return new Requete(this.coll + "/" + this.id + "/" + sous); }
    async _lire() {
      const { data, error } = await sb.from("docs").select("data").eq("collection", this.coll).eq("id", this.id).maybeSingle();
      if (error) throw error;
      return data ? data.data : null;
    }
    async get() { return snapDoc(this.id, await this._lire()); }
    async set(data, opts) {
      let d = copie(data);
      if (opts && opts.merge) d = fusion(await this._lire(), d);
      const { error } = await sb.from("docs").upsert({ collection: this.coll, id: this.id, data: d, maj: Date.now(), source: "web" }, { onConflict: "collection,id" });
      if (error) throw error;
      setTimeout(relancer, 300);
    }
    async update(champs) {
      const actuel = await this._lire();
      if (actuel == null) { const e = new Error("document introuvable : " + this.path); e.code = "not-found"; throw e; }
      const { error } = await sb.from("docs").update({ data: fusion(actuel, copie(champs)), maj: Date.now(), source: "web" }).eq("collection", this.coll).eq("id", this.id);
      if (error) throw error;
      setTimeout(relancer, 300);
    }
    async delete() {
      const { error } = await sb.from("docs").delete().eq("collection", this.coll).eq("id", this.id);
      if (error) throw error;
      setTimeout(relancer, 300);
    }
    onSnapshot(ok, ko) {
      let fini = false;
      const tour = async () => { if (fini) return; try { ok(await this.get()); } catch (e) { ko && ko(e); } };
      ecouteurs.add(tour); tour();
      return () => { fini = true; ecouteurs.delete(tour); };
    }
  }

  class Requete {
    constructor(coll, o) { this.coll = coll; this.o = Object.assign({ ordre: null, sens: "asc", lim: null, filtres: [] }, o || {}); }
    _avec(x) { return new Requete(this.coll, Object.assign({}, this.o, x)); }
    doc(id) { return new DocRef(this.coll, id == null ? nouvelId() : String(id)); }
    orderBy(champ, sens) { return this._avec({ ordre: champ, sens: sens === "desc" ? "desc" : "asc" }); }
    limit(n) { return this._avec({ lim: n }); }
    where(champ, op, val) { return this._avec({ filtres: this.o.filtres.concat([[champ, op, val]]) }); }
    async add(data) { const r = this.doc(); await r.set(data); return r; }
    async _lire() {
      const lot = 1000, max = this.o.lim || 5000, L = [];
      for (let de = 0; de < max; de += lot) {
        let q = sb.from("docs").select("id, data").eq("collection", this.coll);
        for (const [c, op, v] of this.o.filtres) {
          const col = "data->>" + c, sv = String(v);
          if (op === "==" || op === "eq") q = q.eq(col, sv);
          else if (op === "!=" || op === "ne") q = q.neq(col, sv);
          else if (op === "in" && Array.isArray(v)) q = q.in(col, v.map(String));
        }
        if (this.o.ordre) q = q.order("data->" + this.o.ordre, { ascending: this.o.sens !== "desc", nullsFirst: false });
        q = q.range(de, Math.min(de + lot, max) - 1);
        const { data, error } = await q;
        if (error) throw error;
        L.push(...data);
        if (data.length < lot) break;
      }
      // filtres numériques faits ici (comparaison exacte des nombres)
      return L.filter((r) => this.o.filtres.every(([c, op, v]) => {
        const x = (r.data || {})[c];
        switch (op) { case "<": return x < v; case "<=": return x <= v; case ">": return x > v; case ">=": return x >= v;
          case "array-contains": return Array.isArray(x) && x.includes(v); default: return true; }
      }));
    }
    async get() { return snapListe(await this._lire()); }
    onSnapshot(ok, ko) {
      let fini = false;
      const tour = async () => { if (fini) return; try { ok(snapListe(await this._lire())); } catch (e) { ko && ko(e); } };
      ecouteurs.add(tour); tour();
      return () => { fini = true; ecouteurs.delete(tour); };
    }
  }

  const db = { collection: (c) => new Requete(c), doc: (p) => { const i = p.lastIndexOf("/"); return new DocRef(p.slice(0, i), p.slice(i + 1)); } };

  // ---------- utilisateur : accès direct, sans connexion ----------
  const user = {
    id: async () => "u_directeur",
    isOwner: async () => true,
    me: async () => ({ id: "u_directeur", name: "Cherif Blidi", email: "cherifch3ar@gmail.com" }),
    profile: async () => ({ id: "u_directeur", name: "Cherif Blidi" })
  };

  // ---------- fichiers : envoi dans Supabase Storage (bucket public « blobs ») ----------
  const assets = {
    upload: async (fichier, opts) => {
      const id = Array.from(crypto.getRandomValues(new Uint8Array(16))).map((b) => b.toString(16).padStart(2, "0")).join("");
      const { error } = await sb.storage.from("blobs").upload(id, fichier, { contentType: (fichier && fichier.type) || (opts && opts.contentType) || "application/octet-stream" });
      if (error) throw error;
      return { id, url: "/_blob/" + id };
    },
    url: (id) => blobUrl("/_blob/" + id)
  };

  // ---------- téléchargements ----------
  const downloads = {
    save: async (contenu, nom, type) => {
      const blob = contenu instanceof Blob ? contenu : new Blob([contenu], { type: type || "application/octet-stream" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nom || "fichier"; document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
    }
  };
  downloads.download = downloads.save;

  window.claude = {
    use: async (nom) => {
      if (nom === "db") return db;
      if (nom === "user") return user;
      if (nom === "assets") return assets;
      if (nom === "downloads") return downloads;
      return null; // "sample" (IA) n'est pas disponible hors de claude.ai
    }
  };

  // Images des domaines : on lit shared/images_metiers (copie Supabase) pour remplacer les anciennes adresses /_blob/.
  sb.from("docs").select("data").eq("collection", "shared").eq("id", "images_metiers").maybeSingle().then(({ data }) => {
    const d = (data && data.data) || {};
    const ks = d.k || {}, kSb = d.k_supabase || {};
    for (const [cle, ancien] of Object.entries(ks)) {
      const m = String(ancien).match(/[0-9a-f]{32}/);
      if (m && kSb[cle]) BLOBS[m[0]] = kSb[cle];
    }
    for (const [metier, url] of Object.entries(d.par_metier || {})) {
      const m = String(url).match(/[0-9a-f]{32}/);
      const f = { "Ascenseurs": "ascenseurs", "Portail": "portails_automatiques", "Surveillance, alarme, incendie": "surveillance_alarme_incendie", "Électrique": "electrique",
        "Variateurs et équipements industriels": "variateurs_equipements_industriels", "Mécanique": "mecanique", "Métal construction": "construction_metallique", "Peinture": "peinture",
        "Maritime": "maritime", "Engins, levage et hydraulique": "levage_hydraulique", "Blanchisserie et autres techniques": "blanchisserie", "Chaud, froid, climatisation": "mecanique" }[metier];
      if (m && f) BLOBS[m[0]] = IMG + "metier_" + f + ".jpg";
    }
    reecrire(document.body);
  }).catch(() => {});
})();
