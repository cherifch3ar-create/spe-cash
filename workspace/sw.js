// SPE Workspace : cache simple de la page (les données viennent toujours de Supabase)
const C = "spe-workspace-v1";
const FICHIERS = ["./", "index.html", "spe-supabase-adapter.js", "manifest.json", "icon-192.png", "icon-512.png"];
self.addEventListener("install", (e) => { self.skipWaiting(); e.waitUntil(caches.open(C).then((c) => c.addAll(FICHIERS)).catch(() => {})); });
self.addEventListener("activate", (e) => e.waitUntil(caches.keys().then((ks) => Promise.all(ks.filter((k) => k !== C).map((k) => caches.delete(k)))).then(() => self.clients.claim())));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return; // Supabase : toujours en direct
  e.respondWith(fetch(e.request).then((r) => { const k = r.clone(); caches.open(C).then((c) => c.put(e.request, k)); return r; }).catch(() => caches.match(e.request)));
});
