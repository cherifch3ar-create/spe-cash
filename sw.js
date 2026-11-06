// L'ancien Cash Manager est retiré pour le moment (décision du directeur, 06/11/2026).
// Ce fichier remplace son service worker : il se désinstalle et vide son cache pour ne pas gêner SPE Live.
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) await caches.delete(k);
    await self.registration.unregister();
    for (const c of await self.clients.matchAll({ type: "window" })) c.navigate(c.url);
  })());
});
