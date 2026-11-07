// SPE Live : cache léger de la page pour l'installation ; les données viennent toujours de Supabase.
const C = "spe-live-v1";
self.addEventListener("install", (e) => { e.waitUntil(caches.open(C).then((c) => c.addAll(["./", "index.html", "icone.png", "logo_blanc.png", "logo_noir.png"]))); self.skipWaiting(); });
self.addEventListener("activate", (e) => { e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((x) => x !== C).map((x) => caches.delete(x))))); self.clients.claim(); });
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  e.respondWith(fetch(e.request).then((r) => { const copie = r.clone(); caches.open(C).then((c) => c.put(e.request, copie)); return r; }).catch(() => caches.match(e.request)));
});
